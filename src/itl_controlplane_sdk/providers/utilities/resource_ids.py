"""
Enhanced resource ID generation with GUID support for ITL ControlPlane SDK
"""
import uuid
from typing import Optional
from pydantic import BaseModel, Field


class ResourceIdentity(BaseModel):
    """Enhanced resource identity with both GUID and path-based IDs"""
    resource_id: str = Field(..., description="Hierarchical path-based ID (ARM-style)")
    resource_guid: str = Field(..., description="Globally unique identifier (GUID)")
    
    @classmethod
    def create(
        cls,
        subscription_id: str,
        resource_group: Optional[str],
        provider_namespace: str,
        resource_type: str, 
        resource_name: str,
        guid: Optional[str] = None
    ) -> "ResourceIdentity":
        """Create a new resource identity with both path and GUID"""
        
        # Generate path-based ID (current format)
        if resource_group:
            resource_id = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/{provider_namespace}/{resource_type}/{resource_name}"
        else:
            resource_id = f"/subscriptions/{subscription_id}/providers/{provider_namespace}/{resource_type}/{resource_name}"
        
        # Generate GUID if not provided
        if guid is None:
            guid = str(uuid.uuid4())
            
        return cls(resource_id=resource_id, resource_guid=guid)


def generate_resource_id(
    subscription_id: str,
    resource_group: Optional[str],
    provider_namespace: str, 
    resource_type: str,
    resource_name: str,
    include_guid: bool = False
) -> str:
    """
    Generate a resource ID with optional GUID suffix for guaranteed uniqueness
    
    Args:
        subscription_id: The subscription ID
        resource_group: The resource group name (optional)
        provider_namespace: The provider namespace (e.g., 'ITL.Compute') 
        resource_type: The resource type (e.g., 'virtualMachines')
        resource_name: The resource name
        include_guid: Whether to append a GUID for guaranteed uniqueness
        
    Returns:
        Resource ID string
        
    Examples:
        # Traditional path-based (current):
        "/subscriptions/sub-123/resourceGroups/rg-test/providers/ITL.Compute/virtualMachines/vm-1"
        
        # With GUID suffix for uniqueness:
        "/subscriptions/sub-123/resourceGroups/rg-test/providers/ITL.Compute/virtualMachines/vm-1?guid=550e8400-e29b-41d4-a716-446655440000"
    """
    
    # Build base path
    if resource_group:
        base_id = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/{provider_namespace}/{resource_type}/{resource_name}"
    else:
        base_id = f"/subscriptions/{subscription_id}/providers/{provider_namespace}/{resource_type}/{resource_name}"
    
    # Add GUID if requested
    if include_guid:
        guid = str(uuid.uuid4()) 
        return f"{base_id}?guid={guid}"
    
    return base_id


def parse_resource_id(resource_id: str) -> dict:
    """
    Parse a resource ID into its components
    
    Returns:
        Dictionary with subscription_id, resource_group, provider_namespace, 
        resource_type, resource_name, and guid (if present)
    """
    parts = {}
    
    # Check for GUID suffix
    if "?guid=" in resource_id:
        base_id, guid_part = resource_id.split("?guid=", 1)
        parts["guid"] = guid_part
    else:
        base_id = resource_id
        parts["guid"] = None
    
    # Parse path components
    segments = base_id.strip("/").split("/")
    
    if len(segments) >= 2 and segments[0] == "subscriptions":
        parts["subscription_id"] = segments[1]
        
        if len(segments) >= 4 and segments[2] == "resourceGroups":
            parts["resource_group"] = segments[3]
            
            if len(segments) >= 7 and segments[4] == "providers":
                parts["provider_namespace"] = segments[5]
                parts["resource_type"] = segments[6]
                if len(segments) >= 8:
                    parts["resource_name"] = segments[7]
        elif len(segments) >= 5 and segments[2] == "providers":
            parts["resource_group"] = None
            parts["provider_namespace"] = segments[3]
            parts["resource_type"] = segments[4]
            if len(segments) >= 6:
                parts["resource_name"] = segments[5]
    
    return parts


# Example usage and migration strategy
if __name__ == "__main__":
    # Current approach (backward compatible)
    current_id = generate_resource_id(
        subscription_id="sub-123",
        resource_group="rg-test", 
        provider_namespace="ITL.Compute",
        resource_type="virtualMachines",
        resource_name="vm-1"
    )
    print(f"Current: {current_id}")
    
    # Enhanced approach with GUID
    enhanced_id = generate_resource_id(
        subscription_id="sub-123",
        resource_group="rg-test",
        provider_namespace="ITL.Compute", 
        resource_type="virtualMachines",
        resource_name="vm-1",
        include_guid=True
    )
    print(f"Enhanced: {enhanced_id}")
    
    # Using ResourceIdentity class
    identity = ResourceIdentity.create(
        subscription_id="sub-123",
        resource_group="rg-test",
        provider_namespace="ITL.Compute",
        resource_type="virtualMachines", 
        resource_name="vm-1"
    )
    print(f"Identity - Path: {identity.resource_id}")
    print(f"Identity - GUID: {identity.resource_guid}")
