"""
Locations seeding module.

Creates default Azure regions and extended locations (edge zones).
"""

from datetime import datetime
from typing import Dict
import logging
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from itl_controlplane_sdk.core.models.base.constants import DEFAULT_LOCATIONS

logger = logging.getLogger(__name__)


async def seed_locations(session: AsyncSession) -> Dict[str, int]:
    """
    Seed default Azure locations.

    Creates standard and extended (edge) locations if they don't exist.
    Includes ~18 standard locations + 6 extended locations (CDN edge zones).

    Args:
        session: AsyncSession for database operations

    Returns:
        Dictionary with operation status:
        {"created": 24, "skipped": 0, "total": 24}
    """
    now = datetime.utcnow()
    created = 0
    skipped = 0

    # Use standard locations
    all_locations = DEFAULT_LOCATIONS.copy()

    for location in all_locations:
        location_name = location.get("name")
        location_id = f"location:{location_name}"

        # Check if location already exists
        result = await session.execute(
            sa.text("SELECT id FROM locations WHERE id = :id"),
            {"id": location_id},
        )
        if result.scalar():
            skipped += 1
            continue

        # Insert location
        try:
            location_type = location.get("location_type", "Region")

            await session.execute(
                sa.text(
                    """
                    INSERT INTO locations (id, name, display_name, shortname, region,
                                         location_type, created_at, updated_at, last_action, last_action_at)
                    VALUES (:id, :name, :display_name, :shortname, :region,
                           :location_type, :created_at, :updated_at, :last_action, :last_action_at)
                    """
                ),
                {
                    "id": location_id,
                    "name": location_name,
                    "display_name": location.get("display_name", location_name),
                    "shortname": location.get("shortname", location_name[:3]),
                    "region": location.get("region", "Global"),
                    "location_type": location_type,
                    "created_at": now,
                    "updated_at": now,
                    "last_action": "CREATE",
                    "last_action_at": now,
                },
            )
            created += 1
        except Exception as e:
            logger.error(f"Failed to seed location '{location_name}': {str(e)}")
            await session.rollback()
            raise

    if created > 0:
        await session.commit()
        logger.info(f"✓ Seeded {created} locations ({skipped} already existed)")

    return {"created": created, "skipped": skipped, "total": created + skipped}
