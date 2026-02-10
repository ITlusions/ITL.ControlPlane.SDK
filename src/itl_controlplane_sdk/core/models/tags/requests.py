"""Tag request models."""
from typing import Dict, List, Optional
from pydantic import Field

from itl_controlplane_sdk.core.models.base import ResourceRequest
from itl_controlplane_sdk.core.models.tags.properties import TagValue, TagProperties


class CreateTagRequest(ResourceRequest):
    """Create Tag request."""
    values: Optional[List[TagValue]] = Field(None, description="Tag values")
    properties: Optional[TagProperties] = Field(None, description="Tag properties")
