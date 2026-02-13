"""
Generic resource base models for reusable request/response patterns.

Provides a common base class that all providers can inherit from to create
provider-specific request and response models with consistent field structure
and Pydantic configuration.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict


class GenericResourceBase(BaseModel):
    """
    Base class for generic resource models with common fields and configuration.
    
    Provides common schema fields (location, tags) and shared Pydantic configuration
    that can be inherited by request and response models across all providers.
    
    This base class ensures consistency across the platform while allowing
    providers to extend with their own specific fields.
    
    Example:
        class MyProviderRequest(GenericResourceBase):
            subscription_id: str
            resource_group: str
            resource_name: str
            # Additional provider-specific fields here
    """
    
    location: str = Field(..., description="Location or region")
    tags: Optional[Dict[str, str]] = Field(None, description="Resource tags for categorization")
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        arbitrary_types_allowed=True,
    )
