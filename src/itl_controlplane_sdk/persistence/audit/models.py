"""
Pydantic models for audit events.

These models are transport-agnostic and can be serialized to JSON for
message queues or converted to SQLAlchemy models for database storage.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, List

from pydantic import BaseModel, Field, ConfigDict


class AuditAction(str, Enum):
    """CRUD action types for audit events."""
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LIST = "LIST"
    
    # Extended actions for specific operations
    ENABLE = "ENABLE"
    DISABLE = "DISABLE"
    ASSIGN = "ASSIGN"
    UNASSIGN = "UNASSIGN"
    EXECUTE = "EXECUTE"
    SYNC = "SYNC"


class ActorType(str, Enum):
    """Type of actor performing the action."""
    USER = "USER"
    SERVICE_PRINCIPAL = "SERVICE_PRINCIPAL"
    SYSTEM = "SYSTEM"
    ANONYMOUS = "ANONYMOUS"
    MANAGED_IDENTITY = "MANAGED_IDENTITY"


class AuditEvent(BaseModel):
    """
    Immutable audit event record.
    
    This is the canonical representation of an audit event that can be
    serialized to JSON for message queues or stored in databases.
    
    Attributes:
        id: Unique event ID (UUID)
        resource_id: ARM-style resource ID (e.g., /subscriptions/sub-123)
        resource_type: Resource type (e.g., ITL.Core/subscriptions)
        resource_name: Human-readable resource name
        action: CRUD action performed
        actor_id: User or service principal ID
        actor_type: Type of actor (USER, SERVICE_PRINCIPAL, SYSTEM)
        actor_display_name: Human-readable actor name (email, service name)
        timestamp: When the action occurred (UTC)
        previous_state: Resource state before the change
        new_state: Resource state after the change
        change_summary: Human-readable change description
        correlation_id: Distributed tracing correlation ID
        request_id: Original HTTP request ID
        source_ip: Source IP address
        user_agent: HTTP User-Agent header
        extra_data: Additional context for extensibility
        tenant_id: Optional tenant/organization ID for multi-tenancy
        subscription_id: Optional subscription ID for scoping
    """
    
    model_config = ConfigDict(
        frozen=True,  # Immutable
        extra="forbid",
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None,
        },
    )
    
    # Identity
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique event ID",
    )
    
    # Resource identification
    resource_id: str = Field(
        ...,
        description="ARM-style resource ID",
        examples=["/subscriptions/sub-123/resourceGroups/rg-1/providers/ITL.Core/subscriptions/my-sub"],
    )
    resource_type: str = Field(
        ...,
        description="Resource type (namespace/type)",
        examples=["ITL.Core/subscriptions", "ITL.IAM/users"],
    )
    resource_name: str = Field(
        ...,
        description="Resource name",
    )
    
    # Action
    action: AuditAction = Field(
        ...,
        description="CRUD action performed",
    )
    
    # Actor information
    actor_id: Optional[str] = Field(
        default=None,
        description="User or service principal ID",
    )
    actor_type: ActorType = Field(
        default=ActorType.SYSTEM,
        description="Type of actor",
    )
    actor_display_name: Optional[str] = Field(
        default=None,
        description="Human-readable actor name",
    )
    
    # Timestamp
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the action occurred (UTC)",
    )
    
    # State tracking (optional, for UPDATE/DELETE operations)
    previous_state: Optional[dict[str, Any]] = Field(
        default=None,
        description="Resource state before the change",
    )
    new_state: Optional[dict[str, Any]] = Field(
        default=None,
        description="Resource state after the change",
    )
    change_summary: Optional[str] = Field(
        default=None,
        description="Human-readable change description",
    )
    
    # Tracing/correlation
    correlation_id: Optional[str] = Field(
        default=None,
        description="Distributed tracing correlation ID",
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Original HTTP request ID",
    )
    
    # Additional context
    source_ip: Optional[str] = Field(
        default=None,
        description="Source IP address (IPv4 or IPv6)",
    )
    user_agent: Optional[str] = Field(
        default=None,
        description="HTTP User-Agent header",
    )
    extra_data: Optional[dict[str, Any]] = Field(
        default=None,
        description="Additional metadata",
    )
    
    # Multi-tenancy support
    tenant_id: Optional[str] = Field(
        default=None,
        description="Tenant/organization ID for multi-tenancy",
    )
    subscription_id: Optional[str] = Field(
        default=None,
        description="Subscription ID for scoping",
    )
    
    def to_routing_key(self) -> str:
        """
        Generate a routing key for message bus routing.
        
        Format: audit.{namespace}.{resource_type}.{action}
        Example: audit.itl.core.subscriptions.create
        """
        # Parse resource type: "ITL.Core/subscriptions" -> "itl.core.subscriptions"
        parts = self.resource_type.lower().replace("/", ".").replace("..", ".")
        return f"audit.{parts}.{self.action.value.lower()}"
    
    def to_message_body(self) -> dict[str, Any]:
        """Convert to dict for message serialization."""
        return self.model_dump(mode="json")
    
    @classmethod
    def for_create(
        cls,
        resource_id: str,
        resource_type: str,
        resource_name: str,
        new_state: Optional[dict[str, Any]] = None,
        actor_id: Optional[str] = None,
        actor_type: ActorType = ActorType.SYSTEM,
        **kwargs,
    ) -> AuditEvent:
        """Factory method for CREATE events."""
        return cls(
            resource_id=resource_id,
            resource_type=resource_type,
            resource_name=resource_name,
            action=AuditAction.CREATE,
            new_state=new_state,
            actor_id=actor_id,
            actor_type=actor_type,
            **kwargs,
        )
    
    @classmethod
    def for_update(
        cls,
        resource_id: str,
        resource_type: str,
        resource_name: str,
        previous_state: Optional[dict[str, Any]] = None,
        new_state: Optional[dict[str, Any]] = None,
        actor_id: Optional[str] = None,
        actor_type: ActorType = ActorType.SYSTEM,
        **kwargs,
    ) -> AuditEvent:
        """Factory method for UPDATE events."""
        return cls(
            resource_id=resource_id,
            resource_type=resource_type,
            resource_name=resource_name,
            action=AuditAction.UPDATE,
            previous_state=previous_state,
            new_state=new_state,
            actor_id=actor_id,
            actor_type=actor_type,
            **kwargs,
        )
    
    @classmethod
    def for_delete(
        cls,
        resource_id: str,
        resource_type: str,
        resource_name: str,
        previous_state: Optional[dict[str, Any]] = None,
        actor_id: Optional[str] = None,
        actor_type: ActorType = ActorType.SYSTEM,
        **kwargs,
    ) -> AuditEvent:
        """Factory method for DELETE events."""
        return cls(
            resource_id=resource_id,
            resource_type=resource_type,
            resource_name=resource_name,
            action=AuditAction.DELETE,
            previous_state=previous_state,
            actor_id=actor_id,
            actor_type=actor_type,
            **kwargs,
        )
    
    @classmethod
    def for_read(
        cls,
        resource_id: str,
        resource_type: str,
        resource_name: str,
        actor_id: Optional[str] = None,
        actor_type: ActorType = ActorType.SYSTEM,
        **kwargs,
    ) -> AuditEvent:
        """Factory method for READ events (optional, for sensitive resources)."""
        return cls(
            resource_id=resource_id,
            resource_type=resource_type,
            resource_name=resource_name,
            action=AuditAction.READ,
            actor_id=actor_id,
            actor_type=actor_type,
            **kwargs,
        )


class AuditEventQuery(BaseModel):
    """
    Query parameters for searching audit events.
    """
    
    model_config = ConfigDict(extra="forbid")
    
    # Filters
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_name: Optional[str] = None
    action: Optional[AuditAction] = None
    actor_id: Optional[str] = None
    actor_type: Optional[ActorType] = None
    correlation_id: Optional[str] = None
    tenant_id: Optional[str] = None
    subscription_id: Optional[str] = None
    
    # Time range
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Pagination
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    
    # Sorting
    order_by: str = Field(default="timestamp")
    descending: bool = Field(default=True)


class AuditEventPage(BaseModel):
    """
    Paginated response for audit event queries.
    """
    
    model_config = ConfigDict(extra="forbid")
    
    events: List[AuditEvent] = Field(default_factory=list)
    total: int = Field(default=0)
    limit: int = Field(default=100)
    offset: int = Field(default=0)
    has_more: bool = Field(default=False)
    
    @property
    def next_offset(self) -> Optional[int]:
        """Get the offset for the next page, or None if no more pages."""
        if self.has_more:
            return self.offset + self.limit
        return None
