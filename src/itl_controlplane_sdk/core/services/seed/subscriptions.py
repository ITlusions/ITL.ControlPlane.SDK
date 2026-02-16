"""
Subscriptions seeding module.

Creates default ITLusions subscriptions.
"""

import json
from datetime import datetime
from typing import Dict, Optional, List
import logging
import uuid
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from .tenant import DEFAULT_TENANT_UUID

logger = logging.getLogger(__name__)


# Default ITLusions subscriptions seed data
DEFAULT_SUBSCRIPTIONS: List[Dict] = [
    {
        "name": "itl-prod-westeurope",
        "display_name": "ITLusions Production — West Europe",
        "description": "Production subscription for West Europe region",
        "tags": {"env": "production", "region": "westeurope"},
    },
    {
        "name": "itl-dev-westeurope",
        "display_name": "ITLusions Development — West Europe",
        "description": "Development subscription for West Europe region",
        "tags": {"env": "development", "region": "westeurope"},
    },
    {
        "name": "itl-staging-westeurope",
        "display_name": "ITLusions Staging — West Europe",
        "description": "Staging subscription for West Europe region",
        "tags": {"env": "staging", "region": "westeurope"},
    },
    {
        "name": "itl-infra-global",
        "display_name": "ITLusions Platform Infrastructure",
        "description": "Global platform infrastructure subscription",
        "tags": {"env": "shared", "purpose": "infrastructure"},
    },
    {
        "name": "itl-sandbox",
        "display_name": "ITLusions Sandbox & Experiments",
        "description": "Sandbox subscription for experiments and testing",
        "tags": {"env": "sandbox", "purpose": "experiments"},
    },
]


def generate_subscription_guid(name: str) -> str:
    """
    Generate deterministic UUID for subscription based on name.
    
    Uses UUID5 with DNS namespace to ensure consistent ID across instances.
    
    Args:
        name: Subscription name
        
    Returns:
        Deterministic UUID string
    """
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{name}.subscriptions.controlplane.itl"))


async def seed_default_subscriptions(
    session: AsyncSession, tenant_id: Optional[str] = None
) -> Dict[str, int]:
    """
    Seed default ITLusions subscriptions.

    Creates standard ITLusions subscriptions:
    - Production (West Europe)
    - Development (West Europe)
    - Staging (West Europe)
    - Infrastructure (Global)
    - Sandbox

    Args:
        session: AsyncSession for database operations
        tenant_id: Tenant ID to associate subscriptions with (defaults to DEFAULT_TENANT_UUID)

    Returns:
        Dictionary with operation status:
        {"created": N, "skipped": M}
    """
    if tenant_id is None:
        tenant_id = DEFAULT_TENANT_UUID

    now = datetime.utcnow()
    created = 0
    skipped = 0

    for sub in DEFAULT_SUBSCRIPTIONS:
        sub_name = sub["name"]
        sub_guid = generate_subscription_guid(sub_name)
        sub_id = f"subscription:{tenant_id}:{sub_name}"

        # Check if subscription already exists
        result = await session.execute(
            sa.text("SELECT id FROM subscriptions WHERE id = :id OR subscription_id = :sub_guid"),
            {"id": sub_id, "sub_guid": sub_guid},
        )
        if result.scalar():
            logger.debug(f"Subscription '{sub_name}' already exists, skipping")
            skipped += 1
            continue

        try:
            await session.execute(
                sa.text(
                    """
                    INSERT INTO subscriptions (id, name, display_name, subscription_id,
                                              tenant_id, state, provisioning_state,
                                              tags, properties, created_at, updated_at,
                                              last_action, last_action_at)
                    VALUES (:id, :name, :display_name, :subscription_id,
                           :tenant_id, :state, :provisioning_state,
                           CAST(:tags AS jsonb), CAST(:properties AS jsonb), :created_at, :updated_at,
                           :last_action, :last_action_at)
                    """
                ),
                {
                    "id": sub_id,
                    "name": sub_name,
                    "display_name": sub["display_name"],
                    "subscription_id": sub_guid,
                    "tenant_id": tenant_id,
                    "state": "Enabled",
                    "provisioning_state": "Succeeded",
                    "tags": json.dumps(sub.get("tags", {})),
                    "properties": json.dumps({"description": sub.get("description", "")}),
                    "created_at": now,
                    "updated_at": now,
                    "last_action": "CREATE",
                    "last_action_at": now,
                },
            )
            created += 1
            logger.info(f"✓ Created subscription: {sub_name} ({sub_guid})")
        except Exception as e:
            logger.error(f"Failed to create subscription '{sub_name}': {str(e)}")
            raise

    await session.commit()
    logger.info(f"Subscriptions seeding complete: {created} created, {skipped} skipped")
    return {"created": created, "skipped": skipped}
