"""
Data Layer — SQLAlchemy 2.0 async models and storage engine.

Modern approach using resource-specific tables, async sessions, and optional Neo4j sync.

Exports:
    Base: SQLAlchemy declarative base
    Models: TenantModel, SubscriptionModel, ResourceGroupModel, LocationModel, etc.
    SQLAlchemyStorageEngine: Central storage engine
"""

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
    AuditEventModel,
    AuditAction,
    ActorType,
)
from .engine import SQLAlchemyStorageEngine

__all__ = [
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
    "AuditAction",
    "ActorType",
    "SQLAlchemyStorageEngine",
]
