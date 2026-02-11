"""Extended Location response models."""
from typing import Optional, List
from datetime import datetime
import uuid
from pydantic import BaseModel, Field

from itl_controlplane_sdk.core.models.extended_locations.properties import ExtendedLocationProperties


class ExtendedLocationResponse(BaseModel):
    """Response model for an extended location resource."""
    id: str = Field(..., description="ARM-compliant resource ID")
    name: str = Field(..., description="Name of the extended location")
    type: str = Field(default="ITL.ExtendedLocation/customLocations")
    location: str = Field(..., description="Azure region")
    properties: ExtendedLocationProperties = Field(..., description="Extended location properties")
    tags: dict = Field(default_factory=dict, description="Resource tags")
    resource_guid: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique resource GUID"
    )
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    modified_at: Optional[str] = Field(None, description="Last modification timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "/subscriptions/sub-001/resourceGroups/rg-1/providers/ITL.ExtendedLocation/customLocations/arc-prod",
                "name": "arc-prod",
                "type": "ITL.ExtendedLocation/customLocations",
                "location": "eastus",
                "properties": {
                    "namespace": "ITL.Arc",
                    "kind": "Arc",
                    "display_name": "Azure Arc on-premises",
                    "description": "Extended location for Arc-enabled resources",
                    "supported_providers": ["ITL.Compute", "ITL.Storage"],
                    "provisioning_state": "Succeeded"
                },
                "tags": {
                    "environment": "production",
                    "team": "infrastructure"
                },
                "resource_guid": "550e8400-e29b-41d4-a716-446655440000",
                "created_at": "2026-02-11T10:30:00Z",
                "modified_at": "2026-02-11T10:30:00Z"
            }
        }


class PaginatedExtendedLocationList(BaseModel):
    """Paginated list of extended locations."""
    value: List[ExtendedLocationResponse] = Field(..., description="Array of extended location resources")
    next_link: Optional[str] = Field(None, description="Link to next page of results")
    
    class Config:
        json_schema_extra = {
            "example": {
                "value": [
                    {
                        "id": "/subscriptions/sub-001/resourceGroups/rg-1/providers/ITL.ExtendedLocation/customLocations/arc-prod",
                        "name": "arc-prod",
                        "type": "ITL.ExtendedLocation/customLocations",
                        "location": "eastus",
                        "properties": {
                            "namespace": "ITL.Arc",
                            "kind": "Arc",
                            "display_name": "Azure Arc on-premises",
                            "supported_providers": ["ITL.Compute"],
                            "provisioning_state": "Succeeded"
                        },
                        "tags": {"environment": "production"},
                        "resource_guid": "550e8400-e29b-41d4-a716-446655440000"
                    }
                ],
                "next_link": None
            }
        }


class ExtendedLocationErrorResponse(BaseModel):
    """Error response model."""
    error: dict = Field(
        ...,
        description="Error details",
        json_schema_extra={
            "example": {
                "code": "ResourceNotFound",
                "message": "Extended location 'arc-prod' not found"
            }
        }
    )


class ExtendedLocationMetadata(BaseModel):
    """Metadata for extended location operations."""
    operation_id: str = Field(..., description="Unique operation ID")
    status: str = Field(..., description="Operation status")
    timestamp: str = Field(..., description="Operation timestamp")
    duration_ms: Optional[int] = Field(None, description="Operation duration in milliseconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "operation_id": "op-123456",
                "status": "Succeeded",
                "timestamp": "2026-02-11T10:30:00Z",
                "duration_ms": 250
            }
        }
