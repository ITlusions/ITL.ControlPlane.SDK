"""Location properties model."""
from typing import Optional
from pydantic import BaseModel, Field


class LocationProperties(BaseModel):
    """Location properties."""
    display_name: str = Field(..., description="Display name for the region")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")
    paired_region: Optional[str] = Field(None, description="Paired region for disaster recovery")
    physical_location: Optional[str] = Field(None, description="Physical data center location")
