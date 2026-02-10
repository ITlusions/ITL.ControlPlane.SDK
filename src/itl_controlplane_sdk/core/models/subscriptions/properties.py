"""Subscription properties model."""
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class SubscriptionProperties(BaseModel):
    """Subscription properties."""
    display_name: str = Field(..., description="Display name")
    state: str = Field("Enabled", description="Subscription state (Enabled, Warned, PastDue, Disabled)")
    management_group_id: Optional[str] = Field(None, description="Management group ID this subscription belongs to")
    subscription_policies: Optional[Dict[str, Any]] = Field(None, description="Subscription policies")
    quota: Optional[Dict[str, Any]] = Field(None, description="Quota information")
