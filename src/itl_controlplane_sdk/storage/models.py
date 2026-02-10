"""
SQLAlchemy 2.0 ORM Models for ITL ControlPlane.

Resource-specific tables replacing the generic 'nodes' table.
Each resource type gets its own table with proper columns, constraints,
foreign keys, and JSONB support.

Usage::

    from itl_controlplane_sdk.storage.models import (
        Base, ManagementGroupModel, SubscriptionModel,
        ResourceGroupModel, LocationModel, PolicyModel,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
"""

from datetime import datetime
from typing import Optional, Dict, Any
import uuid

from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, Text, Boolean, Float, Integer,
    DateTime, ForeignKey, UniqueConstraint, Index,
    Enum as SAEnum, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ===================================================================
# Enums
# ===================================================================

class AuditAction(str, PyEnum):
    """Audit action types for tracking CRUD operations."""
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LIST = "LIST"


class ActorType(str, PyEnum):
    """Type of actor performing an action."""
    USER = "USER"
    SERVICE_PRINCIPAL = "SERVICE_PRINCIPAL"
    SYSTEM = "SYSTEM"
    ANONYMOUS = "ANONYMOUS"


# ===================================================================
# Base
# ===================================================================

class Base(DeclarativeBase):
    """Declarative base for all ITL ControlPlane models."""
    pass


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamps."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class TagsMixin:
    """Mixin that adds a JSONB tags column."""
    tags: Mapped[Optional[dict]] = mapped_column(
        JSONB, default=None, nullable=True
    )


class PropertiesMixin:
    """Mixin that adds a JSONB properties column for extensible data."""
    properties: Mapped[Optional[dict]] = mapped_column(
        JSONB, default=dict, nullable=True
    )


class AuditMixin:
    """
    Mixin that adds audit fields for tracking CRUD operations on resources.
    
    Fields:
        created_by: User/service ID who created the resource
        updated_by: User/service ID who last updated the resource
        last_action: Last CRUD action performed (CREATE/UPDATE/DELETE)
        last_action_at: When the last action was performed
    
    Usage:
        class MyModel(TimestampMixin, AuditMixin, Base):
            ...
    """
    created_by: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True,
        doc="User or service principal ID who created this resource",
    )
    updated_by: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True,
        doc="User or service principal ID who last updated this resource",
    )
    last_action: Mapped[str] = mapped_column(
        String(20), default=AuditAction.CREATE.value, nullable=False,
        doc="Last CRUD action: CREATE, UPDATE, DELETE",
    )
    last_action_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Timestamp of the last action",
    )


# ===================================================================
# Tenants (top-level organizational entity)
# ===================================================================

# Default tenant name — used when no tenant_id is provided
DEFAULT_TENANT_NAME = "ITL"


class TenantModel(TimestampMixin, AuditMixin, TagsMixin, PropertiesMixin, Base):
    """
    Tenant — top-level organizational entity in the hierarchy.
    
    Hierarchy: Tenant → Management Group → Subscription → Resource Group
    
    Every management group belongs to a tenant. If no tenant is specified,
    the default "ITL" tenant is used.
    """
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(500), nullable=False)
    tenant_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True,
        default=lambda: str(uuid.uuid4()),
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(50), default="Active", nullable=False)
    provisioning_state: Mapped[str] = mapped_column(
        String(50), default="Succeeded", nullable=False
    )

    # One-to-many: tenant → management_groups
    management_groups = relationship(
        "ManagementGroupModel",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    # One-to-many: tenant → subscriptions (direct link)
    subscriptions = relationship(
        "SubscriptionModel",
        back_populates="tenant",
    )
    # One-to-many: tenant → resource_groups (direct link)
    resource_groups = relationship(
        "ResourceGroupModel",
        back_populates="tenant",
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "tenant_id": self.tenant_id,
            "description": self.description,
            "state": self.state,
            "provisioning_state": self.provisioning_state,
            "tags": self.tags or {},
            "properties": self.properties or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ===================================================================
# Management Groups (self-referential hierarchy)
# ===================================================================

class ManagementGroupModel(TimestampMixin, AuditMixin, TagsMixin, PropertiesMixin, Base):
    """
    Management group — CAF hierarchy.
    
    Self-referential FK for parent_id supports the full tree structure:
    Root → Platform / Landing Zones / Sandbox / Decommissioned → ...
    """
    __tablename__ = "management_groups"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(500), nullable=False)
    parent_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        ForeignKey("management_groups.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tenant_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    provisioning_state: Mapped[str] = mapped_column(
        String(50), default="Succeeded", nullable=False
    )

    # Tenant relationship
    tenant = relationship(
        "TenantModel",
        back_populates="management_groups",
    )
    # Self-referential relationships
    parent = relationship(
        "ManagementGroupModel",
        remote_side="ManagementGroupModel.id",
        back_populates="children",
    )
    children = relationship(
        "ManagementGroupModel",
        back_populates="parent",
        cascade="all",
    )
    # One-to-many: management_group → subscriptions
    subscriptions = relationship(
        "SubscriptionModel",
        back_populates="management_group",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "tenant_id": self.tenant_id,
            "parent_id": self.parent_id,
            "description": self.description,
            "provisioning_state": self.provisioning_state,
            "tags": self.tags or {},
            "properties": self.properties or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ===================================================================
# Subscriptions
# ===================================================================

class SubscriptionModel(TimestampMixin, AuditMixin, TagsMixin, PropertiesMixin, Base):
    """
    Subscription — organizational unit for resources.
    
    Has a GUID subscription_id and belongs to a management group.
    Can be directly linked to a tenant.
    """
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(500), nullable=False)
    subscription_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True,
        default=lambda: str(uuid.uuid4()),
    )
    state: Mapped[str] = mapped_column(String(50), default="Enabled", nullable=False)
    management_group_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        ForeignKey("management_groups.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tenant_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provisioning_state: Mapped[str] = mapped_column(
        String(50), default="Succeeded", nullable=False
    )

    # Relationships
    management_group = relationship(
        "ManagementGroupModel",
        back_populates="subscriptions",
    )
    tenant = relationship(
        "TenantModel",
        back_populates="subscriptions",
    )
    resource_groups = relationship(
        "ResourceGroupModel",
        back_populates="subscription",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "subscription_id": self.subscription_id,
            "state": self.state,
            "tenant_id": self.tenant_id,
            "management_group_id": self.management_group_id,
            "provisioning_state": self.provisioning_state,
            "tags": self.tags or {},
            "properties": self.properties or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ===================================================================
# Resource Groups
# ===================================================================

class ResourceGroupModel(TimestampMixin, AuditMixin, TagsMixin, PropertiesMixin, Base):
    """
    Resource group — container for resources within a subscription.
    
    Unique per (subscription_id, name) — matches Azure behavior.
    """
    __tablename__ = "resource_groups"

    id: Mapped[str] = mapped_column(String(500), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    subscription_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    location: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    provisioning_state: Mapped[str] = mapped_column(
        String(50), default="Succeeded", nullable=False
    )

    # Unique per subscription
    __table_args__ = (
        UniqueConstraint("subscription_id", "name", name="uq_rg_sub_name"),
    )

    # Relationships
    subscription = relationship(
        "SubscriptionModel",
        back_populates="resource_groups",
    )
    tenant = relationship(
        "TenantModel",
        back_populates="resource_groups",
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "subscription_id": self.subscription_id,
            "tenant_id": self.tenant_id,
            "location": self.location,
            "provisioning_state": self.provisioning_state,
            "tags": self.tags or {},
            "properties": self.properties or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ===================================================================
# Locations
# ===================================================================

class LocationModel(TimestampMixin, AuditMixin, PropertiesMixin, Base):
    """
    Location — Azure region or ITL datacenter location.
    
    Seeded at startup with DEFAULT_LOCATIONS.
    """
    __tablename__ = "locations"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    shortname: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    geography: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    geography_group: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    location_type: Mapped[str] = mapped_column(String(50), default="Region", nullable=False)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    physical_location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "shortname": self.shortname,
            "region": self.region,
            "geography": self.geography,
            "geography_group": self.geography_group,
            "location_type": self.location_type,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "physical_location": self.physical_location,
            "properties": self.properties or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ===================================================================
# Extended Locations
# ===================================================================

class ExtendedLocationModel(TimestampMixin, AuditMixin, PropertiesMixin, Base):
    """
    Extended location — CDN edge zones, Arc locations, custom locations.
    """
    __tablename__ = "extended_locations"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    shortname: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    location_type: Mapped[str] = mapped_column(
        String(50), default="EdgeZone", nullable=False
    )
    home_location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "shortname": self.shortname,
            "region": self.region,
            "location_type": self.location_type,
            "home_location": self.home_location,
            "properties": self.properties or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ===================================================================
# Policies
# ===================================================================

class PolicyModel(TimestampMixin, AuditMixin, TagsMixin, PropertiesMixin, Base):
    """
    Policy — governance rules applied to subscriptions/management groups.
    """
    __tablename__ = "policies"

    id: Mapped[str] = mapped_column(String(500), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    policy_type: Mapped[str] = mapped_column(String(50), default="Custom", nullable=False)
    mode: Mapped[str] = mapped_column(String(50), default="Indexed", nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rules: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    parameters: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    provisioning_state: Mapped[str] = mapped_column(
        String(50), default="Succeeded", nullable=False
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "policy_type": self.policy_type,
            "mode": self.mode,
            "description": self.description,
            "rules": self.rules,
            "parameters": self.parameters,
            "provisioning_state": self.provisioning_state,
            "tags": self.tags or {},
            "properties": self.properties or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ===================================================================
# Tags
# ===================================================================

class TagModel(TimestampMixin, AuditMixin, Base):
    """
    Tag — key/value metadata applied to resources.
    """
    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(String(500), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    values: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    provisioning_state: Mapped[str] = mapped_column(
        String(50), default="Succeeded", nullable=False
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "count": self.count,
            "values": self.values or [],
            "provisioning_state": self.provisioning_state,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ===================================================================
# Deployments
# ===================================================================

class DeploymentModel(TimestampMixin, AuditMixin, TagsMixin, PropertiesMixin, Base):
    """
    Deployment — ARM-style deployment tracking.
    """
    __tablename__ = "deployments"

    id: Mapped[str] = mapped_column(String(500), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    resource_group: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    template: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    parameters: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    mode: Mapped[str] = mapped_column(String(50), default="Incremental", nullable=False)
    provisioning_state: Mapped[str] = mapped_column(
        String(50), default="Succeeded", nullable=False
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "resource_group": self.resource_group,
            "location": self.location,
            "template": self.template,
            "parameters": self.parameters,
            "mode": self.mode,
            "provisioning_state": self.provisioning_state,
            "tags": self.tags or {},
            "properties": self.properties or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ===================================================================
# Resource Relationships (graph edges)
# ===================================================================

class ResourceRelationshipModel(Base):
    """
    Relationships between resources — enables graph queries.
    
    Examples:
    - ManagementGroup CONTAINS Subscription
    - Subscription CONTAINS ResourceGroup
    - ResourceGroup DEPLOYED_IN Location
    - Subscription MANAGED_BY ManagementGroup
    """
    __tablename__ = "resource_relationships"

    id: Mapped[str] = mapped_column(
        String(500), primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    source_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_id: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    relationship_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    properties: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "source_id", "target_id", "relationship_type",
            name="uq_relationship",
        ),
        Index("idx_rel_source_type", "source_type", "relationship_type"),
        Index("idx_rel_target_type", "target_type", "relationship_type"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type,
            "properties": self.properties or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ===================================================================
# Audit Events (CRUD event log)
# ===================================================================

class AuditEventModel(Base):
    """
    Audit event log for tracking all CRUD operations on resources.
    
    Provides a complete audit trail with:
    - Full resource identification (ARM ID, type, name)
    - Actor information (who performed the action)
    - State tracking (previous and new state, configurable)
    - Correlation/tracing IDs for distributed systems
    - Metadata for extensibility
    
    Usage:
        # Log a create event
        event = AuditEventModel(
            resource_id="/subscriptions/sub-123",
            resource_type="ITL.Core/subscriptions",
            resource_name="my-subscription",
            action=AuditAction.CREATE.value,
            actor_id="user-456",
            actor_type=ActorType.USER.value,
            new_state={"name": "my-subscription", ...},
        )
        session.add(event)
    """
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    
    # Resource identification
    resource_id: Mapped[str] = mapped_column(
        String(500), nullable=False, index=True,
        doc="ARM-style resource ID (e.g., /subscriptions/sub-123)",
    )
    resource_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
        doc="Resource type (e.g., ITL.Core/subscriptions)",
    )
    resource_name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True,
        doc="Resource name",
    )
    
    # Action details
    action: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True,
        doc="CRUD action: CREATE, READ, UPDATE, DELETE, LIST",
    )
    
    # Actor information
    actor_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True,
        doc="User or service principal ID who performed the action",
    )
    actor_type: Mapped[str] = mapped_column(
        String(50), default=ActorType.SYSTEM.value, nullable=False,
        doc="Type of actor: USER, SERVICE_PRINCIPAL, SYSTEM, ANONYMOUS",
    )
    actor_display_name: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True,
        doc="Display name of the actor (e.g., email, service name)",
    )
    
    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    
    # State tracking (configurable)
    previous_state: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True,
        doc="Resource state before the change (for UPDATE/DELETE)",
    )
    new_state: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True,
        doc="Resource state after the change (for CREATE/UPDATE)",
    )
    change_summary: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        doc="Human-readable summary of the change",
    )
    
    # Tracing/correlation
    correlation_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True,
        doc="Correlation ID for distributed tracing",
    )
    request_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True,
        doc="Original request ID",
    )
    
    # Additional context
    source_ip: Mapped[Optional[str]] = mapped_column(
        String(45), nullable=True,
        doc="Source IP address (IPv4 or IPv6)",
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True,
        doc="User agent string",
    )
    extra_data: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, default=dict,
        doc="Additional metadata for extensibility",
    )

    __table_args__ = (
        Index("idx_audit_resource_action", "resource_id", "action"),
        Index("idx_audit_actor_time", "actor_id", "timestamp"),
        Index("idx_audit_type_action_time", "resource_type", "action", "timestamp"),
        Index("idx_audit_correlation", "correlation_id"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "resource_name": self.resource_name,
            "action": self.action,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "actor_display_name": self.actor_display_name,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "previous_state": self.previous_state,
            "new_state": self.new_state,
            "change_summary": self.change_summary,
            "correlation_id": self.correlation_id,
            "request_id": self.request_id,
            "source_ip": self.source_ip,
            "user_agent": self.user_agent,
            "extra_data": self.extra_data or {},
        }

    @classmethod
    def log_event(
        cls,
        resource_id: str,
        resource_type: str,
        resource_name: str,
        action: AuditAction,
        actor_id: str = None,
        actor_type: ActorType = ActorType.SYSTEM,
        actor_display_name: str = None,
        previous_state: dict = None,
        new_state: dict = None,
        change_summary: str = None,
        correlation_id: str = None,
        request_id: str = None,
        source_ip: str = None,
        user_agent: str = None,
        extra_data: dict = None,
    ) -> "AuditEventModel":
        """
        Factory method to create an audit event.
        
        Args:
            resource_id: ARM-style resource ID
            resource_type: Resource type (e.g., ITL.Core/subscriptions)
            resource_name: Resource name
            action: CRUD action (AuditAction enum)
            actor_id: User or service principal ID
            actor_type: Type of actor (ActorType enum)
            actor_display_name: Display name of actor
            previous_state: State before change (for UPDATE/DELETE)
            new_state: State after change (for CREATE/UPDATE)
            change_summary: Human-readable summary
            correlation_id: Distributed tracing correlation ID
            request_id: Original request ID
            source_ip: Source IP address
            user_agent: User agent string
            extra_data: Additional metadata
            
        Returns:
            AuditEventModel instance (not yet persisted)
        """
        return cls(
            resource_id=resource_id,
            resource_type=resource_type,
            resource_name=resource_name,
            action=action.value if isinstance(action, AuditAction) else action,
            actor_id=actor_id,
            actor_type=actor_type.value if isinstance(actor_type, ActorType) else actor_type,
            actor_display_name=actor_display_name,
            previous_state=previous_state,
            new_state=new_state,
            change_summary=change_summary,
            correlation_id=correlation_id,
            request_id=request_id,
            source_ip=source_ip,
            user_agent=user_agent,
            extra_data=extra_data or {},
        )
