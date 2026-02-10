"""Deployment response models."""
from pydantic import ConfigDict

from itl_controlplane_sdk.core.models.base import ResourceResponse


class DeploymentResponse(ResourceResponse):
    """Deployment response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "/subscriptions/sub-12345/resourceGroups/prod-rg/providers/ITL.Core/deployments/app-001",
            "name": "app-deployment-001",
            "type": "ITL.Core/deployments",
            "location": "westeurope",
            "properties": {"provisioning_state": "Succeeded", "correlation_id": "550e8400-e29b"},
            "provisioning_state": "Succeeded",
            "resource_guid": "550e8400-e29b-41d4-a716-446655440002"
        }
    })
