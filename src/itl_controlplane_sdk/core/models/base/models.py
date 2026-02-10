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
