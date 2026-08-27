from datetime import date, datetime, time

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Department(Base):
    __tablename__ = "hrm_departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    code: Mapped[str | None] = mapped_column(String(30), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Designation(Base):
    __tablename__ = "hrm_designations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    code: Mapped[str | None] = mapped_column(String(30), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WorkLocation(Base):
    __tablename__ = "hrm_work_locations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    address: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Employee(Base):
    __tablename__ = "hrm_employees"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150), index=True)
    email: Mapped[str | None] = mapped_column(String(150))
    phone: Mapped[str | None] = mapped_column(String(30))
    # Legacy strings remain populated for compatibility with existing views/data.
    department: Mapped[str] = mapped_column(String(100), default="General")
    designation: Mapped[str] = mapped_column(String(100), default="Staff")
    department_id: Mapped[int | None] = mapped_column(ForeignKey("hrm_departments.id"), index=True)
    designation_id: Mapped[int | None] = mapped_column(ForeignKey("hrm_designations.id"), index=True)
    reporting_manager_id: Mapped[int | None] = mapped_column(ForeignKey("hrm_employees.id"), index=True)
    work_location_id: Mapped[int | None] = mapped_column(ForeignKey("hrm_work_locations.id"), index=True)
    employment_type: Mapped[str] = mapped_column(String(30), default="FULL_TIME")
    join_date: Mapped[date] = mapped_column(Date, default=date.today)
    basic_salary: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    emergency_contact: Mapped[str | None] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    department_master = relationship("Department")
    designation_master = relationship("Designation")
    reporting_manager = relationship("Employee", remote_side=[id], foreign_keys=[reporting_manager_id])
    work_location = relationship("WorkLocation")
    attendance_records = relationship("Attendance", back_populates="employee", cascade="all, delete-orphan")
    leave_requests = relationship("LeaveRequest", back_populates="employee", cascade="all, delete-orphan")


class Holiday(Base):
    __tablename__ = "hrm_holidays"
    __table_args__ = (UniqueConstraint("holiday_date", "name", name="uq_hrm_holiday_date_name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    holiday_date: Mapped[date] = mapped_column(Date, index=True)
    category: Mapped[str] = mapped_column(String(30), default="COMPANY")
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LeaveType(Base):
    __tablename__ = "hrm_leave_types"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    is_paid: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_balance: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LeavePolicy(Base):
    __tablename__ = "hrm_leave_policies"
    __table_args__ = (UniqueConstraint("leave_type_id", "effective_from", name="uq_hrm_leave_policy_effective"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    leave_type_id: Mapped[int] = mapped_column(ForeignKey("hrm_leave_types.id"), index=True)
    annual_entitlement: Mapped[float] = mapped_column(Numeric(6, 2), default=0)
    carry_forward_limit: Mapped[float] = mapped_column(Numeric(6, 2), default=0)
    effective_from: Mapped[date] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    leave_type = relationship("LeaveType")


class LeaveBalance(Base):
    __tablename__ = "hrm_leave_balances"
    __table_args__ = (UniqueConstraint("employee_id", "leave_type_id", "year", name="uq_hrm_leave_balance_employee_type_year"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("hrm_employees.id"), index=True)
    leave_type_id: Mapped[int] = mapped_column(ForeignKey("hrm_leave_types.id"), index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    opening_balance: Mapped[float] = mapped_column(Numeric(6, 2), default=0)
    accrued: Mapped[float] = mapped_column(Numeric(6, 2), default=0)
    used: Mapped[float] = mapped_column(Numeric(6, 2), default=0)
    adjusted: Mapped[float] = mapped_column(Numeric(6, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    employee = relationship("Employee")
    leave_type = relationship("LeaveType")

    @property
    def available(self):
        return self.opening_balance + self.accrued + self.adjusted - self.used


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


class AttendanceRegularization(Base):
    __tablename__ = "hrm_attendance_regularizations"
    __table_args__ = (UniqueConstraint("employee_id", "attendance_date", "status", name="uq_hrm_regularization_open_state"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("hrm_employees.id"), index=True)
    attendance_date: Mapped[date] = mapped_column(Date, index=True)
    requested_status: Mapped[str] = mapped_column(String(20))
    requested_check_in: Mapped[time | None] = mapped_column(Time)
    requested_check_out: Mapped[time | None] = mapped_column(Time)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    employee = relationship("Employee")


class LeaveRequest(Base):
    __tablename__ = "hrm_leave_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("hrm_employees.id"), index=True)
    leave_type: Mapped[str] = mapped_column(String(30), default="CASUAL")
    leave_type_id: Mapped[int | None] = mapped_column(ForeignKey("hrm_leave_types.id"), index=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    balance_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    employee = relationship("Employee", back_populates="leave_requests")
    leave_type_master = relationship("LeaveType")
