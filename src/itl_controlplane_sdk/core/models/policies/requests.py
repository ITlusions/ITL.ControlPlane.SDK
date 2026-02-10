"""Policy request models."""
from typing import Dict, Optional
from pydantic import Field

from itl_controlplane_sdk.core.models.base import ResourceRequest
from itl_controlplane_sdk.core.models.policies.properties import PolicyProperties


class CreatePolicyRequest(ResourceRequest):
    """Create Policy request."""
    tags: Optional[Dict[str, str]] = Field(None, description="Policy tags")
    properties: PolicyProperties = Field(..., description="Policy properties")
