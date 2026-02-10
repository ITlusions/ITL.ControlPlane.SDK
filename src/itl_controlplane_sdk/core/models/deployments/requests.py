"""Deployment request models."""
from typing import Dict, Optional
from pydantic import Field

from itl_controlplane_sdk.core.models.base import ResourceRequest
from itl_controlplane_sdk.core.models.deployments.properties import DeploymentProperties


class CreateDeploymentRequest(ResourceRequest):
    """Create Deployment request."""
    tags: Optional[Dict[str, str]] = Field(None, description="Deployment tags")
    properties: DeploymentProperties = Field(..., description="Deployment properties")
