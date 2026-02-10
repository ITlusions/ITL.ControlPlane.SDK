"""Management Group response models."""
from pydantic import ConfigDict

from itl_controlplane_sdk.core.models.base import ResourceResponse


class ManagementGroupResponse(ResourceResponse):
    """Management Group response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "/subscriptions/sub-12345/providers/ITL.Core/managementgroups/org-hierarchy",
            "name": "org-hierarchy",
            "type": "ITL.Core/managementgroups",
            "location": "global",
            "properties": {
                "tenant_id": "00000000-0000-0000-0000-000000000000",
                "display_name": "Organization Hierarchy",
                "parent_id": None,
                "child_count": 3
            },
            "tags": {
                "org": "contoso",
                "cost-center": "engineering",
                "environment": "production"
            },
            "provisioning_state": "Succeeded",
            "resource_guid": "550e8400-e29b-41d4-a716-446655440000"
        }
    })
