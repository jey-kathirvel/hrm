from datetime import date, datetime, time

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Employee(Base):
    __tablename__ = "hrm_employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150), index=True)
    email: Mapped[str | None] = mapped_column(String(150))
    phone: Mapped[str | None] = mapped_column(String(30))
    department: Mapped[str] = mapped_column(String(100), default="General")
    designation: Mapped[str] = mapped_column(String(100), default="Staff")
    employment_type: Mapped[str] = mapped_column(String(30), default="FULL_TIME")
    join_date: Mapped[date] = mapped_column(Date, default=date.today)
    basic_salary: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    emergency_contact: Mapped[str | None] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    attendance_records = relationship("Attendance", back_populates="employee", cascade="all, delete-orphan")
    leave_requests = relationship("LeaveRequest", back_populates="employee", cascade="all, delete-orphan")


class Attendance(Base):
    __tablename__ = "hrm_attendance"
    __table_args__ = (UniqueConstraint("employee_id", "attendance_date", name="uq_hrm_attendance_employee_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("hrm_employees.id"), index=True)
    attendance_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(20), default="PRESENT")
    check_in: Mapped[time | None] = mapped_column(Time)
    check_out: Mapped[time | None] = mapped_column(Time)
    notes: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", back_populates="attendance_records")


class LeaveRequest(Base):
    __tablename__ = "hrm_leave_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("hrm_employees.id"), index=True)
    leave_type: Mapped[str] = mapped_column(String(30), default="CASUAL")
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", back_populates="leave_requests")
