from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.dependencies import login_required
from app.config.database import get_db
from app.hrm.models import Employee
from app.hrm.payroll import DEDUCTION_FIELDS, EARNING_FIELDS, LABELS, email_payslip, prefill, render_pdf, save_payslip
from app.hrm.payroll_models import Payslip

router = APIRouter(prefix="/hrm/payslips", dependencies=[Depends(login_required)])
templates = Jinja2Templates(directory="app/templates")


def go(message, error=False):
    from urllib.parse import quote
    return RedirectResponse(f"/hrm/payslips?{'error' if error else 'success'}={quote(message)}", 303)


def normalize_save_form(form):
    data = dict(form)
    raw_payslip_id = data.pop("payslip_id", "")
    return data, int(raw_payslip_id) if raw_payslip_id else None


@router.get("", response_class=HTMLResponse)
def list_page(request: Request, db: Session = Depends(get_db)):
    items = db.query(Payslip).order_by(Payslip.payroll_month.desc(), Payslip.employee_name).all()
    return templates.TemplateResponse(request=request, name="hrm/payslips.html", context={"payslips": items, "employees": db.query(Employee).filter(Employee.is_active.is_(True)).order_by(Employee.full_name).all()})


@router.get("/create", response_class=HTMLResponse)
def create_page(request: Request, employee_id: int, db: Session = Depends(get_db)):
    try: defaults = prefill(db, employee_id)
    except ValueError as exc: return go(str(exc), True)
    return templates.TemplateResponse(request=request, name="hrm/payslip_form.html", context={**defaults, "payslip": None, "earnings": EARNING_FIELDS, "deductions": DEDUCTION_FIELDS, "labels": LABELS})


@router.get("/{payslip_id}/edit", response_class=HTMLResponse)
def edit_page(payslip_id: int, request: Request, db: Session = Depends(get_db)):
    payslip = db.get(Payslip, payslip_id)
    if not payslip: raise HTTPException(404, "Payslip not found")
    return templates.TemplateResponse(request=request, name="hrm/payslip_form.html", context={"payslip": payslip, "employee": payslip.employee, "company": None, "earnings": EARNING_FIELDS, "deductions": DEDUCTION_FIELDS, "labels": LABELS})


@router.post("/save")
async def save(request: Request, db: Session = Depends(get_db)):
    try:
        data, payslip_id = normalize_save_form(await request.form())
        item = save_payslip(db, payslip_id=payslip_id, **data)
    except (ValueError, KeyError) as exc: return go(str(exc), True)
    return RedirectResponse(f"/hrm/payslips/{item.id}", 303)


@router.get("/{payslip_id}", response_class=HTMLResponse)
def view(payslip_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.get(Payslip, payslip_id)
    if not item: raise HTTPException(404, "Payslip not found")
    return templates.TemplateResponse(request=request, name="hrm/payslip_view.html", context={"payslip": item, "earnings": EARNING_FIELDS, "deductions": DEDUCTION_FIELDS, "labels": LABELS})


@router.get("/{payslip_id}/pdf")
def pdf(payslip_id: int, db: Session = Depends(get_db)):
    item = db.get(Payslip, payslip_id)
    if not item: raise HTTPException(404, "Payslip not found")
    return Response(render_pdf(item), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="payslip-{item.employee_code}-{item.payroll_month:%Y-%m}.pdf"'})


@router.post("/{payslip_id}/email")
def send_email(payslip_id: int, db: Session = Depends(get_db)):
    item = db.get(Payslip, payslip_id)
    if not item: raise HTTPException(404, "Payslip not found")
    try: email_payslip(item, render_pdf(item))
    except (ValueError, OSError) as exc: return go(str(exc), True)
    item.last_emailed_at = datetime.utcnow(); db.commit()
    return go(f"Payslip emailed to {item.employee_email}")
