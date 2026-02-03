"""
Resource Group Handler - Implementation using ScopedResourceHandler with Big 3 features

Handles resource group creation, retrieval, and deletion with:
- Subscription-scoped uniqueness enforcement
- Automatic timestamps (createdTime, modifiedTime, createdBy, modifiedBy)
- Provisioning state management (Accepted → Provisioning → Succeeded)
- Schema validation (location required, valid tags format)
"""
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, validator, Field
from itl_controlplane_sdk.providers.scoped_resources import ScopedResourceHandler, UniquenessScope
from itl_controlplane_sdk.providers.resource_handlers import (
    TimestampedResourceHandler,
    ProvisioningStateHandler,
    ValidatedResourceHandler,
    ProvisioningState,
)
from itl_controlplane_sdk.providers.locations import LocationsHandler

logger = logging.getLogger(__name__)


class ResourceGroupSchema(BaseModel):
    """Validation schema for Resource Groups."""
    
    location: str = Field(..., description="Azure region (e.g., eastus, westeurope)")
    tags: Optional[Dict[str, str]] = Field(default_factory=dict, description="Resource tags")
    
    @validator('location')
    def validate_location(cls, v):
        """Validate Azure location format using dynamic LocationsHandler."""
        return LocationsHandler.validate_location(v)
    
    @validator('tags')
    def validate_tags(cls, v):
        """Validate tags format."""
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError('Tags must be a dictionary')
        for key, value in v.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError('Tags must have string keys and values')
        return v


class ResourceGroupHandler(
    ValidatedResourceHandler,
    ProvisioningStateHandler,
    TimestampedResourceHandler,
    ScopedResourceHandler
):
    """
    Handler for resource groups with subscription-scoped uniqueness.
    
    Features:
    - UNIQUENESS_SCOPE: [SUBSCRIPTION] - RG names must be unique within a subscription
    - RESOURCE_TYPE: "resourcegroups"
    - Automatic timestamps on create/update
    - Provisioning state machine (Accepted → Provisioning → Succeeded)
    - Schema validation (location required, valid Azure region, valid tags)
    
    Usage:
        rg_handler = ResourceGroupHandler(self.resource_groups)
        
        # Create with automatic validation and state management
        resource_id, rg_config = rg_handler.create_resource(
            "prod-rg",
            {
                "location": "eastus",
                "tags": {"environment": "production", "team": "platform"}
            },
            "Microsoft.Resources/resourceGroups",
            {
                "subscription_id": "sub-123",
                "user_id": "admin@company.com"
            }
        )
        # rg_config now includes:
        # - provisioning_state: "Succeeded"
        # - createdTime, modifiedTime, createdBy, modifiedBy
        
        # Get
        result = rg_handler.get_resource(
            "prod-rg",
            {"subscription_id": "sub-123"}
        )
        
        # List
        resources = rg_handler.list_resources(
            {"subscription_id": "sub-123"}
        )
        
        # Delete (auto-transitions through Deleting → Deleted)
        deleted = rg_handler.delete_resource(
            "prod-rg",
            {"subscription_id": "sub-123"}
        )
    
    Raises:
        ValueError: If validation fails (invalid location, etc.) or RG already exists in subscription
    """
    
    # Configuration
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION]
    RESOURCE_TYPE = "resourcegroups"
    SCHEMA_CLASS = ResourceGroupSchema
    
    def __init__(self, storage_dict: Dict[str, Any]):
        """Initialize the Resource Group handler"""
        super().__init__(storage_dict)
        self.logger = logging.getLogger(f"{__name__}.ResourceGroupHandler")
    
    def _generate_resource_id(self, name: str, resource_type: str, scope_context: Dict[str, str]) -> str:
        """
        Override to generate correct Azure-style resource group ID.
        
        Resource Group IDs follow the format:
        /subscriptions/{subscription}/resourceGroups/{name}
        """
        subscription_id = scope_context.get("subscription_id", "unknown")
        return f"/subscriptions/{subscription_id}/resourceGroups/{name}"
    
    def create_from_properties(
        self,
        name: str,
        properties: Dict[str, Any],
        subscription_id: str,
        default_location: str = "eastus"
    ) -> Dict[str, Any]:
        """
        Create a resource group from properties dict.
        
        Args:
            name: Resource group name
            properties: Properties dict (may contain _subscription_id)
            subscription_id: Target subscription ID
            default_location: Default location if not in properties
        
        Returns:
            Response dict with id, name, properties, etc.
        
        Raises:
            ValueError: If duplicate RG name in subscription or validation fails
        """
        # Extract subscription from properties or use parameter
        actual_subscription = properties.get("_subscription_id") or subscription_id
        
        # Validate properties using schema
        try:
            validated_data = self.validate({
                "location": properties.get("location", default_location),
                "tags": properties.get("tags", {})
            })
        except ValueError as e:
            raise ValueError(f"Validation failed: {str(e)}")
        
        # Prepare resource group config with validated data
        rg_config = {
            "location": validated_data.get("location", default_location),
            "tags": validated_data.get("tags", {}),
            "managed_by": properties.get("managed_by"),
            "provisioning_state": "Accepted"
        }
        
        # Check for duplicates and create
        scope_context = {"subscription_id": actual_subscription}
        
        try:
            resource_id, _ = self.create_resource(
                name,
                rg_config,
                "ITL.Core/resourcegroups",
                scope_context
            )
        except ValueError as e:
            raise ValueError(str(e))
        
        # Add timestamps to the resource
        self.add_timestamps(rg_config, scope_context)
        
        # Transition provisioning state from Accepted → Provisioning → Succeeded
        self.set_state(rg_config, ProvisioningState.PROVISIONING)
        self.set_state(rg_config, ProvisioningState.SUCCEEDED)
        
        return {
            "id": resource_id,
            "name": name,
            "type": "ITL.Core/resourcegroups",
            "location": rg_config["location"],
            "properties": rg_config,
            "tags": rg_config.get("tags"),
            "provisioning_state": rg_config.get("provisioning_state", "Succeeded")
        }
    
    def get_by_name(
        self,
        name: str,
        subscription_id: str,
        default_location: str = "eastus"
    ) -> Dict[str, Any]:
        """
        Get a resource group by name.
        
        Args:
            name: Resource group name
            subscription_id: Subscription ID
            default_location: Default location for response
        
        Returns:
            Response dict with resource group details, or error if not found
        """
        scope_context = {"subscription_id": subscription_id}
        result = self.get_resource(name, scope_context)
        
        if not result:
            return {
                "id": f"/subscriptions/{subscription_id}/resourceGroups/{name}",
                "name": name,
                "type": "ITL.Core/resourcegroups",
                "location": default_location,
                "properties": {"error": f"Resource group '{name}' not found"},
                "provisioning_state": "Failed"
            }
        
        resource_id, rg_config = result
        return {
            "id": resource_id,
            "name": name,
            "type": "ITL.Core/resourcegroups",
            "location": rg_config.get("location", default_location),
            "properties": rg_config,
            "tags": rg_config.get("tags"),
            "provisioning_state": "Succeeded"
        }
    
    def list_by_subscription(
        self,
        subscription_id: str,
        default_location: str = "eastus"
    ) -> Dict[str, Any]:
        """
        List all resource groups in a subscription.
        
        Args:
            subscription_id: Subscription ID
            default_location: Default location for responses
        
        Returns:
            Dict with resources list and count
        """
        scope_context = {"subscription_id": subscription_id}
        resources = self.list_resources(scope_context)
        
        resource_list = []
        for name, resource_id, rg_config in resources:
            resource_list.append({
                "id": resource_id,
                "name": name,
                "type": "ITL.Core/resourcegroups",
                "location": rg_config.get("location", default_location),
                "properties": rg_config,
                "tags": rg_config.get("tags")
            })
        
        return {
            "resources": resource_list,
            "count": len(resource_list)
        }
    
    def delete_by_name(
        self,
        name: str,
        subscription_id: str
    ) -> bool:
        """
        Delete a resource group by name.
        
        Args:
            name: Resource group name
            subscription_id: Subscription ID
        
        Returns:
            True if deleted, False if not found
        """
        scope_context = {"subscription_id": subscription_id}
        return self.delete_resource(name, scope_context)
