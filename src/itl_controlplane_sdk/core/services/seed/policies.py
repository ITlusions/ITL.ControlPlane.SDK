"""
Policies seeding module.

Creates default security and governance policies.
"""

import json
from datetime import datetime
from typing import Dict, Optional
import logging
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from .tenant import DEFAULT_TENANT_UUID

logger = logging.getLogger(__name__)


async def seed_default_policies(
    session: AsyncSession, tenant_id: Optional[str] = None
) -> Dict[str, int]:
    """
    Seed default security and governance policies.

    Creates foundational policies:
    - Enforce encryption at rest
    - Require RBAC
    - Enforce tagging
    - Audit logging

    Args:
        session: AsyncSession for database operations
        tenant_id: Tenant ID to associate policies with (defaults to DEFAULT_TENANT_UUID)

    Returns:
        Dictionary with operation status:
        {"created": 4, "skipped": 0}
    """
    if tenant_id is None:
        tenant_id = DEFAULT_TENANT_UUID

    now = datetime.utcnow()
    created = 0
    skipped = 0

    default_policies = [
        {
            "name": "enforce-encryption-at-rest",
            "display_name": "Enforce Encryption at Rest",
            "description": "All data must be encrypted at rest",
            "properties": {
                "effect": "Deny",
                "condition": "encryption.enabled == false",
            },
        },
        {
            "name": "require-rbac",
            "display_name": "Require Role-Based Access Control",
            "description": "All resources must use RBAC",
            "properties": {
                "effect": "Audit",
                "condition": "access_control.type != 'RBAC'",
            },
        },
        {
            "name": "enforce-tagging",
            "display_name": "Enforce Resource Tagging",
            "description": "All resources must have required tags",
            "properties": {
                "effect": "Deny",
                "required_tags": ["owner", "cost-center", "environment"],
            },
        },
        {
            "name": "audit-logging",
            "display_name": "Enable Audit Logging",
            "description": "All operations must be logged for audit",
            "properties": {
                "effect": "Audit",
                "log_retention_days": 90,
            },
        },
    ]

    for policy in default_policies:
        policy_name = policy["name"]
        policy_id = f"policy:{tenant_id}:{policy_name}"

        # Check if policy already exists
        result = await session.execute(
            sa.text("SELECT id FROM policies WHERE id = :id"),
            {"id": policy_id},
        )
        if result.scalar():
            skipped += 1
            continue

        try:
            await session.execute(
                sa.text(
                    """
                    INSERT INTO policies (id, name, display_name, description,
                                        policy_type, mode, rules, parameters,
                                        provisioning_state, properties,
                                        created_at, updated_at, last_action, last_action_at)
                    VALUES (:id, :name, :display_name, :description,
                           :policy_type, :mode, CAST(:rules AS jsonb), CAST(:parameters AS jsonb),
                           :provisioning_state, CAST(:properties AS jsonb),
                           :created_at, :updated_at, :last_action, :last_action_at)
                    """
                ),
                {
                    "id": policy_id,
                    "name": policy_name,
                    "display_name": policy["display_name"],
                    "description": policy.get("description", ""),
                    "policy_type": "Custom",
                    "mode": "All",
                    "rules": json.dumps(policy.get("properties", {})),
                    "parameters": json.dumps({}),
                    "provisioning_state": "Succeeded",
                    "properties": json.dumps({}),
                    "created_at": now,
                    "updated_at": now,
                    "last_action": "CREATE",
                    "last_action_at": now,
                },
            )
            created += 1
        except Exception as e:
            logger.error(f"Failed to seed policy '{policy_name}': {str(e)}")
            await session.rollback()
            raise

    if created > 0:
        await session.commit()
        logger.info(f"✓ Seeded {created} policies ({skipped} already existed)")

    return {"created": created, "skipped": skipped}
