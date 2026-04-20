"""
Resource Groups seeding module.

Creates default resource groups for each ITLusions subscription.
"""

import json
from datetime import datetime
from typing import Dict, Optional, List
import logging
import uuid
import sqlalchemy as sa
from sqlalchemy import exc as sa_exc
from sqlalchemy.ext.asyncio import AsyncSession

from .tenant import DEFAULT_TENANT_UUID

logger = logging.getLogger(__name__)


# Default ITLusions resource groups seed data
# Organized by subscription name -> list of RGs
DEFAULT_RESOURCE_GROUPS: Dict[str, List[Dict]] = {
    "itl-prod-westeurope": [
        {
            "name": "rg-controlplane-prod",
            "location": "westeurope",
            "tags": {"env": "production", "team": "platform", "cost-center": "CC-1001"},
            "description": "Production control plane resources",
        },
        {
            "name": "rg-workload-prod",
            "location": "westeurope",
            "tags": {"env": "production", "team": "workloads", "cost-center": "CC-1002"},
            "description": "Production workload resources",
        },
    ],
    "itl-dev-westeurope": [
        {
            "name": "rg-controlplane-dev",
            "location": "westeurope",
            "tags": {"env": "development", "team": "platform"},
            "description": "Development control plane resources",
        },
        {
            "name": "rg-application-dev",
            "location": "westeurope",
            "tags": {"env": "development", "team": "application"},
            "description": "Development application resources",
        },
    ],
    "itl-staging-westeurope": [
        {
            "name": "rg-controlplane-staging",
            "location": "westeurope",
            "tags": {"env": "staging", "team": "platform"},
            "description": "Staging control plane resources",
        },
        {
            "name": "rg-testing",
            "location": "westeurope",
            "tags": {"env": "staging", "purpose": "testing"},
            "description": "Staging testing resources",
        },
    ],
    "itl-infra-global": [
        {
            "name": "rg-infrastructure",
            "location": "westeurope",
            "tags": {"env": "shared", "purpose": "infrastructure"},
            "description": "Shared infrastructure resources",
        },
        {
            "name": "rg-monitoring",
            "location": "westeurope",
            "tags": {"env": "shared", "purpose": "monitoring", "cost-center": "CC-2001"},
            "description": "Global monitoring and observability",
        },
    ],
    "itl-sandbox": [
        {
            "name": "rg-experiments",
            "location": "westeurope",
            "tags": {"env": "sandbox", "purpose": "experiments"},
            "description": "Sandbox experimentation resources",
        },
        {
            "name": "rg-poc",
            "location": "westeurope",
            "tags": {"env": "sandbox", "purpose": "poc"},
            "description": "Proof of concept resources",
        },
    ],
}


def generate_resource_group_id(subscription_id: str, rg_name: str) -> str:
    """
    Generate deterministic ID for resource group.
    
    Args:
        subscription_id: Subscription ID (GUID)
        rg_name: Resource group name
        
    Returns:
        Deterministic resource group ID
    """
    return f"resourcegroup:{subscription_id}:{rg_name}"


async def seed_default_resource_groups(
    session: AsyncSession, tenant_id: Optional[str] = None
) -> Dict[str, int]:
    """
    Seed default ITLusions resource groups.
    
    Creates resource groups for each ITLusions subscription.
    Validates that subscriptions have already been seeded.

    Args:
        session: AsyncSession for database operations
        tenant_id: Tenant ID (defaults to DEFAULT_TENANT_UUID)

    Returns:
        Dictionary with operation status:
        {"created": N, "skipped": M, "missing_subscriptions": ["sub1", "sub2"]}
        
    Raises:
        RuntimeError: If no subscriptions exist in the tenant (dependency violation)
    """
    if tenant_id is None:
        tenant_id = DEFAULT_TENANT_UUID

    now = datetime.utcnow()
    created = 0
    skipped = 0
    missing_subscriptions = []

    # ISSUE #1 FIX: Validate subscriptions exist (dependency check)
    logger.info(f"Checking for existing subscriptions in tenant {tenant_id}...")
    
# Get map of subscription names to (subscription_uuid, subscription_resource_id)
    # subscription_uuid: The UUID stored in subscriptions.subscription_id column
    # subscription_resource_id: The full resource ID stored in subscriptions.id column
    result = await session.execute(
        sa.text("""
            SELECT name, subscription_id, id 
            FROM subscriptions 
            WHERE tenant_id = :tenant_id
        """),
        {"tenant_id": tenant_id},
    )
    subscriptions = {}
    for row in result.fetchall():
        name, sub_uuid, resource_id = row[0], row[1], row[2]
        subscriptions[name] = {"subscription_id": sub_uuid, "id": resource_id}
    
    # ISSUE #1 FIX: Check that subscriptions were found
    if not subscriptions:
        logger.error(f"❌ No subscriptions found in tenant {tenant_id}. Resource groups require subscriptions to exist.")
        logger.error(f"   Run 'seed_default_subscriptions' before running this function.")
        raise RuntimeError(
            f"No subscriptions found for tenant {tenant_id}. "
            f"Please seed subscriptions first using seed_default_subscriptions(session, '{tenant_id}')"
        )
    
    logger.info(f"  Found {len(subscriptions)} subscriptions")

    # ISSUE #2 FIX: Validate subscription names match and log FK values
    # Process each resource group definition
    expected_subscriptions = set(DEFAULT_RESOURCE_GROUPS.keys())
    actual_subscriptions = set(subscriptions.keys())
    
    # Warn about mismatches
    missing_in_db = expected_subscriptions - actual_subscriptions
    if missing_in_db:
        logger.warning(f"Expected subscriptions not found in database: {missing_in_db}")
    
    extra_in_db = actual_subscriptions - expected_subscriptions
    if extra_in_db:
        logger.debug(f"Extra subscriptions in database (no RGs defined): {extra_in_db}")
    
    for sub_name, rg_list in DEFAULT_RESOURCE_GROUPS.items():
        if sub_name not in subscriptions:
            logger.warning(f"Subscription '{sub_name}' not found in database, skipping resource groups")
            missing_subscriptions.append(sub_name)
            continue

        # Use subscription_id (UUID) for the FK column
        subscription_uuid = subscriptions[sub_name]["subscription_id"]  # UUID
        
        logger.debug(
            f"Processing RGs for subscription '{sub_name}': "
            f"subscription_id (UUID)={subscription_uuid}"
        )

        for rg_def in rg_list:
            rg_name = rg_def["name"]
            rg_id = generate_resource_group_id(subscription_uuid, rg_name)

            # Check if resource group already exists
            result = await session.execute(
                sa.text("""
                    SELECT id FROM resource_groups 
                    WHERE id = :id OR (subscription_id = :sub_id AND name = :name)
                """),
                {"id": rg_id, "sub_id": subscription_uuid, "name": rg_name},
            )
            if result.scalar():
                logger.debug(f"Resource group '{rg_name}' already exists in subscription '{sub_name}', skipping")
                skipped += 1
                continue

            try:
                # ISSUE #3 FIX: Explicit FK validation and detailed error handling
                await session.execute(
                    sa.text("""
                        INSERT INTO resource_groups (
                            id, name, subscription_id, tenant_id, location,
                            provisioning_state, tags, properties,
                            created_at, updated_at, last_action, last_action_at
                        ) VALUES (
                            :id, :name, :subscription_id, :tenant_id, :location,
                            :provisioning_state, CAST(:tags AS jsonb), 
                            CAST(:properties AS jsonb),
                            :created_at, :updated_at, :last_action, :last_action_at
                        )
                    """),
                    {
                        "id": rg_id,
                        "name": rg_name,
                        "subscription_id": subscription_uuid,  # UUID for FK column
                        "tenant_id": tenant_id,
                        "location": rg_def.get("location", "westeurope"),
                        "provisioning_state": "Succeeded",
                        "tags": json.dumps(rg_def.get("tags", {})),
                        "properties": json.dumps({
                            "description": rg_def.get("description", ""),
                        }),
                        "created_at": now,
                        "updated_at": now,
                        "last_action": "CREATE",
                        "last_action_at": now,
                    },
                )
                created += 1
                logger.info(f"✓ Created resource group: {rg_name} in subscription {sub_name}")
            except sa_exc.IntegrityError as e:
                # Foreign key constraint violation
                if "subscription_id" in str(e):
                    logger.error(
                        f"❌ Foreign key constraint violation for RG '{rg_name}' in subscription '{sub_name}'. "
                        f"Subscription FK='{subscription_id_fk}' does not exist in subscriptions table. "
                        f"Details: {str(e)}"
                    )
                    raise RuntimeError(
                        f"FK constraint: subscription_id '{subscription_id_fk}' not found. "
                        f"Ensure subscriptions are seeded correctly."
                    ) from e
                else:
                    logger.error(
                        f"❌ Database integrity error creating RG '{rg_name}' in subscription '{sub_name}': {str(e)}"
                    )
                    raise
            except Exception as e:
                logger.error(
                    f"❌ Failed to create resource group '{rg_name}' in subscription '{sub_name}': {str(e)}"
                )
                raise

    await session.commit()
    
    result_dict = {"created": created, "skipped": skipped}
    if missing_subscriptions:
        result_dict["missing_subscriptions"] = missing_subscriptions
    
    logger.info(f"Resource groups seeding complete: {created} created, {skipped} skipped")
    if missing_subscriptions:
        logger.warning(f"  Missing subscriptions: {missing_subscriptions}")
    
    return result_dict
