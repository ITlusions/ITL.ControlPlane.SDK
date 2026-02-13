"""
Persistence Module for ITL ControlPlane SDK - SQL Data Layer.

Organized into subdirectories:
    data/           - SQLAlchemy 2.0 ORM models and storage engine
    repositories/   - Async CRUD repositories for each resource type
    sync/           - Neo4j synchronization service
    audit/          - Audit trail event system
    base/           - Base abstractions for future extensions

Provides modern SQLAlchemy 2.0 ORM approach with resource-specific tables,
async repositories, and optional Neo4j metadata sync.

Quick start::

    from itl_controlplane_sdk.persistence import SQLAlchemyStorageEngine

    engine = SQLAlchemyStorageEngine()
    await engine.initialize()

    async with engine.session() as session:
        repo = engine.subscriptions(session)
        sub = await repo.create_or_update(name="prod", display_name="Production")
"""

# Data Layer
from .data import (
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
    AuditEventModel,
    SQLAlchemyStorageEngine,
)

# Sync Layer
from .sync import Neo4jSyncService

# Repositories Layer
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
    AuditEventRepository,
)

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

__all__ = [
    # Engine & Sync
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
    "AuditEventModel",
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
    "AuditEventRepository",
]
