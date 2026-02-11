"""Extended Location request models."""
from typing import List, Optional
from pydantic import BaseModel, Field

from itl_controlplane_sdk.core.models.extended_locations.properties import ExtendedLocationProperties


class CreateExtendedLocationRequest(BaseModel):
    """Request to create an extended location."""
    location: str = Field(..., description="Azure region")
    properties: ExtendedLocationProperties = Field(..., description="Extended location properties")
    tags: Optional[dict] = Field(
        default_factory=dict,
        description="Resource tags for organization and billing"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "location": "eastus",
                "tags": {
                    "environment": "production",
                    "team": "infrastructure"
                },
                "properties": {
                    "namespace": "ITL.Arc",
                    "kind": "Arc",
                    "display_name": "Azure Arc on-premises",
                    "description": "Extended location for Arc-enabled resources",
                    "supported_providers": [
                        "ITL.Compute",
                        "ITL.Storage"
                    ]
                }
            }
        }


class UpdateExtendedLocationRequest(BaseModel):
    """Request to update an extended location (partial update)."""
    tags: Optional[dict] = Field(None, description="Updated tags")
    properties: Optional[ExtendedLocationProperties] = Field(None, description="Updated properties")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tags": {
                    "cost-center": "cc-123"
                },
                "properties": {
                    "display_name": "Updated Display Name"
                }
            }
        }
