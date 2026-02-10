"""Resource Group request models."""
from typing import Dict, Optional
from pydantic import Field

from itl_controlplane_sdk.core.models.base import ResourceRequest
from itl_controlplane_sdk.core.models.resource_groups.properties import ResourceGroupProperties


class CreateResourceGroupRequest(ResourceRequest):
    """Create Resource Group request."""
    tags: Optional[Dict[str, str]] = Field(None, description="Resource tags")
    properties: Optional[ResourceGroupProperties] = Field(None, description="Resource group properties")

    class Config:
        json_schema_extra = {
            "example": {
                "subscription_id": "sub-12345",
                "resource_group": "prod-rg",
                "provider_namespace": "ITL.Core",
                "resource_type": "resourcegroups",
                "resource_name": "prod-rg",
                "location": "westeurope",
                "body": {"managed": True},
                "tags": {"env": "production"}
            }
        }
