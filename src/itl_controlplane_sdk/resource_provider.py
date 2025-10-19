"""
Core Resource Provider base classes and interfaces for the ITL ControlPlane SDK
"""
import abc
import logging
from typing import Dict, List, Any, Optional
from .models import ResourceRequest, ResourceResponse, ResourceListResponse

logger = logging.getLogger(__name__)

class ResourceProvider(abc.ABC):
    """
    Abstract base class for Resource Providers
    
    This class defines the standard contract that all resource providers must implement
    to be compatible with the ITL Control Plane system.
    """
    
    def __init__(self, provider_namespace: str):
        self.provider_namespace = provider_namespace
        self.supported_resource_types: List[str] = []
    
    @abc.abstractmethod
    async def create_or_update_resource(self, request: ResourceRequest) -> ResourceResponse:
        """
        Create or update a resource (PUT operation)
        
        Args:
            request: Resource creation/update request
            
        Returns:
            ResourceResponse with created/updated resource details
        """
        pass
    
    @abc.abstractmethod
    async def get_resource(self, request: ResourceRequest) -> ResourceResponse:
        """
        Get a specific resource (GET operation)
        
        Args:
            request: Resource retrieval request
            
        Returns:
            ResourceResponse with resource details
        """
        pass
    
    @abc.abstractmethod
    async def delete_resource(self, request: ResourceRequest) -> ResourceResponse:
        """
        Delete a resource (DELETE operation)
        
        Args:
            request: Resource deletion request
            
        Returns:
            ResourceResponse confirming deletion
        """
        pass
    
    async def list_resources(self, request: ResourceRequest) -> ResourceListResponse:
        """
        List resources of this type (GET collection operation)
        
        Default implementation - override if needed
        
        Args:
            request: Resource list request
            
        Returns:
            ResourceListResponse with list of resources
        """
        # Default implementation returns empty list
        return ResourceListResponse(value=[])
    
    async def execute_action(self, request: ResourceRequest) -> ResourceResponse:
        """
        Execute a custom action on a resource (POST operation)
        
        Default implementation - override if needed
        
        Args:
            request: Resource action request with action name
            
        Returns:
            ResourceResponse with action result
        """
        raise NotImplementedError(f"Action '{request.action}' not supported by this provider")
    
    def supports_resource_type(self, resource_type: str) -> bool:
        """
        Check if this provider supports the given resource type
        
        Args:
            resource_type: The resource type to check
            
        Returns:
            True if supported, False otherwise
        """
        return resource_type in self.supported_resource_types
    
    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get information about this provider
        
        Returns:
            Dict with provider metadata
        """
        return {
            "namespace": self.provider_namespace,
            "resourceTypes": self.supported_resource_types,
            "apiVersion": "2023-01-01"
        }
    
    def generate_resource_id(self, subscription_id: str, resource_group: str, 
                           resource_type: str, resource_name: str) -> str:
        """Generate standard resource ID"""
        return f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/{self.provider_namespace}/{resource_type}/{resource_name}"
    
    def validate_request(self, request: ResourceRequest) -> List[str]:
        """
        Validate resource request
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not request.subscription_id:
            errors.append("subscription_id is required")
        if not request.resource_group:
            errors.append("resource_group is required")
        if not request.resource_name:
            errors.append("resource_name is required")
        if not request.location:
            errors.append("location is required")
        if not request.body:
            errors.append("body is required")
            
        return errors