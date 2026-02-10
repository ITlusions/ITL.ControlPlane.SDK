"""
Resource Mapper for ITL ControlPlane to Pulumi

Maps ITL ControlPlane resource models to Pulumi resource definitions.
"""

from typing import Any, Dict, Type, Callable, Optional
from dataclasses import dataclass
import pulumi


@dataclass
class ResourceMapping:
    """Mapping configuration for a resource type."""
    
    itl_type: str
    pulumi_type: str
    mapper_fn: Callable[[Dict[str, Any]], Dict[str, Any]]
    resource_class: Optional[Type] = None


class ResourceMapper:
    """
    Maps ITL ControlPlane resources to Pulumi resources.
    
    Provides bidirectional mapping and resource creation from ITL definitions.
    """
    
    def __init__(self):
        """Initialize resource mapper."""
        self._mappings: Dict[str, ResourceMapping] = {}
        self._register_default_mappings()
    
    def register_mapping(self, mapping: ResourceMapping) -> None:
        """
        Register a custom resource mapping.
        
        Args:
            mapping: ResourceMapping configuration
        """
        self._mappings[mapping.itl_type] = mapping
    
    def map_resource(self, itl_resource: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map ITL ControlPlane resource to Pulumi format.
        
        Args:
            itl_resource: ITL resource definition
            
        Returns:
            Pulumi resource definition
        """
        resource_type = itl_resource.get("type")
        
        if resource_type not in self._mappings:
            raise ValueError(f"No mapping found for resource type: {resource_type}")
        
        mapping = self._mappings[resource_type]
        return mapping.mapper_fn(itl_resource)
    
    def create_resource(self, itl_resource: Dict[str, Any], stack_name: str) -> pulumi.Resource:
        """
        Create a Pulumi resource from ITL definition.
        
        Args:
            itl_resource: ITL resource definition
            stack_name: Name of the stack for resource naming
            
        Returns:
            Created Pulumi resource
        """
        resource_type = itl_resource.get("type")
        
        if resource_type not in self._mappings:
            raise ValueError(f"No mapping found for resource type: {resource_type}")
        
        mapping = self._mappings[resource_type]
        pulumi_def = mapping.mapper_fn(itl_resource)
        
        resource_name = f"{stack_name}-{itl_resource.get('name', 'resource')}"
        
        if mapping.resource_class:
            return mapping.resource_class(
                resource_name,
                **pulumi_def
            )
        
        raise NotImplementedError(f"Resource creation not implemented for: {resource_type}")
    
    def _register_default_mappings(self) -> None:
        """Register default resource mappings."""
        
        # Resource Group mapping
        self.register_mapping(ResourceMapping(
            itl_type="resourcegroups",
            pulumi_type="aws:ec2:SecurityGroup",
            mapper_fn=self._map_resource_group
        ))
        
        # Tags mapping
        self.register_mapping(ResourceMapping(
            itl_type="tags",
            pulumi_type="aws:generic:Resource",
            mapper_fn=self._map_tags
        ))
        
        # Locations mapping (read-only)
        self.register_mapping(ResourceMapping(
            itl_type="locations",
            pulumi_type="aws:ec2:AvailabilityZone",
            mapper_fn=self._map_locations
        ))
    
    @staticmethod
    def _map_resource_group(itl_resource: Dict[str, Any]) -> Dict[str, Any]:
        """Map ITL resource group to Pulumi resource."""
        properties = itl_resource.get("properties", {})
        
        return {
            "description": properties.get("display_name", itl_resource.get("name")),
            "tags": properties.get("tags", {}),
            "vpcId": properties.get("vpc_id"),
            "opts": pulumi.ResourceOptions(depends_on=[])
        }
    
    @staticmethod
    def _map_tags(itl_resource: Dict[str, Any]) -> Dict[str, Any]:
        """Map ITL tags to Pulumi resource."""
        properties = itl_resource.get("properties", {})
        
        return {
            "tags": properties.get("tags", {}),
            "opts": pulumi.ResourceOptions()
        }
    
    @staticmethod
    def _map_locations(itl_resource: Dict[str, Any]) -> Dict[str, Any]:
        """Map ITL locations to Pulumi availability zones."""
        properties = itl_resource.get("properties", {})
        
        return {
            "name": properties.get("name", itl_resource.get("name")),
            "state": "available",
            "opts": pulumi.ResourceOptions(protect=True)
        }
    
    def get_supported_types(self) -> list[str]:
        """Get list of supported resource types."""
        return list(self._mappings.keys())
