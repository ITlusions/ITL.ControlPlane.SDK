"""Tenant request models."""
from typing import Dict, Optional
from pydantic import Field

from itl_controlplane_sdk.core.models.base import ResourceRequest
from itl_controlplane_sdk.core.models.tenants.properties import TenantProperties


class CreateTenantRequest(ResourceRequest):
    """Create Tenant request."""
    tags: Optional[Dict[str, str]] = Field(None, description="Tenant tags")
    properties: Optional[TenantProperties] = Field(None, description="Tenant properties")
