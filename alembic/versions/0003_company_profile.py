"""Add singleton company profile for payslip identity.

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "hrm_company_profile",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("legal_name", sa.String(180), nullable=False),
        sa.Column("display_name", sa.String(180)),
        sa.Column("gstin", sa.String(15)),
        sa.Column("registered_address", sa.Text()),
        sa.Column("city", sa.String(100)),
        sa.Column("state", sa.String(100)),
        sa.Column("postal_code", sa.String(10)),
        sa.Column("phone", sa.String(30)),
        sa.Column("email", sa.String(150)),
        sa.Column("website", sa.String(255)),
        sa.Column("logo_path", sa.String(255)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("id = 1", name="ck_hrm_company_profile_singleton"),
        sa.UniqueConstraint("gstin", name="uq_hrm_company_profile_gstin"),
    )


def downgrade():
    op.drop_table("hrm_company_profile")
