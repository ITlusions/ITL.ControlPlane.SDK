"""Extended Location properties model."""
from typing import List, Optional
import os
from pydantic import BaseModel, Field, field_validator


class ExtendedLocationProperties(BaseModel):
    """Extended location specific properties.
    
    Configuration:
    - NAMESPACE_PREFIX: Environment variable to set default namespace prefix (default: "ITL.")
    """
    
    # Class variable for configurable namespace prefix
    namespace_prefix: str = os.getenv("NAMESPACE_PREFIX", "ITL.")
    
    namespace: str = Field(
        ...,
        description="Namespace for the extended location (e.g., 'ITL.Arc', 'ITL.Storage')"
    )
    kind: str = Field(..., description="Kind/type of extended location (e.g., 'Arc')")
    display_name: Optional[str] = Field(None, description="Human-readable display name")
    description: Optional[str] = Field(None, description="Extended location description")
    supported_providers: Optional[List[str]] = Field(
        default_factory=list,
        description="List of resource providers supported in this extended location"
    )
    provisioning_state: str = Field(
        default="Succeeded",
        description="Provisioning state (Accepted, Running, Succeeded, Failed)"
    )
    
    @field_validator("namespace")
    @classmethod
    def validate_namespace_prefix(cls, v: str) -> str:
        """Ensure namespace starts with configured prefix."""
        prefix = os.getenv("NAMESPACE_PREFIX", "ITL.")
        if not v.startswith(prefix):
            v = f"{prefix}{v.lstrip('.')}"
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "namespace": "ITL.Arc",
                "kind": "Arc",
                "display_name": "Azure Arc on-premises",
                "description": "Extended location for Arc-enabled resources",
                "supported_providers": [
                    "ITL.Compute",
                    "ITL.Storage",
                    "ITL.Network"
                ],
                "provisioning_state": "Succeeded"
            }
        }
