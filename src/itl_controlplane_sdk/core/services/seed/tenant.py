"""
Tenant seeding module.

Creates the default ITL tenant if it doesn't exist.
"""

from datetime import datetime
from typing import Dict
import logging
import uuid
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from itl_controlplane_sdk.core.models.base.constants import DEFAULT_TENANT

logger = logging.getLogger(__name__)

# Generate deterministic UUID for default tenant
# Using UUID5 with DNS namespace to ensure consistent ID across instances
DEFAULT_TENANT_UUID = str(
    uuid.uuid5(uuid.NAMESPACE_DNS, f"{DEFAULT_TENANT}.controlplane.itl")
)


async def seed_default_tenant(session: AsyncSession) -> Dict[str, int]:
    """
    Seed the default ITL tenant.

    Creates the default tenant if it doesn't exist.

    Args:
        session: AsyncSession for database operations

    Returns:
        Dictionary with count of created/skipped tenants:
        {"created": 1, "skipped": 0}
    """
    now = datetime.utcnow()

    # Check if tenant already exists
    result = await session.execute(
        sa.text("SELECT id FROM tenants WHERE id = :tenant_id"),
        {"tenant_id": DEFAULT_TENANT_UUID},
    )
    existing = result.scalar()

    if existing:
        logger.info(f"Default tenant '{DEFAULT_TENANT}' already exists, skipping")
        return {"created": 0, "skipped": 1}

    # Insert default tenant
    try:
        await session.execute(
            sa.text(
                """
                INSERT INTO tenants (id, name, display_name, tenant_id, description, 
                                    state, provisioning_state, properties, created_at, updated_at,
                                    last_action, last_action_at)
                VALUES (:id, :name, :display_name, :tenant_id, :description,
                        :state, :provisioning_state, CAST(:properties AS jsonb), :created_at, :updated_at,
                        :last_action, :last_action_at)
                """
            ),
            {
                "id": DEFAULT_TENANT_UUID,
                "name": DEFAULT_TENANT,
                "display_name": "ITL Default Tenant",
                "tenant_id": DEFAULT_TENANT_UUID,
                "description": "Default tenant for ITL ControlPlane",
                "state": "Enabled",
                "provisioning_state": "Succeeded",
                "properties": '{"default_realm": "itl-demo", "keycloak_url": "http://localhost:8080"}',
                "created_at": now,
                "updated_at": now,
                "last_action": "CREATE",
                "last_action_at": now,
            },
        )
        await session.commit()
        logger.info(f"✓ Created default tenant: {DEFAULT_TENANT} ({DEFAULT_TENANT_UUID})")
        return {"created": 1, "skipped": 0}
    except Exception as e:
        logger.error(f"Failed to seed default tenant: {str(e)}")
        await session.rollback()
        raise
