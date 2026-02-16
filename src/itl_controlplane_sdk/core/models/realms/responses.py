"""Realm response models."""
from datetime import datetime
from pydantic import Field, BaseModel

from itl_controlplane_sdk.core.models.realm import RealmResponse


class CreateRealmResponse(RealmResponse):
    """Response when creating a realm."""
    
    pass


class ListRealmsResponse(BaseModel):
    """Response for listing realms."""
    
    realms: list[RealmResponse] = Field(..., description="List of realms")
    total: int = Field(..., description="Total number of realms")
    tenant_id: str = Field(..., description="Parent tenant ID")
