"""Resource Group properties model."""
from typing import Optional
from pydantic import BaseModel, Field


class ResourceGroupProperties(BaseModel):
    """Resource Group properties."""
    provisioning_state: Optional[str] = Field("Succeeded", description="Provisioning state")
    managed: Optional[bool] = Field(False, description="Whether the resource group is managed")
    environment: Optional[str] = Field(None, description="Environment (dev, test, prod)")
