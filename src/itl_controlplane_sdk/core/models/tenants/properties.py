"""Tenant properties model."""
from typing import Optional
from pydantic import BaseModel, Field


class RealmConfiguration(BaseModel):
    """Configuration for the primary realm to be created with the tenant."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Realm name")
    display_name: Optional[str] = Field(None, max_length=500, description="Display name")
    description: Optional[str] = Field(None, max_length=1000, description="Description")
    enabled: bool = Field(default=True, description="Enable realm on creation")
    password_policy: Optional[str] = Field(default="default", description="Password policy")
    otp_policy: Optional[str] = Field(default="default", description="OTP/MFA policy")
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "name": "acme-corp",
                "display_name": "ACME Production Realm",
                "description": "Production identity realm",
                "enabled": True,
                "password_policy": "default"
            }
        }


class TenantProperties(BaseModel):
    """Tenant properties."""
    
    display_name: Optional[str] = Field(None, description="Display name for the tenant")
    description: Optional[str] = Field(None, description="Description of the tenant")
    state: Optional[str] = Field("Active", description="State of the tenant")
    tenant_id: Optional[str] = Field(None, description="Unique tenant identifier (UUID)")
    
    # Realm configuration: optional primary realm to create with tenant
    primary_realm_config: Optional[RealmConfiguration] = Field(
        None, 
        description="Optional configuration for the primary realm. If not provided, a default realm with tenant name will be created."
    )
