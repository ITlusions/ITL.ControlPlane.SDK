"""Tag response models."""
from pydantic import ConfigDict

from itl_controlplane_sdk.core.models.base import ResourceResponse


class TagResponse(ResourceResponse):
    """Tag response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "/subscriptions/sub-12345/providers/ITL.Core/tags/environment",
            "name": "environment",
            "type": "ITL.Core/tags",
            "location": "global",
            "properties": {"count": 125, "values": [{"key": "environment", "value": "production"}]},
            "provisioning_state": "Succeeded",
            "resource_guid": "550e8400-e29b-41d4-a716-446655440004"
        }
    })
