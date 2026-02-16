"""Register existing Keycloak realm with ITL ControlPlane."""
from datetime import datetime
from typing import Optional
from pydantic import Field, BaseModel


class RegisterExistingRealmRequest(BaseModel):
    """Request to register/link an existing Keycloak realm with a tenant."""
    
    realm_name: str = Field(
        ..., 
        min_length=1, 
        max_length=255,
        description="Keycloak realm name (as it exists in Keycloak)"
    )
    realm_id: str = Field(
        ..., 
        description="Keycloak realm ID (GUID) - obtain from Keycloak admin console or API"
    )
    tenant_id: str = Field(
        ..., 
        description="ITL tenant ID (GUID) to link this realm to"
    )
    display_name: Optional[str] = Field(
        None,
        max_length=500,
        description="Display name for the realm in ITL"
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Description of the realm"
    )
    is_primary: bool = Field(
        default=False,
        description="Mark this as the primary realm for the tenant?"
    )
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "realm_name": "acme-corp",
                "realm_id": "123e4567-e89b-12d3-a456-426614174000",
                "tenant_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                "display_name": "ACME Production Realm",
                "description": "Existing Keycloak realm",
                "is_primary": True
            }
        }


class RegisterExistingRealmResponse(BaseModel):
    """Response after registering existing Keycloak realm."""
    
    success: bool = Field(..., description="Was registration successful?")
    message: str = Field(..., description="Status message")
    realm: Optional[dict] = Field(None, description="Created realm resource details")
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Successfully registered existing Keycloak realm",
                "realm": {
                    "id": "/providers/ITL.Core/tenants/acme-corp/realms/acme-corp",
                    "realm_id": "123e4567-e89b-12d3-a456-426614174000",
                    "tenant_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                    "name": "acme-corp",
                    "display_name": "ACME Production Realm",
                    "is_primary": True
                }
            }
        }
