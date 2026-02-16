"""
Generic resource base models for reusable request/response patterns.

Provides a common base class that all providers can inherit from to create
provider-specific request and response models with consistent field structure
and Pydantic configuration.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict


class GenericResourceBase(BaseModel):
    """
    Base class for generic resource models with common fields and configuration.
    
    Provides common schema fields (location, tags) and shared Pydantic configuration
    that can be inherited by request and response models across all providers.
    
    This base class ensures consistency across the platform while allowing
    providers to extend with their own specific fields.
    
    Example:
        class MyProviderRequest(GenericResourceBase):
            subscription_id: str
            resource_group: str
            resource_name: str
            # Additional provider-specific fields here
    """
    
    location: str = Field(..., description="Location or region")
    tags: Optional[Dict[str, str]] = Field(None, description="Resource tags for categorization")
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        arbitrary_types_allowed=True,
    )


class GenericResourceRequest(GenericResourceBase):
    """
    Generic request model for creating/updating resources.
    
    Extends GenericResourceBase with request-specific fields.
    Providers can override this with type-specific request models.
    
    Fields:
        location: Target location/region for the resource
        tags: Optional tags for resource categorization
    """
    pass


class GenericResourceResponse(BaseModel):
    """
    Generic response model for resource operations.
    
    Provides standard response fields that all providers should return.
    Includes resource identification, timestamps, and status information.
    
    Fields:
        id: Unique resource identifier
        name: Human-readable resource name
        type: Resource type classification
        location: Resource location/region
        tags: Resource tags for categorization
        provisioning_state: Current provisioning state
        created_at: Creation timestamp (UTC)
        updated_at: Last update timestamp (UTC)
        properties: Extended properties dict for provider-specific data
    """
    id: str = Field(..., description="Unique resource identifier")
    name: str = Field(..., description="Human-readable resource name")
    type: str = Field(..., description="Resource type (e.g., 'vm', 'storage')")
    location: str = Field(..., description="Resource location/region")
    tags: Optional[Dict[str, str]] = Field(None, description="Resource tags")
    provisioning_state: str = Field(default="Succeeded", description="Provisioning state")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp (UTC)")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp (UTC)")
    properties: Optional[Dict[str, Any]] = Field(None, description="Extended properties")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "00000000-0000-0000-0000-000000000001",
                "name": "my-resource",
                "type": "vm",
                "location": "eastus",
                "tags": {"env": "prod"},
                "provisioning_state": "Succeeded",
                "properties": {}
            }
        }
    )
