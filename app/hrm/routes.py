from datetime import date, time
from decimal import Decimal

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.dependencies import login_required
from app.config.database import get_db
from app.hrm.service import HRMService

router = APIRouter(prefix="/hrm", dependencies=[Depends(login_required)])
templates = Jinja2Templates(directory="app/templates")
ATTENDANCE_STATUSES = {"PRESENT", "ABSENT", "HALF_DAY", "WFH"}


def optional_time(value: str):
    try:
        return time.fromisoformat(value) if value else None
    except ValueError:
        return None


def redirect_with_message(path: str, message: str, error=False):
    from urllib.parse import quote
    key = "error" if error else "success"
    separator = "&" if "?" in path else "?"
    return RedirectResponse(f"{path}{separator}{key}={quote(message)}", 303)


@router.get("", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request=request, name="hrm/dashboard.html", context={"summary": HRMService.dashboard(db), "employees": HRMService.employees(db)[:5], "leaves": HRMService.leaves(db)[:5]})


@router.get("/employees", response_class=HTMLResponse)
def employee_list(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request=request, name="hrm/employees.html", context={"employees": HRMService.employees(db)})


def employee_form_context(db, employee=None):
    data = HRMService.masters(db)
    data.update({"employee": employee, "employees": HRMService.employees(db, True)})
    return data


@router.get("/employees/create", response_class=HTMLResponse)
def employee_create_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request=request, name="hrm/employee_form.html", context=employee_form_context(db))


@router.get("/employees/{employee_id}/edit", response_class=HTMLResponse)
def employee_edit_page(employee_id: int, request: Request, db: Session = Depends(get_db)):
    employee = HRMService.employee(db, employee_id)
    if not employee:
        raise HTTPException(404, "Employee not found")
    return templates.TemplateResponse(request=request, name="hrm/employee_form.html", context=employee_form_context(db, employee))


@router.post("/employees/save")
def employee_save(employee_id: int | None = Form(None), full_name: str = Form(...), email: str = Form(""), phone: str = Form(""), department_id: int | None = Form(None), designation_id: int | None = Form(None), reporting_manager_id: int | None = Form(None), work_location_id: int | None = Form(None), employment_type: str = Form("FULL_TIME"), join_date: date = Form(...), basic_salary: Decimal = Form(0), emergency_contact: str = Form(""), address: str = Form(""), is_active: bool = Form(False), db: Session = Depends(get_db)):
    employee = HRMService.employee(db, employee_id)
    if employee_id and not employee:
        raise HTTPException(404, "Employee not found")
    try:
        HRMService.save_employee(db, employee, full_name=full_name.strip(), email=email or None, phone=phone or None, department_id=department_id, designation_id=designation_id, reporting_manager_id=reporting_manager_id, work_location_id=work_location_id, employment_type=employment_type, join_date=join_date, basic_salary=max(basic_salary, 0), emergency_contact=emergency_contact or None, address=address or None, is_active=is_active)
    except ValueError as exc:
        return redirect_with_message("/hrm/employees", str(exc), True)
    return redirect_with_message("/hrm/employees", "Employee saved")


@router.get("/attendance", response_class=HTMLResponse)
def attendance_page(request: Request, attendance_date: date | None = None, db: Session = Depends(get_db)):
    selected = attendance_date or date.today()
    return templates.TemplateResponse(request=request, name="hrm/attendance.html", context={"employees": HRMService.employees(db, True), "records": HRMService.attendance_for(db, selected), "selected_date": selected})


@router.post("/attendance/save")
def attendance_save(employee_id: int = Form(...), attendance_date: date = Form(...), status: str = Form(...), check_in: str = Form(""), check_out: str = Form(""), notes: str = Form(""), db: Session = Depends(get_db)):
    if status not in ATTENDANCE_STATUSES:
        raise HTTPException(400, "Invalid attendance status")
    if not HRMService.employee(db, employee_id):
        raise HTTPException(404, "Employee not found")
    HRMService.save_attendance(db, employee_id, attendance_date, status=status, check_in=optional_time(check_in), check_out=optional_time(check_out), notes=notes or None)
    return RedirectResponse(f"/hrm/attendance?attendance_date={attendance_date.isoformat()}", 303)


@router.get("/attendance/monthly", response_class=HTMLResponse)
def attendance_monthly(request: Request, year: int | None = None, month: int | None = None, db: Session = Depends(get_db)):
    today = date.today(); year = year or today.year; month = month or today.month
    if month < 1 or month > 12:
        raise HTTPException(400, "Invalid month")
    return templates.TemplateResponse(request=request, name="hrm/attendance_monthly.html", context={"year": year, "month": month, "summary": HRMService.attendance_month(db, year, month), "regularizations": HRMService.regularizations(db), "employees": HRMService.employees(db, True)})


@router.post("/attendance/regularizations/create")
def regularization_create(employee_id: int = Form(...), attendance_date: date = Form(...), requested_status: str = Form(...), requested_check_in: str = Form(""), requested_check_out: str = Form(""), reason: str = Form(...), db: Session = Depends(get_db)):
    if requested_status not in ATTENDANCE_STATUSES or not HRMService.employee(db, employee_id):
        raise HTTPException(400, "Invalid regularization request")
    try:
        HRMService.request_regularization(db, employee_id=employee_id, attendance_date=attendance_date, requested_status=requested_status, requested_check_in=optional_time(requested_check_in), requested_check_out=optional_time(requested_check_out), reason=reason.strip())
    except ValueError as exc:
        return redirect_with_message("/hrm/attendance/monthly", str(exc), True)
    return redirect_with_message("/hrm/attendance/monthly", "Regularization request created")


@router.post("/attendance/regularizations/{request_id}/status")
def regularization_status(request_id: int, status: str = Form(...), db: Session = Depends(get_db)):
    if status not in {"APPROVED", "REJECTED"}:
        raise HTTPException(400, "Invalid status")
    if not HRMService.review_regularization(db, request_id, status):
        raise HTTPException(404, "Pending regularization not found")
    return redirect_with_message("/hrm/attendance/monthly", f"Regularization {status.lower()}")


@router.get("/leaves", response_class=HTMLResponse)
def leave_list(request: Request, year: int | None = None, db: Session = Depends(get_db)):
    year = year or date.today().year
    return templates.TemplateResponse(request=request, name="hrm/leaves.html", context={"leaves": HRMService.leaves(db), "employees": HRMService.employees(db, True), "leave_types": HRMService.leave_types(db), "balances": HRMService.leave_balances(db, year), "year": year})


@router.post("/leaves/create")
def leave_create(employee_id: int = Form(...), leave_type_id: int = Form(...), start_date: date = Form(...), end_date: date = Form(...), reason: str = Form(""), db: Session = Depends(get_db)):
    if end_date < start_date:
        return redirect_with_message("/hrm/leaves", "End date cannot be earlier than start date", True)
    if not HRMService.employee(db, employee_id):
        raise HTTPException(404, "Employee not found")
    try:
        HRMService.create_leave(db, employee_id, leave_type_id, start_date, end_date, reason or None)
    except ValueError as exc:
        return redirect_with_message("/hrm/leaves", str(exc), True)
    return redirect_with_message("/hrm/leaves", "Leave request submitted")


@router.post("/leaves/{leave_id}/status")
def leave_status(leave_id: int, status: str = Form(...), db: Session = Depends(get_db)):
    if status not in {"APPROVED", "REJECTED", "PENDING"}:
        raise HTTPException(400, "Invalid leave status")
    try:
        if not HRMService.update_leave_status(db, leave_id, status):
            raise HTTPException(404, "Leave request not found")
    except ValueError as exc:
        return redirect_with_message("/hrm/leaves", str(exc), True)
    return redirect_with_message("/hrm/leaves", f"Leave {status.lower()}")


@router.post("/leave-balances/save")
def leave_balance_save(employee_id: int = Form(...), leave_type_id: int = Form(...), year: int = Form(...), opening: Decimal = Form(0), accrued: Decimal = Form(0), adjusted: Decimal = Form(0), db: Session = Depends(get_db)):
    HRMService.set_leave_balance(db, employee_id, leave_type_id, year, opening, accrued, adjusted)
    return redirect_with_message(f"/hrm/leaves?year={year}", "Leave balance saved")


@router.get("/holidays", response_class=HTMLResponse)
def holidays_page(request: Request, year: int | None = None, db: Session = Depends(get_db)):
    year = year or date.today().year
    return templates.TemplateResponse(request=request, name="hrm/holidays.html", context={"holidays": HRMService.holidays(db, year), "year": year})


@router.post("/holidays/create")
def holiday_create(name: str = Form(...), holiday_date: date = Form(...), category: str = Form("COMPANY"), is_optional: bool = Form(False), db: Session = Depends(get_db)):
    if category not in {"COMPANY", "NATIONAL", "STATE"}:
        raise HTTPException(400, "Invalid holiday category")
    try:
        HRMService.save_holiday(db, name=name.strip(), holiday_date=holiday_date, category=category, is_optional=is_optional)
    except ValueError as exc:
        return redirect_with_message(f"/hrm/holidays?year={holiday_date.year}", str(exc), True)
    return redirect_with_message(f"/hrm/holidays?year={holiday_date.year}", "Holiday added")


@router.get("/settings/masters", response_class=HTMLResponse)
def masters_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request=request, name="hrm/masters.html", context=HRMService.masters(db))


@router.post("/settings/masters/simple")
def simple_master_create(kind: str = Form(...), name: str = Form(...), code: str = Form(""), address: str = Form(""), db: Session = Depends(get_db)):
    try:
        HRMService.save_simple_master(db, kind, name, code, address)
    except ValueError as exc:
        return redirect_with_message("/hrm/settings/masters", str(exc), True)
    return redirect_with_message("/hrm/settings/masters", f"{kind.title()} added")


@router.post("/settings/leave-types")
def leave_type_create(code: str = Form(...), name: str = Form(...), is_paid: bool = Form(False), requires_balance: bool = Form(False), db: Session = Depends(get_db)):
    try:
        HRMService.save_leave_type(db, code, name, is_paid, requires_balance)
    except ValueError as exc:
        return redirect_with_message("/hrm/settings/masters", str(exc), True)
    return redirect_with_message("/hrm/settings/masters", "Leave type added")


@router.post("/settings/leave-policies")
def leave_policy_create(leave_type_id: int = Form(...), annual_entitlement: Decimal = Form(...), carry_forward_limit: Decimal = Form(0), effective_from: date = Form(...), db: Session = Depends(get_db)):
    try:
        HRMService.save_leave_policy(db, leave_type_id, annual_entitlement, carry_forward_limit, effective_from)
    except ValueError as exc:
        return redirect_with_message("/hrm/settings/masters", str(exc), True)
    return redirect_with_message("/hrm/settings/masters", "Leave policy added")
