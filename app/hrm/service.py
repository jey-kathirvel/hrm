from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.hrm.models import Attendance, Employee, LeaveRequest


class HRMService:
    @staticmethod
    def employees(db: Session, active_only=False):
        query = db.query(Employee)
        if active_only:
            query = query.filter(Employee.is_active.is_(True))
        return query.order_by(Employee.full_name).all()

    @staticmethod
    def employee(db: Session, employee_id: int):
        return db.query(Employee).filter(Employee.id == employee_id).first()

    @staticmethod
    def save_employee(db: Session, employee=None, **data):
        if employee is None:
            next_number = (db.query(func.max(Employee.id)).scalar() or 0) + 1
            employee = Employee(employee_code=f"EMP{next_number:05d}")
            db.add(employee)
        for key, value in data.items():
            setattr(employee, key, value)
        db.commit()
        db.refresh(employee)
        return employee

    @staticmethod
    def attendance_for(db: Session, selected_date: date):
        return {
            item.employee_id: item
            for item in db.query(Attendance).filter(Attendance.attendance_date == selected_date).all()
        }

    @staticmethod
    def save_attendance(db: Session, employee_id: int, attendance_date: date, **data):
        record = db.query(Attendance).filter(
            Attendance.employee_id == employee_id,
            Attendance.attendance_date == attendance_date,
        ).first()
        if record is None:
            record = Attendance(employee_id=employee_id, attendance_date=attendance_date)
            db.add(record)
        for key, value in data.items():
            setattr(record, key, value)
        db.commit()
        return record

    @staticmethod
    def leaves(db: Session):
        return db.query(LeaveRequest).order_by(LeaveRequest.created_at.desc()).all()

    @staticmethod
    def create_leave(db: Session, **data):
        leave = LeaveRequest(**data)
        db.add(leave)
        db.commit()
        return leave

    @staticmethod
    def update_leave_status(db: Session, leave_id: int, status: str):
        leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
        if leave:
            leave.status = status
            db.commit()
        return leave

    @staticmethod
    def dashboard(db: Session):
        today = date.today()
        active = db.query(Employee).filter(Employee.is_active.is_(True)).count()
        attendance = db.query(Attendance).filter(Attendance.attendance_date == today).all()
        pending = db.query(LeaveRequest).filter(LeaveRequest.status == "PENDING").count()
        present = sum(1 for row in attendance if row.status in ("PRESENT", "WFH"))
        absent = sum(1 for row in attendance if row.status == "ABSENT")
        return {"active": active, "present": present, "absent": absent, "pending": pending, "today": today}
