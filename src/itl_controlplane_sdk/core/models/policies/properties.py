"""Policy properties model."""
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class PolicyRule(BaseModel):
    """Policy rule definition."""
    if_: Optional[Dict[str, Any]] = Field(None, description="Condition", alias="if")
    then: Optional[Dict[str, Any]] = Field(None, description="Action to take")


class PolicyProperties(BaseModel):
    """Policy properties."""
    display_name: Optional[str] = Field(None, description="Display name")
    policy_type: str = Field(..., description="Policy type (BuiltIn, Custom)")
    mode: str = Field("Indexed", description="Policy mode (Indexed, All)")
    description: Optional[str] = Field(None, description="Policy description")
    rules: Optional[PolicyRule] = Field(None, description="Policy rules")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Policy parameters")
