import smtplib
from datetime import date, datetime
from decimal import Decimal
from email.message import EmailMessage
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.hrm.company import get_company_profile
from app.hrm.models import Employee
from app.hrm.payroll_models import Payslip

EARNING_FIELDS = ("basic", "hra", "special_allowance", "conveyance", "medical_allowance", "bonus", "incentive", "overtime", "arrears", "other_earnings")
DEDUCTION_FIELDS = ("employee_pf", "employee_esi", "professional_tax", "tds", "loan_advance", "loss_of_pay", "other_deductions")
LABELS = {field: field.replace("_", " ").title() for field in EARNING_FIELDS + DEDUCTION_FIELDS}


def money(value):
    try:
        return max(Decimal(str(value or 0)).quantize(Decimal("0.01")), Decimal("0.00"))
    except Exception as exc:
        raise ValueError("Salary amounts must be valid non-negative numbers") from exc


def masked(value, visible=4):
    value = (value or "").strip()
    if not value or "*" in value:
        return value or None
    compact = "".join(ch for ch in value if ch.isalnum())
    return ("*" * max(len(compact) - visible, 4) + compact[-visible:]) if compact else None


def calculate(data):
    values = {field: money(data.get(field)) for field in EARNING_FIELDS + DEDUCTION_FIELDS}
    values["gross_earnings"] = sum((values[f] for f in EARNING_FIELDS), Decimal("0"))
    values["total_deductions"] = sum((values[f] for f in DEDUCTION_FIELDS), Decimal("0"))
    values["net_pay"] = values["gross_earnings"] - values["total_deductions"]
    if values["net_pay"] < 0:
        raise ValueError("Total deductions cannot exceed gross earnings")
    return values


def prefill(db: Session, employee_id: int):
    employee = db.get(Employee, employee_id)
    if not employee:
        raise ValueError("Employee not found")
    company = get_company_profile(db)
    if not company:
        raise ValueError("Complete the Company Profile before creating payslips")
    return {"employee": employee, "company": company}


def save_payslip(db: Session, payslip_id=None, **data):
    employee = db.get(Employee, int(data["employee_id"]))
    company = get_company_profile(db)
    if not employee or not company:
        raise ValueError("Employee and Company Profile are required")
    month = data["payroll_month"]
    month = month if isinstance(month, date) else date.fromisoformat(str(month) + ("-01" if len(str(month)) == 7 else ""))
    month = month.replace(day=1)
    payslip = db.get(Payslip, payslip_id) if payslip_id else None
    if payslip is None:
        payslip = Payslip(employee_id=employee.id, payroll_month=month)
        db.add(payslip)
    totals = calculate(data)
    snapshot = {
        "employee_id": employee.id, "payroll_month": month,
        "employee_name": data.get("employee_name") or employee.full_name, "employee_code": data.get("employee_code") or employee.employee_code,
        "employee_email": data.get("employee_email") or employee.email, "employee_address": data.get("employee_address") or employee.address,
        "department": data.get("department") or employee.department, "designation": data.get("designation") or employee.designation,
        "join_date": employee.join_date, "company_name": company.display_name or company.legal_name,
        "company_gstin": company.gstin, "company_address": company.registered_address,
        "company_logo_path": company.logo_path, "notes": data.get("notes") or None,
        "bank_account_display": masked(data.get("bank_account_display")), "pan_display": masked(data.get("pan_display")),
        "uan_display": masked(data.get("uan_display")), "esi_display": masked(data.get("esi_display")),
    }
    for field in ("working_days", "paid_days", "lop_days"):
        snapshot[field] = money(data.get(field))
    for key, value in {**totals, **{f: money(data.get(f)) for f in EARNING_FIELDS + DEDUCTION_FIELDS}}.items():
        snapshot[key] = value
    for key, value in snapshot.items():
        setattr(payslip, key, value)
    try:
        db.commit(); db.refresh(payslip)
    except IntegrityError as exc:
        db.rollback(); raise ValueError("A payslip already exists for this employee and month") from exc
    return payslip


def render_pdf(payslip: Payslip):
    buffer = BytesIO(); styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=15*mm, bottomMargin=15*mm)
    story = [Paragraph(payslip.company_name, styles["Title"]), Paragraph(payslip.company_address or "", styles["Normal"])]
    if payslip.company_gstin: story.append(Paragraph(f"GSTIN: {payslip.company_gstin}", styles["Normal"]))
    story += [Spacer(1, 8), Paragraph(f"Payslip - {payslip.payroll_month.strftime('%B %Y')}", styles["Heading2"])]
    details = [["Employee", payslip.employee_name, "Code", payslip.employee_code], ["Department", payslip.department or "-", "Designation", payslip.designation or "-"], ["Paid Days", str(payslip.paid_days), "LOP Days", str(payslip.lop_days)]]
    table = Table(details, colWidths=[30*mm,55*mm,30*mm,55*mm]); table.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.4,colors.grey),("BACKGROUND",(0,0),(0,-1),colors.HexColor("#eef4ff")),("BACKGROUND",(2,0),(2,-1),colors.HexColor("#eef4ff")),("VALIGN",(0,0),(-1,-1),"TOP")]))
    story += [table, Spacer(1, 10)]
    rows = [["Earnings", "Amount", "Deductions", "Amount"]]
    earnings = [(LABELS[f], getattr(payslip,f)) for f in EARNING_FIELDS if getattr(payslip,f)]
    deductions = [(LABELS[f], getattr(payslip,f)) for f in DEDUCTION_FIELDS if getattr(payslip,f)]
    for i in range(max(len(earnings), len(deductions), 1)):
        e = earnings[i] if i < len(earnings) else ("", ""); d = deductions[i] if i < len(deductions) else ("", "")
        rows.append([e[0], str(e[1]), d[0], str(d[1])])
    rows.append(["Gross Earnings", str(payslip.gross_earnings), "Total Deductions", str(payslip.total_deductions)])
    pay = Table(rows, colWidths=[55*mm,30*mm,55*mm,30*mm]); pay.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.4,colors.grey),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#173b73")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("ALIGN",(1,1),(1,-1),"RIGHT"),("ALIGN",(3,1),(3,-1),"RIGHT")]))
    story += [pay, Spacer(1, 12), Paragraph(f"Net Pay: INR {payslip.net_pay:,.2f}", styles["Heading2"]), Paragraph("This is a computer-generated payslip.", styles["Normal"])]
    doc.build(story); return buffer.getvalue()


def email_payslip(payslip: Payslip, pdf: bytes):
    if not settings.smtp_password:
        raise ValueError("SMTP_PASSWORD is not configured")
    recipient = (payslip.employee_email or "").strip()
    if not recipient:
        raise ValueError("Employee email is required")
    message = EmailMessage(); message["From"] = settings.smtp_from_email; message["To"] = recipient
    message["Subject"] = f"Payslip for {payslip.payroll_month.strftime('%B %Y')} - {payslip.company_name}"
    message.set_content(f"Dear {payslip.employee_name},\n\nPlease find your payslip attached.\n\nRegards,\n{payslip.company_name}")
    message.add_attachment(pdf, maintype="application", subtype="pdf", filename=f"payslip-{payslip.employee_code}-{payslip.payroll_month:%Y-%m}.pdf")
    smtp_class = smtplib.SMTP_SSL if settings.smtp_use_ssl else smtplib.SMTP
    try:
        with smtp_class(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            if settings.smtp_use_starttls and not settings.smtp_use_ssl: smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password); smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise ValueError("Email delivery failed; verify the SMTP configuration") from exc
