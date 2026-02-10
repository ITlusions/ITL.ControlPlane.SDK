"""Tenant response models."""
from pydantic import ConfigDict

from itl_controlplane_sdk.core.models.base import ResourceResponse


class TenantResponse(ResourceResponse):
    """Tenant response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "/providers/ITL.Management/tenants/ITL",
            "name": "ITL",
            "type": "ITL.Core/tenants",
            "location": "global",
            "properties": {
                "display_name": "ITL Default Tenant",
                "state": "Active",
                "provisioning_state": "Succeeded"
            }
        }
    })
