"""
Realm configuration models.

Defines specifications and configurations for identity realms.
"""

from typing import Optional, Dict, List
from datetime import datetime
from pydantic import BaseModel, Field


class RealmConfig(BaseModel):
    """Configuration for creating/updating a realm."""
    
    name: str = Field(..., min_length=1, max_length=255)
    display_name: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None, max_length=1000)
    
    # Realm policies
    enabled: bool = Field(default=True)
    password_policy: Optional[str] = Field(default="default", description="Password policy name")
    otp_policy: Optional[str] = Field(default="default", description="OTP/MFA policy name")
    
    # User management
    user_profile_enabled: bool = Field(default=True)
    user_managed_access_allowed: bool = Field(default=False)
    
    # Tenant mapping (set after realm creation)
    tenant_id: Optional[str] = Field(
        None, 
        description="Tenant ID (GUID) to link this realm to. Can be set/updated after realm creation."
    )
    
    # Custom attributes
    attributes: Optional[Dict[str, str]] = Field(default_factory=dict)
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "name": "acme-corp",
                "display_name": "ACME Production Realm",
                "description": "Production identity realm for ACME Corporation",
                "enabled": True,
                "password_policy": "default",
                "otp_policy": "default",
                "tenant_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
            }
        }


class RealmSpec(BaseModel):
    """Realm specification for creation/updates."""
    
    name: str = Field(..., min_length=1, max_length=255)
    display_name: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None, max_length=1000)
    config: RealmConfig


class RealmResponse(BaseModel):
    """Realm response model."""
    
    id: str = Field(..., description="ARM path ID")
    realm_id: str = Field(..., description="Keycloak realm ID (GUID)")
    tenant_id: Optional[str] = Field(None, description="Parent tenant ID (GUID) - can be set after creation")
    name: str
    display_name: Optional[str]
    description: Optional[str]
    enabled: bool
    is_primary: bool = Field(default=False, description="Is this the primary realm for the tenant?")
    created_at: datetime
    updated_at: datetime
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "id": "/providers/ITL.Core/tenants/acme-corp/realms/acme-corp",
                "realm_id": "123e4567-e89b-12d3-a456-426614174000",
                "tenant_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                "name": "acme-corp",
                "display_name": "ACME Production Realm",
                "enabled": True,
                "is_primary": True,
                "created_at": "2026-02-14T14:30:05Z",
                "updated_at": "2026-02-14T14:30:05Z"
            }
        }


class LinkTenantToRealmRequest(BaseModel):
    """Request to link a tenant to a realm (1:1 mapping)."""
    
    tenant_id: str = Field(..., description="Tenant ID (GUID) to link to this realm")
    is_primary: bool = Field(default=True, description="Is this the primary realm for the tenant?")
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "tenant_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                "is_primary": True
            }
        }
