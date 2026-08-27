from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Payslip(Base):
    __tablename__ = "hrm_payslips"
    __table_args__ = (UniqueConstraint("employee_id", "payroll_month", name="uq_hrm_payslip_employee_month"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("hrm_employees.id"), index=True)
    payroll_month: Mapped[date] = mapped_column(Date, index=True)
    employee_name: Mapped[str] = mapped_column(String(150))
    employee_code: Mapped[str] = mapped_column(String(30))
    employee_email: Mapped[str | None] = mapped_column(String(150))
    employee_address: Mapped[str | None] = mapped_column(Text)
    department: Mapped[str | None] = mapped_column(String(100))
    designation: Mapped[str | None] = mapped_column(String(100))
    join_date: Mapped[date | None] = mapped_column(Date)
    bank_account_display: Mapped[str | None] = mapped_column(String(50))
    pan_display: Mapped[str | None] = mapped_column(String(20))
    uan_display: Mapped[str | None] = mapped_column(String(30))
    esi_display: Mapped[str | None] = mapped_column(String(30))
    company_name: Mapped[str] = mapped_column(String(180))
    company_gstin: Mapped[str | None] = mapped_column(String(15))
    company_address: Mapped[str | None] = mapped_column(Text)
    company_logo_path: Mapped[str | None] = mapped_column(String(255))
    working_days: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    paid_days: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    lop_days: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    basic: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    hra: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    special_allowance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    conveyance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    medical_allowance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    bonus: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    incentive: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    overtime: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    arrears: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    other_earnings: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    employee_pf: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    employee_esi: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    professional_tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    tds: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    loan_advance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    loss_of_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    other_deductions: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    gross_earnings: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total_deductions: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    net_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    last_emailed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    employee = relationship("Employee")
