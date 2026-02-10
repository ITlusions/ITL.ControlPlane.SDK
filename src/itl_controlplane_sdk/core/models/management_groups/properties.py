"""Management Group properties model."""
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ManagementGroupProperties(BaseModel):
    """Management Group properties."""
    tenant_id: Optional[str] = Field(None, description="Tenant ID (auto-generated if not provided)")
    display_name: Optional[str] = Field(None, description="Display name for the management group")
    parent_id: Optional[str] = Field(None, description="Parent management group ID")
    description: Optional[str] = Field(None, description="Description of the management group")
    child_count: int = Field(0, description="Number of child management groups")
