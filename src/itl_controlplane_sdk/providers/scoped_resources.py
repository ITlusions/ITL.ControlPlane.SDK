"""
Scoped Resource Handler - Base class for resources with configurable uniqueness scope

Provides automatic duplicate detection and prevention for resources that are unique
within a specific scope (subscription, resource group, management group, etc.)
"""
import logging
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from itl_controlplane_sdk.core import ResourceResponse, ProvisioningState

logger = logging.getLogger(__name__)


class UniquenessScope(Enum):
    """Scope levels for resource uniqueness"""
    GLOBAL = "global"                          # Unique across entire system
    SUBSCRIPTION = "subscription"              # Unique within a subscription
    RESOURCE_GROUP = "resource_group"          # Unique within a resource group
    MANAGEMENT_GROUP = "management_group"      # Unique within a management group
    PARENT_RESOURCE = "parent_resource"        # Unique within a parent resource


class ScopedResourceHandler:
    """
    Base handler for resources with configurable uniqueness scope.
    
    Provides:
    - Automatic storage key generation based on scope configuration
    - Duplicate detection and prevention
    - Scope-aware retrieval, listing, and deletion
    - Backward compatibility with non-scoped resources
    
    Usage:
        class ResourceGroupHandler(ScopedResourceHandler):
            UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION]
            
            async def create_resource(self, name, properties):
                ...
    """
    
    # Configuration: Override in subclass
    UNIQUENESS_SCOPE: List[UniquenessScope] = [UniquenessScope.GLOBAL]
    RESOURCE_TYPE: str = "unknown"
    
    def __init__(self, storage_dict: Dict[str, Any]):
        """
        Initialize the scoped resource handler.
        
        Args:
            storage_dict: The dictionary to use for storing resources
        """
        self.storage = storage_dict
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def _generate_storage_key(self, name: str, scope_context: Dict[str, str]) -> str:
        """
        Generate a storage key based on configured uniqueness scope.
        
        Args:
            name: Resource name
            scope_context: Dictionary with scope values:
                - subscription_id: For SUBSCRIPTION scope
                - resource_group: For RESOURCE_GROUP scope
                - management_group_id: For MANAGEMENT_GROUP scope
                - parent_resource_id: For PARENT_RESOURCE scope
        
        Returns:
            Storage key string combining scope and name
        """
        scope_parts = []
        
        for scope in self.UNIQUENESS_SCOPE:
            if scope == UniquenessScope.GLOBAL:
                # No scope prefix for global
                pass
            elif scope == UniquenessScope.SUBSCRIPTION:
                sub_id = scope_context.get("subscription_id", "unknown")
                scope_parts.append(f"sub:{sub_id}")
            elif scope == UniquenessScope.RESOURCE_GROUP:
                rg = scope_context.get("resource_group", "unknown")
                scope_parts.append(f"rg:{rg}")
            elif scope == UniquenessScope.MANAGEMENT_GROUP:
                mg = scope_context.get("management_group_id", "unknown")
                scope_parts.append(f"mg:{mg}")
            elif scope == UniquenessScope.PARENT_RESOURCE:
                parent = scope_context.get("parent_resource_id", "unknown")
                scope_parts.append(f"parent:{parent}")
        
        if scope_parts:
            return f"{'/'.join(scope_parts)}/{name}"
        else:
            return name
    
    def _generate_resource_id(
        self,
        name: str,
        resource_type: str,
        scope_context: Dict[str, str]
    ) -> str:
        """
        Generate a hierarchical resource ID based on scope.
        
        Args:
            name: Resource name
            resource_type: Resource type
            scope_context: Dictionary with scope values
        
        Returns:
            Hierarchical resource ID
        """
        subscription_id = scope_context.get("subscription_id", "unknown")
        
        # Build ID from scopes
        if UniquenessScope.SUBSCRIPTION in self.UNIQUENESS_SCOPE:
            if UniquenessScope.RESOURCE_GROUP in self.UNIQUENESS_SCOPE:
                rg = scope_context.get("resource_group", "unknown")
                return f"/subscriptions/{subscription_id}/resourceGroups/{rg}/providers/{resource_type}/{name}"
            else:
                return f"/subscriptions/{subscription_id}/{resource_type}/{name}"
        elif UniquenessScope.MANAGEMENT_GROUP in self.UNIQUENESS_SCOPE:
            mg = scope_context.get("management_group_id", "unknown")
            return f"/providers/ITL.Management/managementGroups/{mg}/providers/{resource_type}/{name}"
        elif UniquenessScope.PARENT_RESOURCE in self.UNIQUENESS_SCOPE:
            parent_id = scope_context.get("parent_resource_id", "unknown")
            return f"{parent_id}/providers/{resource_type}/{name}"
        else:
            # Global scope
            return f"/providers/{resource_type}/{name}"
    
    def _find_existing(
        self,
        name: str,
        scope_context: Dict[str, str]
    ) -> Optional[Tuple[str, Any]]:
        """
        Find an existing resource in the same scope.
        
        Args:
            name: Resource name
            scope_context: Scope context for lookup
        
        Returns:
            Tuple of (storage_key, resource_data) if found, None otherwise
        """
        storage_key = self._generate_storage_key(name, scope_context)
        
        # Try subscription-scoped lookup first
        if storage_key in self.storage:
            return (storage_key, self.storage[storage_key])
        
        # Fallback to simple name lookup for backward compatibility
        if name in self.storage:
            self.logger.debug(
                f"Found resource using old non-scoped key: {name}. "
                f"New key should be: {storage_key}"
            )
            return (name, self.storage[name])
        
        return None
    
    def _store_resource(
        self,
        name: str,
        resource_data: Any,
        resource_id: str,
        scope_context: Dict[str, str]
    ) -> None:
        """
        Store a resource with scope-based key.
        
        Args:
            name: Resource name
            resource_data: Resource configuration/data
            resource_id: Full hierarchical resource ID
            scope_context: Scope context for key generation
        """
        storage_key = self._generate_storage_key(name, scope_context)
        # Store as tuple: (resource_id, data) for consistency
        self.storage[storage_key] = (resource_id, resource_data)
        self.logger.debug(
            f"Stored resource: key={storage_key}, id={resource_id}, "
            f"scopes={[s.value for s in self.UNIQUENESS_SCOPE]}"
        )
    
    def _retrieve_resource(
        self,
        name: str,
        scope_context: Dict[str, str]
    ) -> Optional[Tuple[str, Any]]:
        """
        Retrieve a resource by name within its scope.
        
        Args:
            name: Resource name
            scope_context: Scope context for lookup
        
        Returns:
            Tuple of (resource_id, resource_data) if found, None otherwise
        """
        existing = self._find_existing(name, scope_context)
        if existing:
            storage_key, stored_data = existing
            if isinstance(stored_data, tuple):
                return stored_data
            else:
                # Old format without resource_id
                resource_id = self._generate_resource_id(name, self.RESOURCE_TYPE, scope_context)
                return (resource_id, stored_data)
        return None
    
    def _list_resources_in_scope(
        self,
        scope_context: Dict[str, str]
    ) -> List[Tuple[str, str, Any]]:
        """
        List all resources within a specific scope.
        
        Args:
            scope_context: Scope context for filtering
        
        Returns:
            List of tuples: (name, resource_id, resource_data)
        """
        resources = []
        subscription_id = scope_context.get("subscription_id", "unknown")
        resource_group = scope_context.get("resource_group", "unknown")
        
        for storage_key, stored_data in self.storage.items():
            # Parse storage key to check if it matches scope
            if isinstance(stored_data, tuple):
                resource_id, resource_data = stored_data
            else:
                # Old format
                resource_data = stored_data
                resource_id = None
            
            # Check if resource belongs to this scope
            matches_scope = self._matches_scope(storage_key, resource_id, scope_context)
            if matches_scope:
                # Extract name from storage_key
                if "/" in storage_key:
                    name = storage_key.split("/")[-1]
                else:
                    name = storage_key
                
                resources.append((name, resource_id, resource_data))
        
        return resources
    
    def _matches_scope(
        self,
        storage_key: str,
        resource_id: Optional[str],
        scope_context: Dict[str, str]
    ) -> bool:
        """
        Check if a resource matches the given scope.
        
        Args:
            storage_key: Storage key of the resource
            resource_id: Resource ID (if available)
            scope_context: Scope context to match against
        
        Returns:
            True if resource is in scope, False otherwise
        """
        if UniquenessScope.SUBSCRIPTION in self.UNIQUENESS_SCOPE:
            subscription_id = scope_context.get("subscription_id", "unknown")
            if resource_id:
                return resource_id.startswith(f"/subscriptions/{subscription_id}/")
            elif f"sub:{subscription_id}" in storage_key:
                return True
            # Fallback for non-scoped resources
            elif "/" not in storage_key or not storage_key.startswith("sub:"):
                return True
        
        if UniquenessScope.RESOURCE_GROUP in self.UNIQUENESS_SCOPE:
            resource_group = scope_context.get("resource_group", "unknown")
            if resource_id:
                return f"/resourceGroups/{resource_group}/" in resource_id
            elif f"rg:{resource_group}" in storage_key:
                return True
        
        # If no specific scope filters applied, include the resource
        return True
    
    def _delete_resource(
        self,
        name: str,
        scope_context: Dict[str, str]
    ) -> bool:
        """
        Delete a resource from storage.
        
        Args:
            name: Resource name
            scope_context: Scope context for deletion
        
        Returns:
            True if deleted, False if not found
        """
        existing = self._find_existing(name, scope_context)
        if existing:
            storage_key, _ = existing
            del self.storage[storage_key]
            self.logger.debug(f"Deleted resource: key={storage_key}")
            return True
        return False
    
    def check_duplicate(
        self,
        name: str,
        scope_context: Dict[str, str]
    ) -> Optional[str]:
        """
        Check if a resource with this name already exists in the scope.
        
        Args:
            name: Resource name to check
            scope_context: Scope context
        
        Returns:
            Resource ID if exists, None otherwise
        """
        existing = self._find_existing(name, scope_context)
        if existing:
            _, stored_data = existing
            if isinstance(stored_data, tuple):
                resource_id, _ = stored_data
                return resource_id
            else:
                # Old format - generate ID
                return self._generate_resource_id(name, self.RESOURCE_TYPE, scope_context)
        return None
    
    def create_resource(
        self,
        name: str,
        resource_data: Any,
        resource_type: str,
        scope_context: Dict[str, str]
    ) -> Tuple[str, Any]:
        """
        Create and store a new resource.
        
        Args:
            name: Resource name
            resource_data: Resource configuration
            resource_type: Resource type for ID generation
            scope_context: Scope context (subscription_id, resource_group, etc.)
        
        Returns:
            Tuple of (resource_id, resource_data)
        
        Raises:
            ValueError: If resource already exists in scope
        """
        # Check for duplicates
        existing_id = self.check_duplicate(name, scope_context)
        if existing_id:
            raise ValueError(
                f"Resource '{name}' already exists in {self.UNIQUENESS_SCOPE}: {existing_id}"
            )
        
        # Generate resource ID
        resource_id = self._generate_resource_id(name, resource_type, scope_context)
        
        # Store resource
        self._store_resource(name, resource_data, resource_id, scope_context)
        
        return (resource_id, resource_data)
    
    def get_resource(
        self,
        name: str,
        scope_context: Dict[str, str]
    ) -> Optional[Tuple[str, Any]]:
        """
        Retrieve a resource by name.
        
        Args:
            name: Resource name
            scope_context: Scope context
        
        Returns:
            Tuple of (resource_id, resource_data) if found, None otherwise
        """
        return self._retrieve_resource(name, scope_context)
    
    def list_resources(
        self,
        scope_context: Dict[str, str]
    ) -> List[Tuple[str, str, Any]]:
        """
        List all resources in a scope.
        
        Args:
            scope_context: Scope context for filtering
        
        Returns:
            List of (name, resource_id, resource_data) tuples
        """
        return self._list_resources_in_scope(scope_context)
    
    def delete_resource(
        self,
        name: str,
        scope_context: Dict[str, str]
    ) -> bool:
        """
        Delete a resource.
        
        Args:
            name: Resource name
            scope_context: Scope context
        
        Returns:
            True if deleted, False if not found
        """
        return self._delete_resource(name, scope_context)
