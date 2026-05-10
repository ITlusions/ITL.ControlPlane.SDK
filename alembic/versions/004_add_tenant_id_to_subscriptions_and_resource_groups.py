"""add tenant_id to subscriptions and resource_groups tables

Revision ID: 004_add_tenant_id
Revises: 01aa02d8cf05
Create Date: 2026-02-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "004_add_tenant_id"
down_revision: Union[str, None] = "01aa02d8cf05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === Add tenant_id FK to subscriptions ===
    op.add_column(
        "subscriptions",
        sa.Column(
            "tenant_id",
            sa.String(255),
            sa.ForeignKey("tenants.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )

    # === Add tenant_id FK to resource_groups ===
    op.add_column(
        "resource_groups",
        sa.Column(
            "tenant_id",
            sa.String(255),
            sa.ForeignKey("tenants.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("resource_groups", "tenant_id")
    op.drop_column("subscriptions", "tenant_id")
