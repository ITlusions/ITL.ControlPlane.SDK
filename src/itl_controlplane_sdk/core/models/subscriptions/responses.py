"""Subscription response models."""
from pydantic import ConfigDict

from itl_controlplane_sdk.core.models.base import ResourceResponse


class SubscriptionResponse(ResourceResponse):
    """Subscription response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "/subscriptions/sub-12345",
            "name": "sub-prod-eastus",
            "type": "ITL.Core/subscriptions",
            "location": "global",
            "properties": {"display_name": "Production - East US", "state": "Enabled"},
            "provisioning_state": "Succeeded",
            "resource_guid": "550e8400-e29b-41d4-a716-446655440003"
        }
    })
