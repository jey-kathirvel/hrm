"""HR foundation masters, leave balances, holidays and regularization."""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("hrm_departments", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(100), nullable=False), sa.Column("code", sa.String(30)), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("name"), sa.UniqueConstraint("code"))
    op.create_index("ix_hrm_departments_name", "hrm_departments", ["name"], unique=True)
    op.create_table("hrm_designations", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(100), nullable=False), sa.Column("code", sa.String(30)), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("name"), sa.UniqueConstraint("code"))
    op.create_index("ix_hrm_designations_name", "hrm_designations", ["name"], unique=True)
    op.create_table("hrm_work_locations", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(100), nullable=False), sa.Column("address", sa.Text()), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("name"))
    op.create_index("ix_hrm_work_locations_name", "hrm_work_locations", ["name"], unique=True)
    op.create_table("hrm_leave_types", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("code", sa.String(30), nullable=False), sa.Column("name", sa.String(100), nullable=False), sa.Column("is_paid", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("requires_balance", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("code"))
    op.create_index("ix_hrm_leave_types_code", "hrm_leave_types", ["code"], unique=True)
    op.create_table("hrm_holidays", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(120), nullable=False), sa.Column("holiday_date", sa.Date(), nullable=False), sa.Column("category", sa.String(30), nullable=False, server_default="COMPANY"), sa.Column("is_optional", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("holiday_date", "name", name="uq_hrm_holiday_date_name"))
    op.create_index("ix_hrm_holidays_holiday_date", "hrm_holidays", ["holiday_date"])

    for column, target in (("department_id", "hrm_departments"), ("designation_id", "hrm_designations"), ("reporting_manager_id", "hrm_employees"), ("work_location_id", "hrm_work_locations")):
        op.add_column("hrm_employees", sa.Column(column, sa.Integer()))
        op.create_foreign_key(f"fk_hrm_employees_{column}", "hrm_employees", target, [column], ["id"])
        op.create_index(f"ix_hrm_employees_{column}", "hrm_employees", [column])

    op.execute(sa.text("INSERT INTO hrm_departments (name) SELECT DISTINCT department FROM hrm_employees WHERE department IS NOT NULL AND trim(department) <> '' ON CONFLICT (name) DO NOTHING"))
    op.execute(sa.text("INSERT INTO hrm_designations (name) SELECT DISTINCT designation FROM hrm_employees WHERE designation IS NOT NULL AND trim(designation) <> '' ON CONFLICT (name) DO NOTHING"))
    op.execute(sa.text("UPDATE hrm_employees e SET department_id=d.id FROM hrm_departments d WHERE e.department=d.name"))
    op.execute(sa.text("UPDATE hrm_employees e SET designation_id=d.id FROM hrm_designations d WHERE e.designation=d.name"))
    op.execute(sa.text("INSERT INTO hrm_leave_types (code,name,is_paid,requires_balance) VALUES ('CASUAL','Casual Leave',true,true),('SICK','Sick Leave',true,true),('EARNED','Earned Leave',true,true),('UNPAID','Unpaid Leave',false,false) ON CONFLICT (code) DO NOTHING"))

    op.create_table("hrm_leave_policies", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("leave_type_id", sa.Integer(), sa.ForeignKey("hrm_leave_types.id"), nullable=False), sa.Column("annual_entitlement", sa.Numeric(6, 2), nullable=False, server_default="0"), sa.Column("carry_forward_limit", sa.Numeric(6, 2), nullable=False, server_default="0"), sa.Column("effective_from", sa.Date(), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("leave_type_id", "effective_from", name="uq_hrm_leave_policy_effective"))
    op.create_index("ix_hrm_leave_policies_leave_type_id", "hrm_leave_policies", ["leave_type_id"])
    op.create_table("hrm_leave_balances", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("employee_id", sa.Integer(), sa.ForeignKey("hrm_employees.id"), nullable=False), sa.Column("leave_type_id", sa.Integer(), sa.ForeignKey("hrm_leave_types.id"), nullable=False), sa.Column("year", sa.Integer(), nullable=False), sa.Column("opening_balance", sa.Numeric(6, 2), nullable=False, server_default="0"), sa.Column("accrued", sa.Numeric(6, 2), nullable=False, server_default="0"), sa.Column("used", sa.Numeric(6, 2), nullable=False, server_default="0"), sa.Column("adjusted", sa.Numeric(6, 2), nullable=False, server_default="0"), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("employee_id", "leave_type_id", "year", name="uq_hrm_leave_balance_employee_type_year"))
    for column in ("employee_id", "leave_type_id", "year"):
        op.create_index(f"ix_hrm_leave_balances_{column}", "hrm_leave_balances", [column])

    op.add_column("hrm_leave_requests", sa.Column("leave_type_id", sa.Integer()))
    op.add_column("hrm_leave_requests", sa.Column("balance_applied", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_foreign_key("fk_hrm_leave_requests_leave_type_id", "hrm_leave_requests", "hrm_leave_types", ["leave_type_id"], ["id"])
    op.create_index("ix_hrm_leave_requests_leave_type_id", "hrm_leave_requests", ["leave_type_id"])
    op.execute(sa.text("UPDATE hrm_leave_requests r SET leave_type_id=t.id FROM hrm_leave_types t WHERE r.leave_type=t.code"))

    op.create_table("hrm_attendance_regularizations", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("employee_id", sa.Integer(), sa.ForeignKey("hrm_employees.id"), nullable=False), sa.Column("attendance_date", sa.Date(), nullable=False), sa.Column("requested_status", sa.String(20), nullable=False), sa.Column("requested_check_in", sa.Time()), sa.Column("requested_check_out", sa.Time()), sa.Column("reason", sa.Text(), nullable=False), sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"), sa.Column("reviewed_at", sa.DateTime()), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("employee_id", "attendance_date", "status", name="uq_hrm_regularization_open_state"))
    for column in ("employee_id", "attendance_date", "status"):
        op.create_index(f"ix_hrm_attendance_regularizations_{column}", "hrm_attendance_regularizations", [column])


def downgrade():
    op.drop_table("hrm_attendance_regularizations")
    op.drop_index("ix_hrm_leave_requests_leave_type_id", table_name="hrm_leave_requests")
    op.drop_constraint("fk_hrm_leave_requests_leave_type_id", "hrm_leave_requests", type_="foreignkey")
    op.drop_column("hrm_leave_requests", "balance_applied")
    op.drop_column("hrm_leave_requests", "leave_type_id")
    op.drop_table("hrm_leave_balances")
    op.drop_table("hrm_leave_policies")
    for column in ("work_location_id", "reporting_manager_id", "designation_id", "department_id"):
        op.drop_index(f"ix_hrm_employees_{column}", table_name="hrm_employees")
        op.drop_constraint(f"fk_hrm_employees_{column}", "hrm_employees", type_="foreignkey")
        op.drop_column("hrm_employees", column)
    op.drop_table("hrm_holidays")
    op.drop_table("hrm_leave_types")
    op.drop_table("hrm_work_locations")
    op.drop_table("hrm_designations")
    op.drop_table("hrm_departments")
