"""
Base HTTP models for the ITL ControlPlane SDK.

Contains the foundational request/response structures used across
all resource providers.
"""
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

from itl_controlplane_sdk.core.models.base.enums import ProvisioningState


class CoreBaseModel(BaseModel):
    """Base model for all Core API request/response models with shared configuration."""
    model_config = ConfigDict(json_schema_extra={})


class CoreRequestBaseModel(CoreBaseModel):
    """Base model for all Core API request models with shared fields."""
    subscription_id: str = Field(..., description="Subscription ID")
    resource_group: str = Field(..., description="Resource Group")
    provider_namespace: str = Field(default="ITL.Core", description="Provider namespace")
    resource_type: str = Field(..., description="Resource type")
    resource_name: str = Field(..., min_length=1, max_length=260, description="Resource name")
    location: str = Field(..., description="Location")
    body: Dict[str, Any] = Field(default_factory=dict, description="Request body")
    action: Optional[str] = Field(None, description="Action to perform")
    api_version: str = Field(default="2023-01-01", pattern=r"^\d{4}-\d{2}-\d{2}$", description="API version")


class ResourceMetadata(BaseModel):
    """Standard resource metadata."""
    id: str = Field(..., description="Hierarchical resource ID")
    name: str
    type: str
    location: str
    resource_group: str
    subscription_id: str
    tags: Optional[Dict[str, str]] = None
    created_time: Optional[datetime] = None
    modified_time: Optional[datetime] = None
    resource_guid: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), description="Globally unique identifier")


class ResourceRequest(CoreRequestBaseModel):
    """Standard resource request structure — inherits all fields from CoreRequestBaseModel."""
    pass


class ListResourceRequest(CoreBaseModel):
    """
    Request model for list operations.
    
    Unlike ResourceRequest, resource_name is not required for list operations.
    Follows ARM pattern: GET /subscriptions/{sub}/resourceGroups/{rg}/providers/{ns}/{type}
    """
    subscription_id: str = Field(default="", description="Subscription ID (optional for tenant-scoped)")
    resource_group: str = Field(default="", description="Resource Group (optional)")
    provider_namespace: str = Field(default="ITL.Core", description="Provider namespace")
    resource_type: str = Field(..., description="Resource type to list")
    location: str = Field(default="", description="Filter by location (optional)")
    api_version: str = Field(default="2023-01-01", pattern=r"^\d{4}-\d{2}-\d{2}$", description="API version")
    filter: Optional[str] = Field(None, description="OData $filter expression")
    top: Optional[int] = Field(None, ge=1, le=1000, description="Maximum results to return")
    skip: Optional[int] = Field(None, ge=0, description="Number of results to skip")


class ResourceResponse(CoreBaseModel):
    """Standard resource response structure."""
    id: str = Field(..., description="Hierarchical resource ID (ARM-style)")
    name: str
    type: str
    location: str
    properties: Dict[str, Any]
    tags: Optional[Dict[str, str]] = None
    provisioning_state: ProvisioningState = ProvisioningState.SUCCEEDED
    resource_guid: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), description="Globally unique identifier")


class ResourceListResponse(BaseModel):
    """Response for resource list operations."""
    value: List[ResourceResponse]
    next_link: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: Dict[str, Any]

class ProviderContext(CoreBaseModel):
    """
    Execution context for provider operations.
    
    Contains essential information about the request context, including
    tenant/organizational information, user identity, request tracing,
    and operation metadata.
    
    Every provider operation receives a ProviderContext from the control plane,
    ensuring operations are properly scoped, traceable, and auditable.
    
    Example::
    
        context = ProviderContext(
            tenant_id="tenant-123",
            user_id="user-456",
            request_id="req-789",
            subscription_id="sub-abc"
        )
        resource = await provider.create_resource(spec, context)
    
    Attributes:
        tenant_id: Multi-tenancy isolation — scopes all operations to a tenant
        user_id: Subject of the operation for audit trail
        request_id: Unique identifier for this request (for tracing)
        subscription_id: Azure subscription ID for resource scoping
        correlation_id: Optional ID to correlate across request chain
        timestamp: When the context was created
        metadata: Arbitrary context-specific data
    """
    
    tenant_id: str = Field(
        ..., 
        description="Tenant ID for multi-tenancy isolation"
    )
    user_id: str = Field(
        ..., 
        description="User ID (subject) for audit trail"
    )
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique request ID for tracing"
    )
    subscription_id: Optional[str] = Field(
        None,
        description="Azure subscription ID (if applicable)"
    )
    correlation_id: Optional[str] = Field(
        None,
        description="Correlation ID for distributed tracing"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when context was created"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context-specific metadata"
    )
    
    @property
    def trace_id(self) -> str:
        """Get trace ID — prefer correlation_id if set, else request_id."""
        return self.correlation_id or self.request_id