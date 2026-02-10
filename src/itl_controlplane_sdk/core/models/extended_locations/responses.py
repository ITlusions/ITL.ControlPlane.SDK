"""Extended Location response models."""
from pydantic import ConfigDict

from itl_controlplane_sdk.core.models.base import ResourceResponse


class ExtendedLocationResponse(ResourceResponse):
    """Extended Location response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "/subscriptions/sub-12345/providers/ITL.Core/extendedlocations/edge-dc-01",
            "name": "edge-dc-01",
            "type": "ITL.Core/extendedlocations",
            "location": "westeurope",
            "properties": {"display_name": "Edge Zone Amsterdam", "location_type": "EdgeZone", "capabilities": ["vm", "storage"]},
            "provisioning_state": "Succeeded",
            "resource_guid": "550e8400-e29b-41d4-a716-446655440007"
        }
    })
