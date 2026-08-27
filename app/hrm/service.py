from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.hrm.models import (
    Attendance, AttendanceRegularization, Department, Designation, Employee,
    Holiday, LeaveBalance, LeavePolicy, LeaveRequest, LeaveType, WorkLocation,
)


class HRMService:
    @staticmethod
    def employees(db: Session, active_only=False):
        query = db.query(Employee)
        if active_only:
            query = query.filter(Employee.is_active.is_(True))
        return query.order_by(Employee.full_name).all()

    @staticmethod
    def employee(db: Session, employee_id: int | None):
        return db.query(Employee).filter(Employee.id == employee_id).first() if employee_id else None

    @staticmethod
    def save_employee(db: Session, employee=None, **data):
        if employee is None:
            next_number = (db.query(func.max(Employee.id)).scalar() or 0) + 1
            employee = Employee(employee_code=f"EMP{next_number:05d}")
            db.add(employee)
        if employee.id is not None and data.get("reporting_manager_id") == employee.id:
            raise ValueError("An employee cannot report to themselves")
        department = db.get(Department, data.get("department_id")) if data.get("department_id") else None
        designation = db.get(Designation, data.get("designation_id")) if data.get("designation_id") else None
        data["department"] = department.name if department else data.get("department", "General")
        data["designation"] = designation.name if designation else data.get("designation", "Staff")
        for key, value in data.items():
            setattr(employee, key, value)
        db.commit()
        db.refresh(employee)
        return employee

    @staticmethod
    def masters(db: Session):
        return {
            "departments": db.query(Department).order_by(Department.name).all(),
            "designations": db.query(Designation).order_by(Designation.name).all(),
            "locations": db.query(WorkLocation).order_by(WorkLocation.name).all(),
            "leave_types": db.query(LeaveType).order_by(LeaveType.name).all(),
            "policies": db.query(LeavePolicy).order_by(LeavePolicy.effective_from.desc()).all(),
        }

    @staticmethod
    def save_simple_master(db: Session, kind: str, name: str, code=None, address=None):
        model = {"department": Department, "designation": Designation, "location": WorkLocation}.get(kind)
        if not model:
            raise ValueError("Invalid master type")
        kwargs = {"name": name.strip()}
        if model in (Department, Designation):
            kwargs["code"] = code.strip().upper() if code else None
        else:
            kwargs["address"] = address.strip() if address else None
        item = model(**kwargs)
        db.add(item)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("That master name or code already exists") from exc
        return item

    @staticmethod
    def save_leave_type(db: Session, code: str, name: str, is_paid: bool, requires_balance: bool):
        item = LeaveType(code=code.strip().upper(), name=name.strip(), is_paid=is_paid, requires_balance=requires_balance)
        db.add(item)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("That leave type code already exists") from exc
        return item

    @staticmethod
    def save_leave_policy(db: Session, leave_type_id: int, annual_entitlement: Decimal, carry_forward_limit: Decimal, effective_from: date):
        if not db.get(LeaveType, leave_type_id):
            raise ValueError("Leave type not found")
        policy = LeavePolicy(leave_type_id=leave_type_id, annual_entitlement=max(annual_entitlement, 0), carry_forward_limit=max(carry_forward_limit, 0), effective_from=effective_from)
        db.add(policy)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("A policy already exists for this type and effective date") from exc
        return policy

    @staticmethod
    def holidays(db: Session, year: int):
        return db.query(Holiday).filter(Holiday.holiday_date >= date(year, 1, 1), Holiday.holiday_date <= date(year, 12, 31)).order_by(Holiday.holiday_date).all()

    @staticmethod
    def save_holiday(db: Session, **data):
        holiday = Holiday(**data)
        db.add(holiday)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("That holiday already exists on this date") from exc
        return holiday

    @staticmethod
    def attendance_for(db: Session, selected_date: date):
        return {item.employee_id: item for item in db.query(Attendance).filter(Attendance.attendance_date == selected_date).all()}

    @staticmethod
    def attendance_month(db: Session, year: int, month: int):
        start = date(year, month, 1)
        end = date(year, month, monthrange(year, month)[1])
        records = db.query(Attendance).filter(Attendance.attendance_date.between(start, end)).all()
        summary = {}
        for employee in HRMService.employees(db, True):
            counts = {"PRESENT": 0, "ABSENT": 0, "HALF_DAY": 0, "WFH": 0}
            for record in records:
                if record.employee_id == employee.id:
                    counts[record.status] = counts.get(record.status, 0) + 1
            summary[employee] = counts
        return summary

    @staticmethod
    def save_attendance(db: Session, employee_id: int, attendance_date: date, **data):
        record = db.query(Attendance).filter(Attendance.employee_id == employee_id, Attendance.attendance_date == attendance_date).first()
        if record is None:
            record = Attendance(employee_id=employee_id, attendance_date=attendance_date)
            db.add(record)
        for key, value in data.items():
            setattr(record, key, value)
        db.commit()
        return record

    @staticmethod
    def request_regularization(db: Session, **data):
        request = AttendanceRegularization(**data)
        db.add(request)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("A pending regularization already exists for this employee and date") from exc
        return request

    @staticmethod
    def regularizations(db: Session):
        return db.query(AttendanceRegularization).order_by(AttendanceRegularization.created_at.desc()).all()

    @staticmethod
    def review_regularization(db: Session, request_id: int, status: str):
        item = db.get(AttendanceRegularization, request_id)
        if not item or item.status != "PENDING":
            return None
        item.status = status
        item.reviewed_at = datetime.utcnow()
        if status == "APPROVED":
            HRMService.save_attendance(db, item.employee_id, item.attendance_date, status=item.requested_status, check_in=item.requested_check_in, check_out=item.requested_check_out, notes="Approved regularization")
        db.commit()
        return item

    @staticmethod
    def leaves(db: Session):
        return db.query(LeaveRequest).order_by(LeaveRequest.created_at.desc()).all()

    @staticmethod
    def leave_types(db: Session, active_only=True):
        query = db.query(LeaveType)
        if active_only:
            query = query.filter(LeaveType.is_active.is_(True))
        return query.order_by(LeaveType.name).all()

    @staticmethod
    def leave_balances(db: Session, year: int):
        return db.query(LeaveBalance).filter(LeaveBalance.year == year).order_by(LeaveBalance.employee_id, LeaveBalance.leave_type_id).all()

    @staticmethod
    def set_leave_balance(db: Session, employee_id: int, leave_type_id: int, year: int, opening: Decimal, accrued: Decimal, adjusted: Decimal):
        item = db.query(LeaveBalance).filter_by(employee_id=employee_id, leave_type_id=leave_type_id, year=year).first()
        if item is None:
            item = LeaveBalance(employee_id=employee_id, leave_type_id=leave_type_id, year=year)
            db.add(item)
        item.opening_balance = opening
        item.accrued = accrued
        item.adjusted = adjusted
        db.commit()
        return item

    @staticmethod
    def create_leave(db: Session, employee_id: int, leave_type_id: int, start_date: date, end_date: date, reason=None):
        leave_type = db.get(LeaveType, leave_type_id)
        if not leave_type or not leave_type.is_active:
            raise ValueError("Leave type is not available")
        overlap = db.query(LeaveRequest).filter(LeaveRequest.employee_id == employee_id, LeaveRequest.status.in_(["PENDING", "APPROVED"]), LeaveRequest.start_date <= end_date, LeaveRequest.end_date >= start_date).first()
        if overlap:
            raise ValueError("This request overlaps an existing pending or approved leave")
        days = Decimal((end_date - start_date).days + 1)
        if leave_type.requires_balance:
            balance = db.query(LeaveBalance).filter_by(employee_id=employee_id, leave_type_id=leave_type_id, year=start_date.year).first()
            if not balance or balance.available < days:
                raise ValueError("Insufficient leave balance for this request")
        leave = LeaveRequest(employee_id=employee_id, leave_type_id=leave_type.id, leave_type=leave_type.code, start_date=start_date, end_date=end_date, reason=reason)
        db.add(leave)
        db.commit()
        return leave

    @staticmethod
    def update_leave_status(db: Session, leave_id: int, status: str):
        leave = db.get(LeaveRequest, leave_id)
        if not leave:
            return None
        days = Decimal((leave.end_date - leave.start_date).days + 1)
        leave_type = leave.leave_type_master
        if status == "APPROVED" and leave_type and leave_type.requires_balance and not leave.balance_applied:
            balance = db.query(LeaveBalance).filter_by(employee_id=leave.employee_id, leave_type_id=leave.leave_type_id, year=leave.start_date.year).with_for_update().first()
            if not balance or balance.available < days:
                raise ValueError("Insufficient leave balance to approve this request")
            balance.used += days
            leave.balance_applied = True
        elif leave.status == "APPROVED" and status != "APPROVED" and leave.balance_applied:
            balance = db.query(LeaveBalance).filter_by(employee_id=leave.employee_id, leave_type_id=leave.leave_type_id, year=leave.start_date.year).with_for_update().first()
            if balance:
                balance.used = max(balance.used - days, Decimal("0"))
            leave.balance_applied = False
        leave.status = status
        db.commit()
        return leave

    @staticmethod
    def dashboard(db: Session):
        today = date.today()
        attendance = db.query(Attendance).filter(Attendance.attendance_date == today).all()
        return {
            "active": db.query(Employee).filter(Employee.is_active.is_(True)).count(),
            "present": sum(1 for row in attendance if row.status in ("PRESENT", "WFH")),
            "absent": sum(1 for row in attendance if row.status == "ABSENT"),
            "pending": db.query(LeaveRequest).filter(LeaveRequest.status == "PENDING").count(),
            "departments": db.query(Department).filter(Department.is_active.is_(True)).count(),
            "holidays": db.query(Holiday).filter(Holiday.holiday_date >= today).count(),
            "regularizations": db.query(AttendanceRegularization).filter(AttendanceRegularization.status == "PENDING").count(),
            "today": today,
        }
