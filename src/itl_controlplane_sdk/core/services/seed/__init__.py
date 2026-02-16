"""
Seed service for populating initial database data.

All seed functions are idempotent and safe to call multiple times.

Usage:
    from itl_controlplane_sdk.core.services.seed import SeedService
    
    # Seed specific resources
    await SeedService.seed_default_tenant(session)
    await SeedService.seed_locations(session)
    await SeedService.seed_default_subscriptions(session)
    
    # Or seed all at once
    results = await SeedService.seed_all(session)
"""

import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from .tenant import seed_default_tenant, DEFAULT_TENANT_UUID
from .locations import seed_locations
from .management_groups import seed_default_management_groups
from .policies import seed_default_policies
from .subscriptions import seed_default_subscriptions, DEFAULT_SUBSCRIPTIONS
from .resource_groups import seed_default_resource_groups, DEFAULT_RESOURCE_GROUPS
from .audit_events import seed_audit_events

logger = logging.getLogger(__name__)


class SeedService:
    """Service providing database seeding operations."""

    @staticmethod
    async def seed_default_tenant(session: AsyncSession) -> Dict[str, int]:
        """Seed the default ITL tenant."""
        return await seed_default_tenant(session)

    @staticmethod
    async def seed_locations(session: AsyncSession) -> Dict[str, int]:
        """Seed default Azure locations."""
        return await seed_locations(session)

    @staticmethod
    async def seed_default_management_groups(
        session: AsyncSession, tenant_id: str = None
    ) -> Dict[str, int]:
        """Seed default management groups."""
        return await seed_default_management_groups(session, tenant_id)

    @staticmethod
    async def seed_default_policies(
        session: AsyncSession, tenant_id: str = None
    ) -> Dict[str, int]:
        """Seed default security and governance policies."""
        return await seed_default_policies(session, tenant_id)

    @staticmethod
    async def seed_default_subscriptions(
        session: AsyncSession, tenant_id: str = None
    ) -> Dict[str, int]:
        """Seed default ITLusions subscriptions."""
        return await seed_default_subscriptions(session, tenant_id)

    @staticmethod
    async def seed_default_resource_groups(
        session: AsyncSession, tenant_id: str = None
    ) -> Dict[str, int]:
        """Seed default resource groups for subscriptions."""
        return await seed_default_resource_groups(session, tenant_id)

    @staticmethod
    async def seed_audit_events(
        session: AsyncSession, tenant_id: str = None
    ) -> Dict[str, int]:
        """Seed audit events for seeded resources."""
        return await seed_audit_events(session, tenant_id)

    @staticmethod
    async def seed_all(
        session: AsyncSession, tenant_id: str = None
    ) -> Dict[str, Any]:
        """Seed all default data in correct order."""
        logger.info("Starting database seed process...")

        results = {}

        try:
            # Seed tenant first (required for other seeds)
            results["tenant"] = await SeedService.seed_default_tenant(session)
            logger.info(f"  Tenant: {results['tenant']}")

            # Seed locations (independent)
            results["locations"] = await SeedService.seed_locations(session)
            logger.info(f"  Locations: {results['locations']}")

            # Seed management groups (depends on tenant)
            results["management_groups"] = (
                await SeedService.seed_default_management_groups(session, tenant_id)
            )
            logger.info(f"  Management Groups: {results['management_groups']}")

            # Seed subscriptions (depends on tenant)
            results["subscriptions"] = await SeedService.seed_default_subscriptions(
                session, tenant_id
            )
            logger.info(f"  Subscriptions: {results['subscriptions']}")

            # Seed resource groups (depends on subscriptions)
            results["resource_groups"] = await SeedService.seed_default_resource_groups(
                session, tenant_id
            )
            logger.info(f"  Resource Groups: {results['resource_groups']}")

            # Seed default policies (depends on tenant)
            results["policies"] = await SeedService.seed_default_policies(
                session, tenant_id
            )
            logger.info(f"  Policies: {results['policies']}")

            # Seed audit events (depends on all other resources)
            results["audit_events"] = await SeedService.seed_audit_events(
                session, tenant_id
            )
            logger.info(f"  Audit Events: {results['audit_events']}")

            logger.info("✓ Database seeding completed successfully")
            return results

        except Exception as e:
            logger.error(f"✗ Database seeding failed: {str(e)}")
            raise


# Convenience exports for direct function use
__all__ = [
    "SeedService",
    "DEFAULT_TENANT_UUID",
    "seed_default_tenant",
    "seed_locations",
    "seed_default_management_groups",
    "seed_default_policies",
    "seed_default_subscriptions",
    "seed_default_resource_groups",
    "seed_audit_events",
    "DEFAULT_SUBSCRIPTIONS",
    "DEFAULT_RESOURCE_GROUPS",
]
