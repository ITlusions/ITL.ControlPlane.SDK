"""add tenants table and tenant_id to management_groups

Revision ID: 003_add_tenants
Revises: 002_migrate_data
Create Date: 2026-02-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003_add_tenants"
down_revision: Union[str, None] = "002_migrate_data"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === Tenants table ===
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("display_name", sa.String(500), nullable=False),
        sa.Column("tenant_id", sa.String(36), unique=True, nullable=False, index=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("state", sa.String(50), nullable=False, server_default="Active"),
        sa.Column("provisioning_state", sa.String(50), nullable=False, server_default="Succeeded"),
        sa.Column("tags", postgresql.JSONB, nullable=True),
        sa.Column("properties", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # === Add tenant_id FK to management_groups ===
    op.add_column(
        "management_groups",
        sa.Column(
            "tenant_id",
            sa.String(255),
            sa.ForeignKey("tenants.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("management_groups", "tenant_id")
    op.drop_table("tenants")
