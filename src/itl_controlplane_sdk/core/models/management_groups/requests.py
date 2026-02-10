"""Management Group request models."""
from typing import Dict, Optional
from pydantic import Field

from itl_controlplane_sdk.core.models.base import ResourceRequest
from itl_controlplane_sdk.core.models.management_groups.properties import ManagementGroupProperties


class CreateManagementGroupRequest(ResourceRequest):
    """Create Management Group request."""
    tags: Optional[Dict[str, str]] = Field(None, description="Management group tags")
    properties: Optional[ManagementGroupProperties] = Field(None, description="Management group properties")
