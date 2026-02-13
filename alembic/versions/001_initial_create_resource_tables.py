"""create resource specific tables

Revision ID: 001_initial
Revises: None
Create Date: 2026-02-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === Management Groups ===
    op.create_table(
        "management_groups",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("display_name", sa.String(500), nullable=False),
        sa.Column("parent_id", sa.String(255),
                   sa.ForeignKey("management_groups.id", ondelete="SET NULL"),
                   nullable=True, index=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("provisioning_state", sa.String(50), nullable=False, server_default="Succeeded"),
        sa.Column("tags", postgresql.JSONB, nullable=True),
        sa.Column("properties", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # === Subscriptions ===
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("display_name", sa.String(500), nullable=False),
        sa.Column("subscription_id", sa.String(36), unique=True, nullable=False, index=True),
        sa.Column("state", sa.String(50), nullable=False, server_default="Enabled"),
        sa.Column("management_group_id", sa.String(255),
                   sa.ForeignKey("management_groups.id", ondelete="SET NULL"),
                   nullable=True, index=True),
        sa.Column("provisioning_state", sa.String(50), nullable=False, server_default="Succeeded"),
        sa.Column("tags", postgresql.JSONB, nullable=True),
        sa.Column("properties", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # === Resource Groups ===
    op.create_table(
        "resource_groups",
        sa.Column("id", sa.String(500), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("subscription_id", sa.String(255),
                   sa.ForeignKey("subscriptions.id", ondelete="CASCADE"),
                   nullable=False, index=True),
        sa.Column("location", sa.String(100), nullable=False, index=True),
        sa.Column("provisioning_state", sa.String(50), nullable=False, server_default="Succeeded"),
        sa.Column("tags", postgresql.JSONB, nullable=True),
        sa.Column("properties", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("subscription_id", "name", name="uq_rg_sub_name"),
    )

    # === Locations ===
    op.create_table(
        "locations",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("shortname", sa.String(10), nullable=True),
        sa.Column("region", sa.String(100), nullable=True, index=True),
        sa.Column("geography", sa.String(100), nullable=True),
        sa.Column("geography_group", sa.String(100), nullable=True),
        sa.Column("location_type", sa.String(50), nullable=False, server_default="Region"),
        sa.Column("latitude", sa.Float, nullable=True),
        sa.Column("longitude", sa.Float, nullable=True),
        sa.Column("physical_location", sa.String(255), nullable=True),
        sa.Column("properties", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # === Extended Locations ===
    op.create_table(
        "extended_locations",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("shortname", sa.String(10), nullable=True),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("location_type", sa.String(50), nullable=False, server_default="EdgeZone"),
        sa.Column("home_location", sa.String(100), nullable=True),
        sa.Column("properties", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # === Policies ===
    op.create_table(
        "policies",
        sa.Column("id", sa.String(500), primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("display_name", sa.String(500), nullable=True),
        sa.Column("policy_type", sa.String(50), nullable=False, server_default="Custom"),
        sa.Column("mode", sa.String(50), nullable=False, server_default="Indexed"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("rules", postgresql.JSONB, nullable=True),
        sa.Column("parameters", postgresql.JSONB, nullable=True),
        sa.Column("provisioning_state", sa.String(50), nullable=False, server_default="Succeeded"),
        sa.Column("tags", postgresql.JSONB, nullable=True),
        sa.Column("properties", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # === Tags ===
    op.create_table(
        "tags",
        sa.Column("id", sa.String(500), primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("values", postgresql.JSONB, nullable=True),
        sa.Column("provisioning_state", sa.String(50), nullable=False, server_default="Succeeded"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # === Deployments ===
    op.create_table(
        "deployments",
        sa.Column("id", sa.String(500), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("resource_group", sa.String(255), nullable=True),
        sa.Column("location", sa.String(100), nullable=True),
        sa.Column("template", postgresql.JSONB, nullable=True),
        sa.Column("parameters", postgresql.JSONB, nullable=True),
        sa.Column("mode", sa.String(50), nullable=False, server_default="Incremental"),
        sa.Column("provisioning_state", sa.String(50), nullable=False, server_default="Succeeded"),
        sa.Column("tags", postgresql.JSONB, nullable=True),
        sa.Column("properties", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # === Resource Relationships (graph edges) ===
    op.create_table(
        "resource_relationships",
        sa.Column("id", sa.String(500), primary_key=True),
        sa.Column("source_type", sa.String(100), nullable=False, index=True),
        sa.Column("source_id", sa.String(500), nullable=False, index=True),
        sa.Column("target_type", sa.String(100), nullable=False, index=True),
        sa.Column("target_id", sa.String(500), nullable=False, index=True),
        sa.Column("relationship_type", sa.String(100), nullable=False, index=True),
        sa.Column("properties", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("source_id", "target_id", "relationship_type", name="uq_relationship"),
    )
    op.create_index("idx_rel_source_type", "resource_relationships", ["source_type", "relationship_type"])
    op.create_index("idx_rel_target_type", "resource_relationships", ["target_type", "relationship_type"])


def downgrade() -> None:
    op.drop_table("resource_relationships")
    op.drop_table("deployments")
    op.drop_table("tags")
    op.drop_table("policies")
    op.drop_table("extended_locations")
    op.drop_table("locations")
    op.drop_table("resource_groups")
    op.drop_table("subscriptions")
    op.drop_table("management_groups")
