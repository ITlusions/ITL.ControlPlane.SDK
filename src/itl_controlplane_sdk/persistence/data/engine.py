"""
SQLAlchemy 2.0 Async Storage Engine for ITL ControlPlane.

Replaces the old ``StorageBackend`` (generic nodes table + write-through
cache) with a proper SQLAlchemy engine that uses resource-specific tables,
async sessions, and optional Neo4j sync.

Usage::

    from itl_controlplane_sdk.persistence.engine import SQLAlchemyStorageEngine

    engine = SQLAlchemyStorageEngine()
    await engine.initialize()

    # Use repositories via the engine
    async with engine.session() as session:
        repo = engine.subscriptions(session)
        sub = await repo.create_or_update(name="prod", display_name="Production")
        await session.commit()

    # Or use the convenience methods
    await engine.shutdown()
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncEngine,
)

from .models import Base
from .models import ProviderResourceModel
from ..repositories import (
    TenantRepository,
    ManagementGroupRepository,
    SubscriptionRepository,
    ResourceGroupRepository,
    LocationRepository,
    ExtendedLocationRepository,
    PolicyRepository,
    TagRepository,
    DeploymentRepository,
    RelationshipRepository,
    AuditEventRepository,
)
from ..sync import Neo4jSyncService

logger = logging.getLogger(__name__)


def _build_pg_url() -> str:
    """Build async PostgreSQL connection URL from environment variables."""
    host = os.getenv("DATABASE_HOST", "localhost")
    port = os.getenv("DATABASE_PORT", "5432")
    db = os.getenv("DATABASE_NAME", "controlplane")
    user = os.getenv("DATABASE_USER", "controlplane")
    password = os.getenv("DATABASE_PASSWORD", "")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


class SQLAlchemyStorageEngine:
    """
    Central storage engine using SQLAlchemy 2.0 async ORM.

    Creates resource-specific tables, provides async session management,
    and optionally syncs to Neo4j for graph visualization.

    Configuration via environment variables:
        STORAGE_BACKEND     â€” "postgresql" (default) or "sqlite"
        DATABASE_HOST       â€” PostgreSQL host
        DATABASE_PORT       â€” PostgreSQL port  
        DATABASE_NAME       â€” Database name
        DATABASE_USER       â€” Database user
        DATABASE_PASSWORD   â€” Database password
        NEO4J_URI           â€” Neo4j bolt URI (optional, enables sync)
        NEO4J_USERNAME      â€” Neo4j username
        NEO4J_PASSWORD      â€” Neo4j password
    """

    def __init__(self):
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None
        self._neo4j_sync: Optional[Neo4jSyncService] = None
        self._initialized = False

    async def initialize(self) -> bool:
        """
        Initialize the storage engine:
        1. Create SQLAlchemy async engine + session factory
        2. Create all tables (if not exist)
        3. Connect Neo4j sync (if configured)
        
        Returns True if initialization succeeded.
        """
        backend = os.getenv("STORAGE_BACKEND", "postgresql").lower()

        try:
            if backend in ("postgresql", "postgres"):
                url = _build_pg_url()
                self._engine = create_async_engine(
                    url,
                    echo=os.getenv("SQL_ECHO", "").lower() == "true",
                    pool_size=5,
                    max_overflow=10,
                    pool_pre_ping=True,
                )
            elif backend == "sqlite":
                db_path = os.getenv("DATABASE_PATH", "/data/controlplane.db")
                url = f"sqlite+aiosqlite:///{db_path}"
                self._engine = create_async_engine(url, echo=False)
            else:
                logger.warning("Unsupported backend '%s', falling back to PostgreSQL", backend)
                url = _build_pg_url()
                self._engine = create_async_engine(url, pool_pre_ping=True)

            # Create session factory
            self._session_factory = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            # Create all tables
            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            logger.info("SQLAlchemy engine initialized: %s", backend)

            # Initialize Neo4j sync (optional)
            neo4j_uri = os.getenv("NEO4J_URI")
            if neo4j_uri:
                self._neo4j_sync = Neo4jSyncService(
                    uri=neo4j_uri,
                    username=os.getenv("NEO4J_USERNAME", "neo4j"),
                    password=os.getenv("NEO4J_PASSWORD", ""),
                    database=os.getenv("NEO4J_DATABASE", "neo4j"),
                )
                neo4j_ok = await self._neo4j_sync.connect()
                if neo4j_ok:
                    logger.info("Neo4j sync enabled: %s", neo4j_uri)
                else:
                    logger.warning("Neo4j sync connection failed â€” running without sync")
                    self._neo4j_sync = None
            else:
                logger.info("Neo4j sync not configured (set NEO4J_URI to enable)")

            self._initialized = True
            return True

        except Exception as e:
            logger.error("Storage engine initialization failed: %s", e)
            return False

    async def shutdown(self):
        """Shutdown engine and disconnect all backends."""
        if self._neo4j_sync:
            await self._neo4j_sync.disconnect()
        if self._engine:
            await self._engine.dispose()
            logger.info("Storage engine shut down")
        self._initialized = False

    @asynccontextmanager
    async def session(self):
        """
        Provide an async session context manager.

        Usage::

            async with engine.session() as session:
                repo = engine.subscriptions(session)
                subs = await repo.list_all()
                await session.commit()
        """
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    @property
    def session_factory(self) -> async_sessionmaker:
        """Expose session factory for advanced use cases."""
        return self._session_factory

    @property
    def neo4j_sync(self) -> Optional[Neo4jSyncService]:
        """Access the Neo4j sync service (may be None)."""
        return self._neo4j_sync

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    # ===================================================================
    # Repository factories â€” create repo instances for a given session
    # ===================================================================

    def tenants(self, session: AsyncSession) -> TenantRepository:
        return TenantRepository(session, self._neo4j_sync)

    def management_groups(self, session: AsyncSession) -> ManagementGroupRepository:
        return ManagementGroupRepository(session, self._neo4j_sync)

    def subscriptions(self, session: AsyncSession) -> SubscriptionRepository:
        return SubscriptionRepository(session, self._neo4j_sync)

    def resource_groups(self, session: AsyncSession) -> ResourceGroupRepository:
        return ResourceGroupRepository(session, self._neo4j_sync)

    def locations(self, session: AsyncSession) -> LocationRepository:
        return LocationRepository(session, self._neo4j_sync)

    def extended_locations(self, session: AsyncSession) -> ExtendedLocationRepository:
        return ExtendedLocationRepository(session, self._neo4j_sync)

    def policies(self, session: AsyncSession) -> PolicyRepository:
        return PolicyRepository(session, self._neo4j_sync)

    def tags(self, session: AsyncSession) -> TagRepository:
        return TagRepository(session, self._neo4j_sync)

    def deployments(self, session: AsyncSession) -> DeploymentRepository:
        return DeploymentRepository(session, self._neo4j_sync)

    def relationships(self, session: AsyncSession) -> RelationshipRepository:
        return RelationshipRepository(session, self._neo4j_sync)

    def audit_events(self, session: AsyncSession) -> AuditEventRepository:
        """Get audit events repository for logging CRUD operations."""
        return AuditEventRepository(session, self._neo4j_sync)

    # ===================================================================
    # Utility methods
    # ===================================================================

    async def seed_locations(self, default_locations: list, extended_locations: list = None):
        """Seed default locations and extended locations."""
        async with self.session() as session:
            loc_repo = self.locations(session)
            await loc_repo.seed_defaults(default_locations, extended_locations or [])

            if extended_locations:
                ext_repo = self.extended_locations(session)
                for ext in extended_locations:
                    await ext_repo.create_or_update(
                        name=ext["name"],
                        display_name=ext.get("display_name", ext["name"]),
                        shortname=ext.get("shortname"),
                        region=ext.get("region"),
                        location_type=ext.get("location_type", "EdgeZone"),
                    )

    async def seed_default_tenant(self):
        """Ensure the default ITL tenant exists. Called on startup."""
        async with self.session() as session:
            repo = self.tenants(session)
            tenant = await repo.ensure_default_tenant()
            logger.info("Default tenant ensured: %s (tenant_id=%s)", tenant.name, tenant.tenant_id)

    async def full_neo4j_sync(self):
        """Trigger a full sync of all PostgreSQL data to Neo4j."""
        if not self._neo4j_sync or not self._neo4j_sync.is_connected:
            logger.warning("Neo4j not connected â€” full sync skipped")
            return
        await self._neo4j_sync.full_sync(self._session_factory)

    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics from both PostgreSQL and Neo4j."""
        from .models import (
            TenantModel,
            ManagementGroupModel, SubscriptionModel, ResourceGroupModel,
            LocationModel, ExtendedLocationModel, PolicyModel,
            TagModel, DeploymentModel, ResourceRelationshipModel,
            AuditEventModel,
        )
        from sqlalchemy import select, func

        stats = {"postgresql": {}, "neo4j": {}}

        async with self.session() as session:
            models = {
                "tenants": TenantModel,
                "management_groups": ManagementGroupModel,
                "subscriptions": SubscriptionModel,
                "resource_groups": ResourceGroupModel,
                "locations": LocationModel,
                "extended_locations": ExtendedLocationModel,
                "policies": PolicyModel,
                "tags": TagModel,
                "deployments": DeploymentModel,
                "relationships": ResourceRelationshipModel,
                "audit_events": AuditEventModel,
            }
            total = 0
            for name, model in models.items():
                stmt = select(func.count()).select_from(model)
                result = await session.execute(stmt)
                count = result.scalar() or 0
                stats["postgresql"][name] = count
                total += count
            stats["postgresql"]["total"] = total

        if self._neo4j_sync and self._neo4j_sync.is_connected:
            stats["neo4j"] = await self._neo4j_sync.get_stats()
        else:
            stats["neo4j"] = {"connected": False}

        return stats

    # ===================================================================
    # Generic Provider Resource CRUD
    # For ResourceProvider implementations (Identity, Compute, etc.)
    # ===================================================================

    async def upsert_resource(self, resource_data: Dict[str, Any]) -> ProviderResourceModel:
        """
        Create or update a generic provider resource.
        
        Args:
            resource_data: Dict containing:
                - id: ARM-style resource ID (required)
                - name: Resource name (required)
                - type: Resource type (required, e.g., "ITL.Identity/realms")
                - location: Azure region (optional)
                - properties: JSONB properties (optional)
                - tags: Resource tags (optional)
                
        Returns:
            ProviderResourceModel instance
        """
        resource_id = resource_data["id"]
        
        # Parse resource ID to extract hierarchy
        # Format: /subscriptions/{sub}/resourceGroups/{rg}/providers/{namespace}/{type}/{name}
        parts = resource_id.split("/")
        subscription_id = None
        resource_group = None
        provider_namespace = None
        resource_type = None
        
        for i, part in enumerate(parts):
            if part == "subscriptions" and i + 1 < len(parts):
                subscription_id = parts[i + 1]
            elif part == "resourceGroups" and i + 1 < len(parts):
                resource_group = parts[i + 1]
            elif part == "providers" and i + 1 < len(parts):
                provider_namespace = parts[i + 1]
                if i + 2 < len(parts):
                    resource_type = parts[i + 2]
        
        async with self.session() as session:
            # Check if exists
            stmt = select(ProviderResourceModel).where(ProviderResourceModel.id == resource_id)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update existing
                existing.name = resource_data.get("name", existing.name)
                existing.type = resource_data.get("type", existing.type)
                existing.location = resource_data.get("location", existing.location)
                existing.properties = resource_data.get("properties", existing.properties)
                existing.tags = resource_data.get("tags", existing.tags)
                existing.provisioning_state = resource_data.get("properties", {}).get(
                    "provisioningState", existing.provisioning_state
                )
                resource = existing
            else:
                # Create new
                resource = ProviderResourceModel(
                    id=resource_id,
                    name=resource_data["name"],
                    type=resource_data.get("type", f"{provider_namespace}/{resource_type}"),
                    location=resource_data.get("location"),
                    subscription_id=subscription_id,
                    resource_group=resource_group,
                    provider_namespace=provider_namespace or "Unknown",
                    resource_type=resource_type or "unknown",
                    properties=resource_data.get("properties", {}),
                    tags=resource_data.get("tags", {}),
                    provisioning_state=resource_data.get("properties", {}).get(
                        "provisioningState", "Succeeded"
                    ),
                )
                session.add(resource)
            
            await session.commit()
            return resource

    async def get_resource(self, resource_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a generic provider resource by ID.
        
        Args:
            resource_id: ARM-style resource ID
            
        Returns:
            Resource dict or None if not found
        """
        async with self.session() as session:
            stmt = select(ProviderResourceModel).where(ProviderResourceModel.id == resource_id)
            result = await session.execute(stmt)
            resource = result.scalar_one_or_none()
            return resource.to_dict() if resource else None

    async def list_resources(
        self,
        subscription_id: str = None,
        resource_group: str = None,
        resource_type: str = None,
        provider_namespace: str = None,
    ) -> List[ProviderResourceModel]:
        """
        List generic provider resources with optional filtering.
        
        Args:
            subscription_id: Filter by subscription
            resource_group: Filter by resource group
            resource_type: Filter by resource type (e.g., "realms")
            provider_namespace: Filter by provider (e.g., "ITL.Identity")
            
        Returns:
            List of ProviderResourceModel instances
        """
        async with self.session() as session:
            stmt = select(ProviderResourceModel)
            
            if subscription_id:
                stmt = stmt.where(ProviderResourceModel.subscription_id == subscription_id)
            if resource_group:
                stmt = stmt.where(ProviderResourceModel.resource_group == resource_group)
            if resource_type:
                stmt = stmt.where(ProviderResourceModel.resource_type == resource_type)
            if provider_namespace:
                stmt = stmt.where(ProviderResourceModel.provider_namespace == provider_namespace)
            
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def delete_resource(self, resource_id: str) -> bool:
        """
        Delete a generic provider resource.
        
        Args:
            resource_id: ARM-style resource ID
            
        Returns:
            True if deleted, False if not found
        """
        async with self.session() as session:
            stmt = delete(ProviderResourceModel).where(ProviderResourceModel.id == resource_id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
