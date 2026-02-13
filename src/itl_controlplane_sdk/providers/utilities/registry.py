"""
Resource Provider Registry for the ITL ControlPlane SDK (Core)

This is the core registry without graph database dependencies.
For metadata functionality, use the graph-datastore component separately.
"""
import logging
from typing import Dict, List, Any, Optional
from ..base import ResourceProvider
from itl_controlplane_sdk.core import ResourceRequest, ResourceResponse, ResourceListResponse

logger = logging.getLogger(__name__)

class ResourceProviderRegistry:
    """
    Registry for managing multiple resource providers (core functionality)
    """
    
    def __init__(self):
        self._providers: Dict[str, Dict[str, ResourceProvider]] = {}
        # Structure: {provider_namespace: {resource_type: provider}}
    
    def register_provider(self, provider_namespace: str, resource_type: str, provider: ResourceProvider):
        """Register a resource provider for a specific namespace and resource type"""
        if provider_namespace not in self._providers:
            self._providers[provider_namespace] = {}
        
        self._providers[provider_namespace][resource_type] = provider
        
        # Update provider's supported resource types
        if resource_type not in provider.supported_resource_types:
            provider.supported_resource_types.append(resource_type)
            
        logger.info(f"Registered resource provider: {provider_namespace}/{resource_type}")
    
    def get_provider(self, provider_namespace: str, resource_type: str) -> Optional[ResourceProvider]:
        """Get a registered resource provider"""
        namespace_providers = self._providers.get(provider_namespace, {})
        return namespace_providers.get(resource_type)
    
    def list_providers(self) -> List[str]:
        """List all registered resource provider types"""
        providers = []
        for namespace, resource_types in self._providers.items():
            for resource_type in resource_types.keys():
                providers.append(f"{namespace}/{resource_type}")
        return providers
    
    def list_provider_namespaces(self) -> List[str]:
        """List all registered provider namespaces"""
        return list(self._providers.keys())
    
    async def create_or_update_resource(self, provider_namespace: str, resource_type: str, 
                                      request: ResourceRequest) -> ResourceResponse:
        """Create or update a resource using the appropriate provider"""
        provider = self.get_provider(provider_namespace, resource_type)
        if not provider:
            raise ValueError(f"Resource provider {provider_namespace}/{resource_type} not found")
        
        # Validate request
        errors = provider.validate_request(request)
        if errors:
            raise ValueError(f"Validation errors: {', '.join(errors)}")
        
        return await provider.create_or_update_resource(request)
    
    async def get_resource(self, provider_namespace: str, resource_type: str,
                         request: ResourceRequest) -> ResourceResponse:
        """Get a resource using the appropriate provider"""
        provider = self.get_provider(provider_namespace, resource_type)
        if not provider:
            raise ValueError(f"Resource provider {provider_namespace}/{resource_type} not found")
        
        return await provider.get_resource(request)
    
    async def list_resources(self, provider_namespace: str, resource_type: str,
                           request: ResourceRequest) -> ResourceListResponse:
        """List resources using the appropriate provider"""
        provider = self.get_provider(provider_namespace, resource_type)
        if not provider:
            raise ValueError(f"Resource provider {provider_namespace}/{resource_type} not found")
        
        return await provider.list_resources(request)
    
    async def delete_resource(self, provider_namespace: str, resource_type: str,
                            request: ResourceRequest) -> ResourceResponse:
        """Delete a resource using the appropriate provider"""
        provider = self.get_provider(provider_namespace, resource_type)
        if not provider:
            raise ValueError(f"Resource provider {provider_namespace}/{resource_type} not found")
        
        return await provider.delete_resource(request)
    
    async def execute_action(self, provider_namespace: str, resource_type: str,
                           request: ResourceRequest) -> ResourceResponse:
        """Execute an action using the appropriate provider"""
        provider = self.get_provider(provider_namespace, resource_type)
        if not provider:
            raise ValueError(f"Resource provider {provider_namespace}/{resource_type} not found")
        
        return await provider.execute_action(request)

# Global registry instance
resource_registry = ResourceProviderRegistry()
