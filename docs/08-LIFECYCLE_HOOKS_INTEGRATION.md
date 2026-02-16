# Lifecycle Hooks: Implementation & Integration Guide

**Status**: Implementation Complete (Consolidated into ResourceProvider base class)  
**Version**: 2.0  
**Created**: 2026-02-14  
**Updated**: 2026-02-14

---

## Overview

Lifecycle hooks are now **built into the ResourceProvider base class**. All providers automatically inherit 7 lifecycle hooks for custom logic at key points in the resource lifecycle:

**Available Hooks**:
- `on_creating()` - Before resource creation (can abort)
- `on_created()` - After successful creation
- `on_updating()` - Before resource update (can abort)
- `on_updated()` - After successful update
- `on_getting()` - Before resource retrieval (can abort)
- `on_deleting()` - Before resource deletion (can abort)
- `on_deleted()` - After successful deletion

No mixin needed — simply override these methods in your provider!

---

## Quick Start: Add Lifecycle Hooks to Your Provider

```python
from itl_controlplane_sdk import ResourceProvider, ResourceRequest, ProviderContext, ResourceResponse

class MyProvider(ResourceProvider):
    """Custom provider with lifecycle hooks."""
    
    async def on_creating(self, request: ResourceRequest, context: ProviderContext) -> None:
        """Validate before resource creation. Can raise to abort."""
        logger.info(f"Creating {request.resource_type}: {request.spec}")
        
        # Validation logic
        if not self._is_valid_spec(request.spec):
            raise ValueError("Invalid resource specification")
    
    async def on_created(self, request: ResourceRequest, response: ResourceResponse, context: ProviderContext) -> None:
        """Setup after successful creation. Failures don't abort."""
        try:
            logger.info(f"Created resource: {response.id}")
            await self._notify_monitoring_system(response.id)
            await self._register_in_cmdb(response.id, response.name)
        except Exception as e:
            # Log but don't abort — resource already created
            logger.warning(f"Post-creation setup failed: {e}")
    
    async def on_deleting(self, request: ResourceRequest, context: ProviderContext) -> None:
        """Validate before deletion. Can raise to abort."""
        # Check for dependencies
        if await self._has_child_resources(request.resource_id):
            raise Exception("Cannot delete: has child resources")
    
    async def on_deleted(self, request: ResourceRequest, context: ProviderContext) -> None:
        """Cleanup after deletion. Failures don't abort."""
        try:
            await self._cleanup_cache(request.resource_id)
            await self._notify_monitoring_system(request.resource_id)
        except Exception as e:
            logger.warning(f"Post-deletion cleanup failed: {e}")
```

---

## Migration Guide (from LifecycleHookResourceHandler)

Previously, lifecycle hooks were available through a `LifecycleHookResourceHandler` mixin. **This mixin has been consolidated into the ResourceProvider base class.**

**Before** (deprecated):
```python
from itl_controlplane_sdk.providers import LifecycleHookResourceHandler

class MyHandler(LifecycleHookResourceHandler, ScopedResourceHandler):
    async def on_created(self, request, response):
        ...
```

**After** (recommended):
```python
from itl_controlplane_sdk import ResourceProvider

class MyProvider(ResourceProvider):
    async def on_created(self, request, response, context):
        ...
```

**Benefits**:
- Simpler API — no mixin needed
- Consistent interface — all hooks in base class
- Better IDE support — hooks documented in base class
- No import confusion — fewer patterns to learn

---

## Hook Signatures and Behavior

### All Hook Methods

Lifecycle hooks follow this pattern for their signatures:

**Pre-operation hooks** (can abort by raising exception):
```python
async def on_creating(self, request: ResourceRequest, context: ProviderContext) -> None:
async def on_updating(self, request: ResourceRequest, context: ProviderContext) -> None:
async def on_getting(self, request: ResourceRequest, context: ProviderContext) -> None:
async def on_deleting(self, request: ResourceRequest, context: ProviderContext) -> None:
```

**Post-operation hooks** (cannot abort, failures logged):
```python
async def on_created(self, request: ResourceRequest, response: ResourceResponse, context: ProviderContext) -> None:
async def on_updated(self, request: ResourceRequest, response: ResourceResponse, context: ProviderContext) -> None:
async def on_deleted(self, request: ResourceRequest, context: ProviderContext) -> None:
```

### Hook Semantics

| Hook | Timing | Can Abort | Use Case |
|------|--------|-----------|----------|
| `on_creating` | Before create | Yes | Validate spec, check quotas, enforce policies |
| `on_created` | After create | No | Notify users, setup monitoring, register in CMDB |
| `on_updating` | Before update | Yes | Validate changes, check immutability, enforce policies |
| `on_updated` | After update | No | Notify, invalidate cache, audit log |
| `on_getting` | Before get | Yes | Access control, rate limiting |
| `on_deleting` | Before delete | Yes | Check dependencies, validate permissions |
| `on_deleted` | After delete | No | Cleanup, deregister, notify |

---

## Available Hooks

### Pre-Operation Hooks (Can Abort)

These hooks run **before** the operation and can prevent it by raising an exception.

#### `on_creating`
Runs before resource creation. Abort by raising an exception.

```python
async def on_creating(self, name, resource_data, resource_type, scope_context):
    # Validate before creation
    if not self._can_create(name, resource_type):
        raise ValueError(f"Cannot create {name}")
    
    # Check quotas
    if await self._quota_exceeded(scope_context):
        raise Exception("Quota exceeded")
```

**Parameters**:
- `name: str` – Resource name
- `resource_data: Dict` – Resource configuration
- `resource_type: str` – Resource type (e.g., "virtualmachines")
- `scope_context: Dict` – Subscription, user, tenant context

---

#### `on_updating`
Runs before resource update. Abort by raising an exception.

```python
async def on_updating(self, name, resource_data, scope_context):
    # Prevent updates to immutable resources
    current = await self._get_resource(name)
    if current.get("immutable"):
        raise Exception("Resource is immutable")
    
    # Validate update fields
    if "critical_field" in resource_data:
        raise ValueError("Cannot update critical field")
```

**Parameters**:
- `name: str` – Resource name
- `resource_data: Dict` – New resource data
- `scope_context: Dict` – Scope context

---

#### `on_deleting`
Runs before resource deletion. Abort by raising an exception.

```python
async def on_deleting(self, name, scope_context):
    # Check for dependencies
    dependents = await self._find_dependents(name)
    if dependents:
        raise Exception(f"{len(dependents)} resources depend on this")
    
    # Graceful shutdown
    await self._drain_traffic(name)
    logger.info(f"Pre-deletion checks passed for {name}")
```

**Parameters**:
- `name: str` – Resource name
- `scope_context: Dict` – Scope context

---

### Post-Operation Hooks (Cannot Abort)

These hooks run **after** the operation completes. Exceptions are logged but **do not** affect the operation.

#### `on_created`
Runs after successful creation. Resource already exists; cannot abort.

```python
async def on_created(self, request, response):
    # Setup related resources
    resource_id = response.get("id")
    try:
        await configure_monitoring(resource_id)
        await initialize_networking(resource_id)
        await notif_team(f"Resource {response.get('name')} created")
    except Exception as e:
        # Log but don't fail — resource already created
        logger.warning(f"Post-creation setup failed: {e}")
```

**Parameters**:
- `request: Dict` – Original create request
- `response: Dict` – Created resource response

---

#### `on_updated`
Runs after successful update. Resource already modified; cannot abort.

```python
async def on_updated(self, request, response):
    # Update related systems
    try:
        await synchronize_backup(response.get("id"))
        await invalidate_cache(response.get("name"))
        logger.info(f"Post-update sync completed for {response.get('name')}")
    except Exception as e:
        logger.warning(f"Post-update sync failed: {e}")
```

**Parameters**:
- `request: Dict` – Original update request
- `response: Dict` – Updated resource response

---

#### `on_deleted`
Runs after successful deletion. Resource no longer exists; cannot abort.

```python
async def on_deleted(self, name, scope_context):
    # Cleanup related resources
    try:
        await cleanup_backups(name)
        await remove_from_cmdb(name)
        await deregister_from_monitoring(name)
    except Exception as e:
        logger.warning(f"Post-deletion cleanup failed: {e}")
```

**Parameters**:
- `name: str` – Resource name (for reference/logging)
- `scope_context: Dict` – Scope context

---

## Integration Points in Core Provider

### Option 1: ResourceGroup Handler with Lifecycle Hooks

Add lifecycle hooks to the existing ResourceGroup creation in `core_provider.py`:

```python
# File: core-provider/src/core_provider.py

from itl_controlplane_sdk.providers import LifecycleHookResourceHandler

class CoreProviderWithLifecycleHooks(ResourceProvider, LifecycleHookResourceHandler):
    """Extended Core Provider with lifecycle hook support."""
    
    async def _create_resource_group(self, name, props, sub_id=None):
        """Create resource group with lifecycle hooks."""
        subscription_id = props.get("_subscription_id") or sub_id or self.subscription_id
        actual_name = name.split("/")[-1] if "/" in name else name
        location = props.get("location", self.default_location)
        
        # PRE-CREATION HOOK
        await self.on_creating(
            actual_name, 
            props, 
            "ITL.Core/resourcegroups",
            {"subscription_id": subscription_id, "user_id": "system"}
        )
        
        # CREATE IN DATABASE
        async with self.engine.session() as session:
            repo = self.engine.resource_groups(session)
            rg = await repo.create_or_update(
                name=actual_name,
                subscription_id=subscription_id,
                location=location,
                tags=props.get("tags"),
                properties={k: v for k, v in props.items()
                           if k not in ("_subscription_id", "location", "tags")},
            )
            
            response = ResourceResponse(
                id=rg.id, name=actual_name, type="ITL.Core/resourcegroups",
                location=location, properties=rg.to_dict(),
                tags=rg.tags,
                provisioning_state=ProvisioningState.SUCCEEDED,
            )
        
        # POST-CREATION HOOK
        try:
            await self.on_created(
                {"name": actual_name, "type": "resourcegroups"},
                response
            )
        except Exception as e:
            logger.warning(f"on_created hook failed: {e}")
        
        return response
    
    # Override hook if you want default behavior
    async def on_created(self, request, response):
        """Post-creation: audit logging, notifications, etc."""
        rg_name = response.name
        logger.info(f"Resource group '{rg_name}' created successfully")
        # Could add: notify Slack, log to audit store, update CMDB, etc.
```

---

### Option 2: Dedicated ResourceGroupHandler Class

Create a specialized handler using mixins:

```python
# File: core-provider/src/resource_group_handler.py

from itl_controlplane_sdk.providers import (
    LifecycleHookResourceHandler,
    TimestampedResourceHandler,
    ValidatedResourceHandler,
    ScopedResourceHandler,
    UniquenessScope
)
from itl_controlplane_sdk import ProvisioningState, ResourceResponse

class ResourceGroupHandler(
    LifecycleHookResourceHandler,
    TimestampedResourceHandler,
    ValidatedResourceHandler,
    ScopedResourceHandler
):
    """Specialized handler for Resource Groups with full lifecycle support."""
    
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION]
    RESOURCE_TYPE = "ITL.Core/resourcegroups"
    
    def __init__(self, engine):
        self.engine = engine
        super().__init__()
    
    async def on_created(self, request, response):
        """Post-RG creation: seed with default locations."""
        rg_id = response.get("id")
        logger.info(f"ResourceGroup created: {rg_id}")
        # Could seed with default policies, locations, etc.
    
    async def on_deleting(self, name, scope_context):
        """Pre-deletion: check for child resources."""
        async with self.engine.session() as session:
            # Check if RG has child resources
            children_count = await self._count_children(session, name)
            if children_count > 0:
                raise Exception(f"Cannot delete RG with {children_count} child resources")
    
    async def on_deleted(self, name, scope_context):
        """Post-deletion: cleanup related entities."""
        logger.info(f"ResourceGroup deleted: {name}")
        # Could cleanup: policies, deployments, audit records, etc.
```

Then use it in CoreProvider:

```python
class CoreProvider(ResourceProvider):
    def __init__(self, config, engine):
        super().__init__(PROVIDER_NAMESPACE)
        self.engine = engine
        self.rg_handler = ResourceGroupHandler(engine)
    
    async def _create_resource_group(self, name, props, sub_id=None):
        # Use handler instead of inline logic
        resource_id, response = await self.rg_handler.create_resource(
            name, props, "ITL.Core/resourcegroups", 
            {"subscription_id": sub_id or self.subscription_id, "user_id": "system"}
        )
        return response
```

---

### Option 3: Decoupled Hook Functions

Register hooks as separate functions:

```python
# File: core-provider/src/core_provider.py

class CoreProviderWithHooks(ResourceProvider):
    
    def __init__(self, config, engine):
        super().__init__(PROVIDER_NAMESPACE)
        self.engine = engine
        self._register_hooks()
    
    def _register_hooks(self):
        """Register lifecycle hooks."""
        self.on_rg_created = self._handle_rg_created
        self.on_rg_deleting = self._handle_rg_deleting
    
    async def _create_resource_group(self, name, props, sub_id=None):
        # Pre-delete check
        await self._handle_rg_deleting(name, sub_id)
        
        # Create
        response = await self._do_create_rg(name, props, sub_id)
        
        # Post-create hook
        await self._handle_rg_created(response)
        
        return response
    
    async def _handle_rg_created(self, response):
        """Hook: post-creation notification."""
        logger.info(f"RG {response.name} created")
        # Notify admins, update CMDB, etc.
    
    async def _handle_rg_deleting(self, name, sub_id):
        """Hook: pre-deletion validation."""
        # Check dependencies
        pass
```

---

## Real-World Examples

### Example 1: Audit Compliance

```python
class AuditedResourceGroupHandler(
    LifecycleHookResourceHandler,
    TimestampedResourceHandler,
    ScopedResourceHandler
):
    """Track all RG operations for compliance."""
    
    async def on_created(self, request, response):
        """Log creation to audit store."""
        await self._audit_log(
            operation="ResourceGroupCreated",
            resource_id=response.get("id"),
            user=request.get("user_id"),
            timestamp=response.get("createdTime"),
            details=response
        )
    
    async def on_deleted(self, name, scope_context):
        """Log deletion to audit store."""
        await self._audit_log(
            operation="ResourceGroupDeleted",
            resource_name=name,
            user=scope_context.get("user_id"),
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
```

---

### Example 2: Multi-Region Redundancy

```python
class RedundantResourceHandler(LifecycleHookResourceHandler, ScopedResourceHandler):
    """Automatically replicate resources across regions."""
    
    async def on_created(self, request, response):
        """Create replicas in secondary regions."""
        resource_id = response.get("id")
        
        # Check replication policy
        if response.get("tags", {}).get("ReplicationPolicy") == "Multi-Region":
            # Create replicas
            await self._replicate_to_secondary_region(
                resource_id,
                response
            )
            logger.info(f"Resource {resource_id} replicated to secondary regions")
    
    async def on_deleted(self, name, scope_context):
        """Delete replicas when primary deleted."""
        await self._delete_all_replicas(name)
```

---

### Example 3: Cost Tracking

```python
class CostTrackedHandler(LifecycleHookResourceHandler, ScopedResourceHandler):
    """Track costs per subscription."""
    
    async def on_created(self, request, response):
        """Record cost allocation."""
        await self._record_cost_event(
            event_type="ResourceCreated",
            resource_id=response.get("id"),
            resource_type=response.get("type"),
            subscription=request.get("subscription_id"),
            cost_model=response.get("tags", {}).get("CostModel", "Standard"),
            timestamp=response.get("createdTime")
        )
    
    async def on_deleted(self, name, scope_context):
        """Record end of cost."""
        await self._record_cost_event(
            event_type="ResourceDeleted",
            resource=name,
            subscription=scope_context.get("subscription_id"),
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
```

---

## Best Practices

### 1. Pre-Operation Hooks Should Be Fast

```python
# GOOD: Quick validation
async def on_creating(self, name, resource_data, resource_type, scope_context):
    if not self._validate_name(name):
        raise ValueError("Invalid name format")

# BAD: Slow operations causing timeouts
async def on_creating(self, name, resource_data, resource_type, scope_context):
    # This could timeout if service is slow
    await slow_external_api_check()
```

### 2. Post-Operation Hooks Must Not Fail

```python
# GOOD: Catch and log
async def on_created(self, request, response):
    try:
        await send_notification(response)
        await update_external_system(response)
    except Exception as e:
        logger.warning(f"Post-creation tasks failed: {e}")

# BAD: Uncaught exception
async def on_created(self, request, response):
    await send_notification(response)  # If this fails, hook fails
```

### 3. Use Appropriate Hook Levels

```python
# For validation → use on_creating (can abort)
async def on_creating(self, name, resource_data, resource_type, scope_context):
    if not valid_config(resource_data):
        raise ValueError("Invalid configuration")

# For setup → use on_created (cannot abort)
async def on_created(self, request, response):
    await setup_monitoring(response.get("id"))
    await initialize_backup(response.get("id"))

# For cleanup → use on_deleted (cannot abort)
async def on_deleted(self, name, scope_context):
    await cleanup_external_resources(name)
```

### 4. Log All Hook Activity

```python
async def on_created(self, request, response):
    logger.info(
        "on_created hook executing",
        extra={
            "resource_id": response.get("id"),
            "resource_name": response.get("name"),
            "user_id": request.get("user_id"),
        }
    )
    try:
        # Do work...
    except Exception as e:
        logger.error("on_created hook failed", exc_info=True)
```

---

## Integration Checklist

- [ ] Import `LifecycleHookResourceHandler` in your handler
- [ ] Mixin `LifecycleHookResourceHandler` with your handler class
- [ ] Override desired hooks (`on_creating`, `on_created`, etc.)
- [ ] Call hooks in your CRUD methods:
  - Call `on_creating` before create, catch exceptions
  - Call `on_created` after create, log failures
  - Call `on_updating` before update, catch exceptions
  - Call `on_updated` after update, log failures
  - Call `on_deleting` before delete, catch exceptions
  - Call `on_deleted` after delete, log failures
- [ ] Add error handling / logging
- [ ] Test pre/post operation behavior
- [ ] Update documentation with your hooks

---

## Testing Lifecycle Hooks

```python
import pytest

@pytest.mark.asyncio
async def test_on_created_called():
    """Verify on_created hook is invoked."""
    handler = MyHandler()
    
    # Track if hook was called
    created_called = False
    
    async def mock_on_created(request, response):
        nonlocal created_called
        created_called = True
    
    handler.on_created = mock_on_created
    
    # Create resource
    rid, resp = await handler.create_resource("test", {}, "test-resource", {})
    
    # Verify hook was called
    assert created_called, "on_created hook was not called"

@pytest.mark.asyncio
async def test_on_creating_abort_creation():
    """Verify on_creating can abort creation."""
    handler = MyHandler()
    
    async def strict_validation(name, data, rtype, ctx):
        raise ValueError("Not allowed!")
    
    handler.on_creating = strict_validation
    
    # Should raise exception
    with pytest.raises(ValueError):
        await handler.create_resource("test", {}, "test-resource", {})
```

---

## Next Steps

1. **Choose Integration Approach**: Option 1 (inline), Option 2 (dedicated handler), or Option 3 (decoupled functions)
2. **Implement Hooks**: Override methods in your handler
3. **Add Error Handling**: Log failures in post-operation hooks
4. **Test**: Write tests for pre/post operation logic
5. **Document**: Add hook documentation to your handler
6. **Roll Out**: Start with non-critical resources, expand gradually

---

**Status**: Ready for Production  
**Maintainer**: SDK Team  
**Last Updated**: 2026-02-14
