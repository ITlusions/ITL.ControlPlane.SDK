"""add_realms_table

Revision ID: 06bb13e9de10
Revises: 01aa02d8cf05
Create Date: 2026-02-14 10:30:00.000000

This migration creates the realms table for supporting multiple Keycloak realms
per organizational tenant, and adds primary_realm_id reference to tenants table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '06bb13e9de10'
down_revision: Union[str, None] = '01aa02d8cf05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create realms table for multi-realm per tenant support."""
    
    # Create realms table
    op.create_table(
        'realms',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False, index=True),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('realm_id', sa.String(length=36), nullable=False, unique=True, index=True),
        sa.Column('keycloak_realm_id', sa.String(length=255), nullable=True),
        sa.Column('tenant_id', sa.String(length=36), nullable=False, index=True),  # ← Updated to 36 (GUID length)
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('location', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('provisioning_state', sa.String(length=50), nullable=False, server_default='Succeeded'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.Column('updated_by', sa.String(length=255), nullable=True),
        sa.Column('last_action', sa.String(length=20), server_default='CREATE', nullable=False),
        sa.Column('last_action_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('failure_type', sa.String(length=50), nullable=True),
        sa.Column('failure_message', sa.Text(), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('properties', postgresql.JSONB(), nullable=True),
        sa.Column('tags', postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], ondelete='CASCADE'),  # ← Fixed to point to tenant_id (GUID)
        sa.UniqueConstraint('tenant_id', 'name', name='uq_tenant_realm_name'),
    )
    
    # Create composite indexes for common query patterns
    op.create_index('idx_realm_status', 'realms', ['status'])
    op.create_index('idx_realm_tenant_status', 'realms', ['tenant_id', 'status'])
    op.create_index('idx_realm_created_by', 'realms', ['created_by'], unique=False)
    op.create_index('idx_realm_updated_by', 'realms', ['updated_by'], unique=False)
    
    # Add primary_realm_id to tenants table
    op.add_column('tenants', sa.Column('primary_realm_id', sa.String(length=255), nullable=True))
    op.create_index('idx_tenant_primary_realm', 'tenants', ['primary_realm_id'])


def downgrade() -> None:
    """Revert realms table creation and tenant changes."""
    
    # Drop primary_realm_id from tenants
    op.drop_index('idx_tenant_primary_realm', table_name='tenants')
    op.drop_column('tenants', 'primary_realm_id')
    
    # Drop realms table and indexes
    op.drop_index('idx_realm_updated_by', table_name='realms')
    op.drop_index('idx_realm_created_by', table_name='realms')
    op.drop_index('idx_realm_tenant_status', table_name='realms')
    op.drop_index('idx_realm_status', table_name='realms')
    op.drop_table('realms')
