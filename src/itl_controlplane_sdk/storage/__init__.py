"""
Storage Module for ITL ControlPlane SDK.

Provides two storage approaches:

1. **Legacy (dict-like stores)**: Write-through cache over generic nodes table.
   Use ``StorageBackend``, ``ResourceStore``, ``TupleResourceStore``.

2. **SQLAlchemy 2.0 ORM (recommended)**: Resource-specific tables with proper
   constraints, repositories, and optional Neo4j sync (Option B).
   Use ``SQLAlchemyStorageEngine`` and the repository classes.

Quick start (new — SQLAlchemy)::

    from itl_controlplane_sdk.storage import SQLAlchemyStorageEngine

    engine = SQLAlchemyStorageEngine()
    await engine.initialize()

    async with engine.session() as session:
        repo = engine.subscriptions(session)
        sub = await repo.create_or_update(name="prod", display_name="Production")

Quick start (legacy — dict-like)::

    from itl_controlplane_sdk.storage import StorageBackend
    from itl_controlplane_sdk.graphdb import NodeType

    storage = StorageBackend()
    storage.register_store("subscriptions", NodeType.SUBSCRIPTION)
    await storage.initialize()
"""

from .resource_store import ResourceStore, TupleResourceStore
from .backend import StorageBackend
from .engine import SQLAlchemyStorageEngine
from .neo4j_sync import Neo4jSyncService

# Audit Event System (adapters + publisher)
from .audit import (
    AuditEvent,
    AuditAction,
    ActorType,
    AuditEventQuery,
    AuditEventPage,
    AuditEventAdapter,
    SQLAuditEventAdapter,
    RabbitMQAuditEventAdapter,
    CompositeAuditEventAdapter,
    InMemoryAuditEventAdapter,
    NoOpAuditEventAdapter,
    AuditEventPublisher,
)

# Models
from .models import (
    Base,
    DEFAULT_TENANT_NAME,
    TenantModel,
    ManagementGroupModel,
    SubscriptionModel,
    ResourceGroupModel,
    LocationModel,
    ExtendedLocationModel,
    PolicyModel,
    TagModel,
    DeploymentModel,
    ResourceRelationshipModel,
)

# Repositories
from .repositories import (
    BaseRepository,
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
)

__all__ = [
    # Legacy
    "StorageBackend",
    "ResourceStore",
    "TupleResourceStore",
    # Engine (new)
    "SQLAlchemyStorageEngine",
    "Neo4jSyncService",
    # Audit Event System
    "AuditEvent",
    "AuditAction",
    "ActorType",
    "AuditEventQuery",
    "AuditEventPage",
    "AuditEventAdapter",
    "SQLAuditEventAdapter",
    "RabbitMQAuditEventAdapter",
    "CompositeAuditEventAdapter",
    "InMemoryAuditEventAdapter",
    "NoOpAuditEventAdapter",
    "AuditEventPublisher",
    # Models
    "Base",
    "DEFAULT_TENANT_NAME",
    "TenantModel",
    "ManagementGroupModel",
    "SubscriptionModel",
    "ResourceGroupModel",
    "LocationModel",
    "ExtendedLocationModel",
    "PolicyModel",
    "TagModel",
    "DeploymentModel",
    "ResourceRelationshipModel",
    # Repositories
    "BaseRepository",
    "TenantRepository",
    "ManagementGroupRepository",
    "SubscriptionRepository",
    "ResourceGroupRepository",
    "LocationRepository",
    "ExtendedLocationRepository",
    "PolicyRepository",
    "TagRepository",
    "DeploymentRepository",
    "RelationshipRepository",
]
