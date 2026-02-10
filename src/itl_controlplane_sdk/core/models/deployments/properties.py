"""Deployment properties model."""
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class DeploymentProperties(BaseModel):
    """Deployment properties."""
    provisioning_state: str = Field("InProgress", description="Provisioning state (InProgress, Succeeded, Failed)")
    template: Optional[Dict[str, Any]] = Field(None, description="ARM template")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Template parameters")
    output: Optional[Dict[str, Any]] = Field(None, description="Deployment output")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracking")
