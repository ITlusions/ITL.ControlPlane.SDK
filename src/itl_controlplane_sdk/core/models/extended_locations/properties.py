"""Extended Location properties model."""
from typing import List, Optional
from pydantic import BaseModel, Field


class ExtendedLocationProperties(BaseModel):
    """Extended Location properties."""
    display_name: str = Field(..., description="Display name for the extended location")
    location_type: str = Field(..., description="Type of extended location (e.g., 'EdgeZone', 'CustomLocation')")
    parent_location: Optional[str] = Field(None, description="Parent location")
    capabilities: Optional[List[str]] = Field(None, description="Available capabilities")
    status: str = Field("Available", description="Status (Available, Unavailable)")
