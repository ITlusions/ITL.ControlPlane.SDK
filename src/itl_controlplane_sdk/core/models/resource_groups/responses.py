"""Resource Group response models."""
from pydantic import ConfigDict

from itl_controlplane_sdk.core.models.base import ResourceResponse


class ResourceGroupResponse(ResourceResponse):
    """Resource Group response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "/subscriptions/sub-12345/resourceGroups/prod-rg",
            "name": "prod-rg",
            "type": "ITL.Core/resourcegroups",
            "location": "westeurope",
            "properties": {"provisioning_state": "Succeeded", "managed": True},
            "tags": {"env": "production"},
            "provisioning_state": "Succeeded",
            "resource_guid": "550e8400-e29b-41d4-a716-446655440001"
        }
    })
