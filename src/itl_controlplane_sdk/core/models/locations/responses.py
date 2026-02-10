"""Location response models."""
from pydantic import ConfigDict

from itl_controlplane_sdk.core.models.base import ResourceResponse


class LocationResponse(ResourceResponse):
    """Location response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "/subscriptions/sub-12345/providers/ITL.Core/locations/westeurope",
            "name": "westeurope",
            "type": "ITL.Core/locations",
            "location": "global",
            "properties": {"display_name": "West Europe", "latitude": 50.93, "longitude": 6.97, "paired_region": "northeurope"},
            "provisioning_state": "Succeeded",
            "resource_guid": "550e8400-e29b-41d4-a716-446655440006"
        }
    })
