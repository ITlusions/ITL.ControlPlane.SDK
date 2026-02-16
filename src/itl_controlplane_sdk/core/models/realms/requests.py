"""Realm request models."""
from typing import Dict, Optional
from pydantic import Field, BaseModel

from itl_controlplane_sdk.core.models.base import ResourceRequest
from itl_controlplane_sdk.core.models.realm import RealmConfig, LinkTenantToRealmRequest


class CreateRealmRequest(ResourceRequest):
    """Create Realm request."""
    
    config: RealmConfig = Field(..., description="Realm configuration")
    tags: Optional[Dict[str, str]] = Field(None, description="Realm tags")


class UpdateRealmRequest(ResourceRequest):
    """Update Realm request."""
    
    config: Optional[RealmConfig] = Field(None, description="Realm configuration updates")
    tags: Optional[Dict[str, str]] = Field(None, description="Realm tags")


class LinkTenantRequest(BaseModel):
    """Request to link a tenant to a realm (set tenant_id post-creation)."""
    
    tenant_id: str = Field(..., description="Tenant ID (GUID) to link to this realm")
    is_primary: bool = Field(default=True, description="Mark as primary realm for tenant?")
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "tenant_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                "is_primary": True
            }
        }
