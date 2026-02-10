"""Extended Location request models."""
from typing import List, Optional
from pydantic import Field

from itl_controlplane_sdk.core.models.base import ResourceRequest
from itl_controlplane_sdk.core.models.extended_locations.properties import ExtendedLocationProperties


class CreateExtendedLocationRequest(ResourceRequest):
    """Create Extended Location request."""
    location_type: str = Field(..., description="Type of extended location")
    parent_location: Optional[str] = Field(None, description="Parent location")
    display_name: Optional[str] = Field(None, description="Display name")
    capabilities: Optional[List[str]] = Field(None, description="Capabilities")
    properties: Optional[ExtendedLocationProperties] = Field(None, description="Extended location properties")
