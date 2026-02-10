"""Tenant properties model."""
from typing import Optional
from pydantic import BaseModel, Field


class TenantProperties(BaseModel):
    """Tenant properties."""
    display_name: Optional[str] = Field(None, description="Display name for the tenant")
    description: Optional[str] = Field(None, description="Description of the tenant")
    state: Optional[str] = Field("Active", description="State of the tenant")
    tenant_id: Optional[str] = Field(None, description="Unique tenant identifier (UUID)")
