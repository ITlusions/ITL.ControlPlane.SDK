"""
Example: ResourceGroupHandler with Lifecycle Hooks

Demonstrates how to use lifecycle hooks from ResourceProvider base class
for a resource group handler with pre/post operation logic.

Lifecycle hooks are now built into ResourceProvider base class. This handler
shows how to combine hooks with other mixins (validation, timestamps, scopes).
"""

import logging
from typing import Any, Dict, Tuple, Type
from pydantic import BaseModel, validator

from .advanced import (
    ValidatedResourceHandler,
    TimestampedResourceHandler,
    ProvisioningStateHandler,
)
from .scoped import ScopedResourceHandler, UniquenessScope

logger = logging.getLogger(__name__)


class ResourceGroupSchema(BaseModel):
    """Pydantic schema for resource group validation."""
    
    name: str
    location: str
    tags: Dict[str, str] = {}
    
    @validator('name')
    def validate_name(cls, v):
        """Validate RG name follows Azure naming rules."""
        if not v or len(v) < 1 or len(v) > 90:
            raise ValueError(f"RG name must be 1-90 chars, got {len(v)}")
        if not all(c.isalnum() or c in '-_.' for c in v):
            raise ValueError("RG name contains invalid characters")
        return v
    
    @validator('location')
    def validate_location(cls, v):
        """Ensure location is specified."""
        if not v:
            raise ValueError("Location is required")
        return v


class ResourceGroupHandler(
    ValidatedResourceHandler,
    TimestampedResourceHandler,
    ProvisioningStateHandler,
    ScopedResourceHandler
):
    """
    Resource Group Handler with full lifecycle hooks.
    
    Lifecycle hooks (on_creating, on_created, on_deleting, on_deleted) are
    provided by ResourceProvider base class. This handler demonstrates how
    to combine them with other mixins for full functionality.
    
    Demonstrates:
    - Pre-creation validation (on_creating - in ResourceProvider)
    - Post-creation setup (on_created - in ResourceProvider)
    - Pre-deletion checks (on_deleting - in ResourceProvider)
    - Post-deletion cleanup (on_deleted - in ResourceProvider)
    - Mixed with other handlers for validation, timestamps, scopes
    
    Usage:
        handler = ResourceGroupHandler(storage_dict)
        
        # Create with hooks (inherited from ResourceProvider)
        rg_id, rg_data = handler.create_resource(
            "prod-rg",
            {"location": "eastus", "tags": {"env": "prod"}},
            "ITL.Resources/resourcegroups",
            {"subscription_id": "sub-123", "user_id": "user@company.com"}
        )
        # Hooks called: on_creating → create → on_created
        
        # Delete with hooks (inherited from ResourceProvider)
        success = handler.delete_resource(
            "prod-rg",
            {"subscription_id": "sub-123", "user_id": "user@company.com"}
        )
        # Hooks called: on_deleting → delete → on_deleted
    """
    
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION]
    RESOURCE_TYPE = "resourcegroups"
    SCHEMA_CLASS = ResourceGroupSchema
    
    def __init__(self, storage: Dict[str, Any]):
        """Initialize handler."""
        super().__init__(storage)
        # Track child resources for deletion checks
        self._child_resources = {}
        # Track external integrations (CMDB, monitoring, etc.)
        self._cmdb_entries = {}
    
    # ===================================================================
    # Pre-Creation: Validation and Policy Checks
    # ===================================================================
    
    async def on_creating(
        self,
        name: str,
        resource_data: Dict[str, Any],
        resource_type: str,
        scope_context: Dict[str, Any]
    ) -> None:
        """
        Pre-creation hook: Validate RG and check policies.
        
        Can raise exception to abort creation.
        """
        logger.info(f"[PRE-CREATE] Validating resource group: {name}")
        
        subscription_id = scope_context.get("subscription_id")
        user_id = scope_context.get("user_id", "system")
        location = resource_data.get("location")
        tags = resource_data.get("tags", {})
        
        # 1. Check naming conventions
        if name.startswith("test-") and "environment" not in tags:
            logger.warning(f"Test RG {name} missing environment tag")
        
        # 2. Validate location is in allowed regions
        ALLOWED_REGIONS = ["eastus", "westus", "eastus2", "westeurope", "southeastasia"]
        if location and location not in ALLOWED_REGIONS:
            raise ValueError(
                f"Location '{location}' not in approved regions: {ALLOWED_REGIONS}"
            )
        
        # 3. Enforce required tags for production
        if name.startswith("prod-"):
            required_tags = ["owner", "environment", "cost-center"]
            missing = [t for t in required_tags if t not in tags]
            if missing:
                raise ValueError(
                    f"Production RGs require tags: {missing}. Got: {list(tags.keys())}"
                )
        
        # 4. Check quota/limits
        # In real scenario, would check against subscription limits
        existing_count = len([k for k in self.storage.keys() 
                             if k.startswith(f"{subscription_id}/resourcegroups/")])
        if existing_count > 1000:
            raise ValueError(
                f"Subscription {subscription_id} has reached RG quota (1000)"
            )
        
        logger.info(
            f"[PRE-CREATE] Validation passed for: {name} "
            f"location={location} user={user_id}"
        )
    
    # ===================================================================
    # Post-Creation: Setup and Integrations
    # ===================================================================
    
    async def on_created(
        self,
        request: Dict[str, Any],
        response: Dict[str, Any]
    ) -> None:
        """
        Post-creation hook: Setup monitoring, CMDB, notifications.
        
        Cannot abort (resource already created).
        Exceptions are logged but don't fail.
        """
        try:
            rg_id = response.get("id")
            rg_name = response.get("name")
            location = response.get("location")
            tags = response.get("tags", {})
            
            logger.info(f"[POST-CREATE] Setting up RG: {rg_name} ({rg_id})")
            
            # 1. Register in CMDB
            await self._register_in_cmdb(rg_id, rg_name, location, tags)
            
            # 2. Setup monitoring/alerting
            await self._setup_monitoring(rg_id, rg_name)
            
            # 3. Apply default policies
            await self._apply_policies(rg_id, rg_name, tags)
            
            # 4. Send notification
            await self._notify_creation(rg_name, location, tags)
            
            logger.info(f"[POST-CREATE] Setup complete for: {rg_name}")
            
        except Exception as e:
            # Log but don't fail - RG is already created
            logger.error(
                f"[POST-CREATE] Setup failed for {rg_name}: {str(e)}. "
                f"RG created but integrations pending."
            )
    
    # ===================================================================
    # Pre-Deletion: Validation and Graceful Shutdown
    # ===================================================================
    
    async def on_deleting(
        self,
        name: str,
        scope_context: Dict[str, Any]
    ) -> None:
        """
        Pre-deletion hook: Check dependencies and validate deletion.
        
        Can raise exception to abort deletion.
        """
        logger.info(f"[PRE-DELETE] Validating deletion of: {name}")
        
        subscription_id = scope_context.get("subscription_id")
        user_id = scope_context.get("user_id", "system")
        
        # 1. Check for child resources
        child_count = len(self._child_resources.get(name, []))
        if child_count > 0:
            children = self._child_resources[name]
            raise ValueError(
                f"Cannot delete RG {name}: contains {child_count} child resources: "
                f"{children}. Delete children first."
            )
        
        # 2. Check for active deployments
        # In real scenario, would query actual deployments
        logger.info(f"[PRE-DELETE] No active deployments in {name}")
        
        # 3. Require additional confirmation for production RGs
        if name.startswith("prod-") and user_id == "system":
            raise ValueError(
                f"Production RG {name} cannot be deleted by system account. "
                f"Manual approval required."
            )
        
        logger.info(f"[PRE-DELETE] Validation passed for: {name}")
    
    # ===================================================================
    # Post-Deletion: Cleanup and Deregistration
    # ===================================================================
    
    async def on_deleted(
        self,
        name: str,
        scope_context: Dict[str, Any]
    ) -> None:
        """
        Post-deletion hook: Cleanup external integrations.
        
        Cannot abort (resource already deleted).
        Exceptions are logged but don't fail.
        """
        try:
            logger.info(f"[POST-DELETE] Cleaning up: {name}")
            
            # 1. Deregister from CMDB
            await self._deregister_from_cmdb(name)
            
            # 2. Remove monitoring/alerts
            await self._remove_monitoring(name)
            
            # 3. Cleanup policies
            await self._cleanup_policies(name)
            
            # 4. Send notification
            await self._notify_deletion(name)
            
            logger.info(f"[POST-DELETE] Cleanup complete for: {name}")
            
        except Exception as e:
            # Log but don't fail - RG is already deleted
            logger.error(
                f"[POST-DELETE] Cleanup failed for {name}: {str(e)}. "
                f"External integrations may need manual cleanup."
            )
    
    # ===================================================================
    # Helper Methods (Stubs - would integrate with real services)
    # ===================================================================
    
    async def _register_in_cmdb(
        self,
        rg_id: str,
        rg_name: str,
        location: str,
        tags: Dict[str, str]
    ) -> None:
        """Register RG in CMDB system."""
        logger.info(f"Registering in CMDB: {rg_id}")
        # Real: await cmdb_client.register({
        #     "id": rg_id,
        #     "name": rg_name,
        #     "type": "resource-group",
        #     "location": location,
        #     "tags": tags
        # })
        self._cmdb_entries[rg_name] = {"id": rg_id, "location": location}
    
    async def _deregister_from_cmdb(self, rg_name: str) -> None:
        """Deregister RG from CMDB."""
        logger.info(f"Deregistering from CMDB: {rg_name}")
        # Real: await cmdb_client.deregister(rg_id)
        if rg_name in self._cmdb_entries:
            del self._cmdb_entries[rg_name]
    
    async def _setup_monitoring(self, rg_id: str, rg_name: str) -> None:
        """Setup monitoring and alerting."""
        logger.info(f"Setting up monitoring for: {rg_name}")
        # Real: await monitoring_service.create_alerts({
        #     "resource_id": rg_id,
        #     "alert_rules": ["cpu > 80%", "disk > 90%"],
        #     "notification_channels": ["ops-team@company.com"]
        # })
    
    async def _remove_monitoring(self, rg_name: str) -> None:
        """Remove monitoring and alerts."""
        logger.info(f"Removing monitoring for: {rg_name}")
        # Real: await monitoring_service.delete_alerts(filter={"resource": rg_name})
    
    async def _apply_policies(
        self,
        rg_id: str,
        rg_name: str,
        tags: Dict[str, str]
    ) -> None:
        """Apply default policies to RG."""
        logger.info(f"Applying policies to: {rg_name}")
        # Real: await policy_service.apply_policies({
        #     "resource_group_id": rg_id,
        #     "policies": [
        #         "enforce-tagging",
        #         "require-encryption",
        #         "restrict-locations"
        #     ]
        # })
    
    async def _cleanup_policies(self, rg_name: str) -> None:
        """Remove policies from RG."""
        logger.info(f"Cleaning up policies for: {rg_name}")
        # Real: await policy_service.cleanup_policies(resource_group=rg_name)
    
    async def _notify_creation(
        self,
        rg_name: str,
        location: str,
        tags: Dict[str, str]
    ) -> None:
        """Send creation notification."""
        owner = tags.get("owner", "unknown")
        logger.info(f"Notifying owner {owner} about RG creation: {rg_name}")
        # Real: await slack_client.send_message(
        #     channel=f"@{owner}",
        #     text=f"RG {rg_name} created in {location}"
        # )
    
    async def _notify_deletion(self, rg_name: str) -> None:
        """Send deletion notification."""
        logger.info(f"Notifying about RG deletion: {rg_name}")
        # Real: await slack_client.send_message(
        #     channel="#infra",
        #     text=f"RG {rg_name} has been deleted"
        # )


# ===================================================================
# Example Usage
# ===================================================================

if __name__ == "__main__":
    import asyncio
    
    # Setup handler
    storage = {}
    handler = ResourceGroupHandler(storage)
    
    async def demo():
        """Demonstrate lifecycle hooks in action."""
        
        print("\n" + "="*70)
        print("DEMO: ResourceGroupHandler with Lifecycle Hooks")
        print("="*70)
        
        # ====== CREATE ======
        print("\n1. CREATE with hooks:")
        print("-" * 70)
        
        spec = {
            "location": "eastus",
            "tags": {"owner": "alice@company.com", "environment": "test"}
        }
        
        try:
            rg_id, rg_data = handler.create_resource(
                "test-rg",
                spec,
                "ITL.Resources/resourcegroups",
                {"subscription_id": "sub-123", "user_id": "alice@company.com"}
            )
            print(f"✓ Created: {rg_id}")
            print(f"  Data: {rg_data}")
        except ValueError as e:
            print(f"✗ Creation failed: {e}")
        
        # ====== CREATE PROD (will fail validation) ======
        print("\n2. CREATE prod RG without required tags (should fail):")
        print("-" * 70)
        
        try:
            rg_id, rg_data = handler.create_resource(
                "prod-app",
                {"location": "eastus"},  # Missing required tags
                "ITL.Resources/resourcegroups",
                {"subscription_id": "sub-123", "user_id": "alice@company.com"}
            )
            print(f"✓ Created: {rg_id}")
        except ValueError as e:
            print(f"✗ Validation failed (expected): {e}")
        
        # ====== DELETE ======
        print("\n3. DELETE with hooks:")
        print("-" * 70)
        
        success = handler.delete_resource(
            "test-rg",
            {"subscription_id": "sub-123", "user_id": "alice@company.com"}
        )
        if success:
            print("✓ Deleted: test-rg")
        else:
            print("✗ Deletion failed")
        
        print("\n" + "="*70)
    
    asyncio.run(demo())
