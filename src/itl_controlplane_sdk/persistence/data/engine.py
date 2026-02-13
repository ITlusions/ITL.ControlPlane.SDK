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
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncEngine,
)

from .models import Base
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
