"""
Audit events seeding module.

Creates audit log entries for seeded resources.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Optional
import logging
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from .tenant import DEFAULT_TENANT_UUID

logger = logging.getLogger(__name__)


async def seed_audit_events(
    session: AsyncSession, tenant_id: Optional[str] = None
) -> Dict[str, int]:
    """
    Seed audit events for already-seeded resources.

    Creates CREATE audit entries for:
    - Tenant
    - Locations
    - Management Groups
    - Subscriptions
    - Policies

    Args:
        session: AsyncSession for database operations
        tenant_id: Tenant ID (defaults to DEFAULT_TENANT_UUID)

    Returns:
        Dictionary with operation status:
        {"created": N, "skipped": M}
    """
    if tenant_id is None:
        tenant_id = DEFAULT_TENANT_UUID

    created = 0
    skipped = 0

    # Get all seeded resources and their timestamps
    resources_to_audit = []

    # 1. Tenant
    result = await session.execute(
        sa.text("SELECT id, name, created_at FROM tenants WHERE id = :id"),
        {"id": tenant_id},
    )
    tenant = result.fetchone()
    if tenant:
        resources_to_audit.append({
            "resource_id": tenant[0],
            "resource_type": "tenant",
            "resource_name": tenant[1],
            "timestamp": tenant[2],
            "new_state": {"name": tenant[1], "id": tenant[0]},
        })

    # 2. Locations
    result = await session.execute(
        sa.text("SELECT id, name, display_name, created_at FROM locations")
    )
    for row in result.fetchall():
        resources_to_audit.append({
            "resource_id": row[0],
            "resource_type": "location",
            "resource_name": row[1],
            "timestamp": row[3],
            "new_state": {"name": row[1], "display_name": row[2]},
        })

    # 3. Management Groups
    result = await session.execute(
        sa.text("SELECT id, name, display_name, created_at FROM management_groups")
    )
    for row in result.fetchall():
        resources_to_audit.append({
            "resource_id": row[0],
            "resource_type": "management_group",
            "resource_name": row[1],
            "timestamp": row[3],
            "new_state": {"name": row[1], "display_name": row[2]},
        })

    # 4. Subscriptions
    result = await session.execute(
        sa.text("SELECT id, name, display_name, subscription_id, created_at FROM subscriptions")
    )
    for row in result.fetchall():
        resources_to_audit.append({
            "resource_id": row[0],
            "resource_type": "subscription",
            "resource_name": row[1],
            "timestamp": row[4],
            "new_state": {
                "name": row[1],
                "display_name": row[2],
                "subscription_id": row[3],
            },
        })

    # 5. Policies
    result = await session.execute(
        sa.text("SELECT id, name, display_name, created_at FROM policies")
    )
    for row in result.fetchall():
        resources_to_audit.append({
            "resource_id": row[0],
            "resource_type": "policy",
            "resource_name": row[1],
            "timestamp": row[3],
            "new_state": {"name": row[1], "display_name": row[2]},
        })

    # Create audit events for each resource
    for resource in resources_to_audit:
        # Generate deterministic event ID based on resource
        event_id = str(uuid.uuid5(
            uuid.NAMESPACE_DNS,
            f"audit:{resource['resource_id']}:CREATE"
        ))

        # Check if audit event already exists
        result = await session.execute(
            sa.text("SELECT id FROM audit_events WHERE id = :id"),
            {"id": event_id},
        )
        if result.scalar():
            skipped += 1
            continue

        try:
            await session.execute(
                sa.text(
                    """
                    INSERT INTO audit_events (
                        id, resource_id, resource_type, resource_name,
                        action, actor_id, actor_type, actor_display_name,
                        timestamp, previous_state, new_state, change_summary,
                        correlation_id, request_id, source_ip, user_agent, extra_data
                    )
                    VALUES (
                        :id, :resource_id, :resource_type, :resource_name,
                        :action, :actor_id, :actor_type, :actor_display_name,
                        :timestamp, :previous_state, CAST(:new_state AS jsonb), :change_summary,
                        :correlation_id, :request_id, :source_ip, :user_agent, CAST(:extra_data AS jsonb)
                    )
                    """
                ),
                {
                    "id": event_id,
                    "resource_id": resource["resource_id"],
                    "resource_type": resource["resource_type"],
                    "resource_name": resource["resource_name"],
                    "action": "CREATE",
                    "actor_id": "system:seed-service",
                    "actor_type": "SYSTEM",
                    "actor_display_name": "ITL Seed Service",
                    "timestamp": resource["timestamp"],
                    "previous_state": None,
                    "new_state": json.dumps(resource["new_state"]),
                    "change_summary": f"Created {resource['resource_type']} '{resource['resource_name']}' via database seeding",
                    "correlation_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "seed-operation")),
                    "request_id": str(uuid.uuid4()),
                    "source_ip": "127.0.0.1",
                    "user_agent": "ITL-SDK-SeedService/1.0",
                    "extra_data": json.dumps({"seeded": True, "seed_version": "1.0"}),
                },
            )
            created += 1
        except Exception as e:
            logger.error(f"Failed to create audit event for {resource['resource_id']}: {str(e)}")
            raise

    await session.commit()
    logger.info(f"Audit events seeding complete: {created} created, {skipped} skipped")
    return {"created": created, "skipped": skipped}
