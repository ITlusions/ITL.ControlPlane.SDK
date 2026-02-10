"""Location request models."""
from typing import Optional
from pydantic import Field

from itl_controlplane_sdk.core.models.base import ResourceRequest
from itl_controlplane_sdk.core.models.locations.properties import LocationProperties


class CreateLocationRequest(ResourceRequest):
    """Create Location request."""
    display_name: Optional[str] = Field(None, description="Display name")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")
    paired_region: Optional[str] = Field(None, description="Paired region")
    properties: Optional[LocationProperties] = Field(None, description="Location properties")
