"""Add manual-input payslip snapshots.

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "hrm_payslips",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("hrm_employees.id"), nullable=False),
        sa.Column("payroll_month", sa.Date(), nullable=False),
        sa.Column("employee_name", sa.String(150), nullable=False), sa.Column("employee_code", sa.String(30), nullable=False),
        sa.Column("employee_email", sa.String(150)), sa.Column("employee_address", sa.Text()),
        sa.Column("department", sa.String(100)), sa.Column("designation", sa.String(100)), sa.Column("join_date", sa.Date()),
        sa.Column("bank_account_display", sa.String(50)), sa.Column("pan_display", sa.String(20)), sa.Column("uan_display", sa.String(30)), sa.Column("esi_display", sa.String(30)),
        sa.Column("company_name", sa.String(180), nullable=False), sa.Column("company_gstin", sa.String(15)), sa.Column("company_address", sa.Text()), sa.Column("company_logo_path", sa.String(255)),
        sa.Column("working_days", sa.Numeric(6,2), nullable=False, server_default="0"), sa.Column("paid_days", sa.Numeric(6,2), nullable=False, server_default="0"), sa.Column("lop_days", sa.Numeric(6,2), nullable=False, server_default="0"),
        *[sa.Column(name, sa.Numeric(12,2), nullable=False, server_default="0") for name in ("basic","hra","special_allowance","conveyance","medical_allowance","bonus","incentive","overtime","arrears","other_earnings","employee_pf","employee_esi","professional_tax","tds","loan_advance","loss_of_pay","other_deductions","gross_earnings","total_deductions","net_pay")],
        sa.Column("notes", sa.Text()), sa.Column("last_emailed_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("employee_id", "payroll_month", name="uq_hrm_payslip_employee_month"),
    )
    op.create_index("ix_hrm_payslips_employee_id", "hrm_payslips", ["employee_id"])
    op.create_index("ix_hrm_payslips_payroll_month", "hrm_payslips", ["payroll_month"])


def downgrade():
    op.drop_table("hrm_payslips")
