"""Policy response models."""
from pydantic import ConfigDict

from itl_controlplane_sdk.core.models.base import ResourceResponse


class PolicyResponse(ResourceResponse):
    """Policy response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "/subscriptions/sub-12345/providers/ITL.Core/policies/require-tags",
            "name": "require-tags-policy",
            "type": "ITL.Core/policies",
            "location": "global",
            "properties": {"display_name": "Require Tags", "policy_type": "Custom", "mode": "Indexed"},
            "provisioning_state": "Succeeded",
            "resource_guid": "550e8400-e29b-41d4-a716-446655440005"
        }
    })
