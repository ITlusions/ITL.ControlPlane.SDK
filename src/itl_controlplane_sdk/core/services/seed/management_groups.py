"""
Management groups seeding module.

Creates default management group hierarchy.
"""

from datetime import datetime
from typing import Dict, Optional
import logging
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from itl_controlplane_sdk.core.models.base.constants import DEFAULT_TENANT
from .tenant import DEFAULT_TENANT_UUID

logger = logging.getLogger(__name__)


async def seed_default_management_groups(
    session: AsyncSession, tenant_id: Optional[str] = None
) -> Dict[str, int]:
    """
    Seed default management groups.

    Creates common management group hierarchy:
    - Root (tenant root)
    - Infrastructure
    - Workloads
    - Platform

    Args:
        session: AsyncSession for database operations
        tenant_id: Tenant ID to associate groups with (defaults to DEFAULT_TENANT_UUID)

    Returns:
        Dictionary with operation status:
        {"created": 4, "skipped": 0}
    """
    if tenant_id is None:
        tenant_id = DEFAULT_TENANT_UUID

    now = datetime.utcnow()
    created = 0
    skipped = 0

    default_groups = [
        {
            "name": "root",
            "display_name": "Root",
            "description": "Root management group",
        },
        {
            "name": "infrastructure",
            "display_name": "Infrastructure",
            "description": "Infrastructure and platform services",
        },
        {
            "name": "workloads",
            "display_name": "Workloads",
            "description": "Application and workload resources",
        },
        {
            "name": "platform",
            "display_name": "Platform",
            "description": "Platform integration and middleware",
        },
    ]

    for group in default_groups:
        group_name = group["name"]
        group_id = f"management-group:{tenant_id}:{group_name}"

        # Check if group already exists
        result = await session.execute(
            sa.text("SELECT id FROM management_groups WHERE id = :id"),
            {"id": group_id},
        )
        if result.scalar():
            skipped += 1
            continue

        try:
            await session.execute(
                sa.text(
                    """
                    INSERT INTO management_groups (id, name, display_name, description,
                                                  tenant_id, provisioning_state,
                                                  created_at, updated_at, last_action, last_action_at)
                    VALUES (:id, :name, :display_name, :description, :tenant_id,
                           :provisioning_state, :created_at, :updated_at, :last_action, :last_action_at)
                    """
                ),
                {
                    "id": group_id,
                    "name": group_name,
                    "display_name": group["display_name"],
                    "description": group.get("description", ""),
                    "tenant_id": tenant_id,
                    "provisioning_state": "Succeeded",
                    "created_at": now,
                    "updated_at": now,
                    "last_action": "CREATE",
                    "last_action_at": now,
                },
            )
            created += 1
        except Exception as e:
            logger.error(f"Failed to seed management group '{group_name}': {str(e)}")
            await session.rollback()
            raise

    if created > 0:
        await session.commit()
        logger.info(
            f"✓ Seeded {created} management groups ({skipped} already existed)"
        )

    return {"created": created, "skipped": skipped}
