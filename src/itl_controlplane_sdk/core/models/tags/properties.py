"""Tag properties model."""
from typing import List
from pydantic import BaseModel, Field


class TagValue(BaseModel):
    """Tag value entry."""
    key: str = Field(..., description="Tag key")
    value: str = Field(..., description="Tag value")


class TagProperties(BaseModel):
    """Tag properties."""
    count: int = Field(0, description="Number of resources with this tag")
    values: List[TagValue] = Field(default_factory=list, description="Tag values")
