# Scoped Resource Handler - Architecture Complete ✅

## Summary

Successfully implemented a **configurable, reusable base class for scope-aware resource uniqueness** across the ITL ControlPlane SDK. This enables automatic duplicate detection and prevention for any resource type with customizable scope levels.

## What Was Created

### 1. Core Base Class: `ScopedResourceHandler`
**File:** `ITL.ControlPanel.SDK/src/itl_controlplane_sdk/providers/scoped_resources.py`

- Generic base class for scope-aware resources
- Configurable uniqueness scopes (global, subscription, resource group, management group, parent resource)
- Automatic storage key generation based on scope configuration
- Duplicate detection and prevention (raises `ValueError` for duplicates)
- Scope-aware retrieval, listing, and deletion
- Backward compatibility with non-scoped storage format

**Key Features:**
```python
class ScopedResourceHandler:
    UNIQUENESS_SCOPE = [UniquenessScope.GLOBAL]  # Configure per resource type
    RESOURCE_TYPE = "unknown"
    
    # Methods provided:
    - create_resource()      # Create with automatic duplicate detection
    - get_resource()         # Retrieve by name within scope
    - list_resources()       # List all in scope
    - delete_resource()      # Delete from scope
    - check_duplicate()      # Check if name exists in scope
```

### 2. Specialized Handler: `ResourceGroupHandler`
**File:** `ITL.ControlPanel.SDK/src/itl_controlplane_sdk/providers/resource_group_handler.py`

Example implementation showing how to extend `ScopedResourceHandler`:

```python
class ResourceGroupHandler(ScopedResourceHandler):
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION]
    RESOURCE_TYPE = "resourcegroups"
    
    # Domain-specific convenience methods:
    - create_from_properties()
    - get_by_name()
    - list_by_subscription()
    - delete_by_name()
```

### 3. SDK Exports
**File:** `ITL.ControlPanel.SDK/src/itl_controlplane_sdk/providers/__init__.py`

Updated to export:
```python
from .scoped_resources import ScopedResourceHandler, UniquenessScope
from .resource_group_handler import ResourceGroupHandler
```

## Architecture Benefits

| Aspect | Benefit |
|--------|---------|
| **Reusability** | One base class for all resource types (VMs, Disks, Storage, etc.) |
| **Configurability** | Define unique scope per resource type via `UNIQUENESS_SCOPE` |
| **Consistency** | All resources behave identically for duplicate detection |
| **Testability** | Logic can be tested independently of resource type |
| **Maintainability** | Bug fixes apply to all resource types automatically |
| **Extensibility** | Easy to add domain-specific methods (see `ResourceGroupHandler`) |
| **Performance** | O(1) duplicate detection using storage keys |
| **Backward Compatible** | Supports both old and new storage formats |

## Usage Examples

### Basic Usage Pattern

```python
from itl_controlplane_sdk.providers import ScopedResourceHandler, UniquenessScope

# 1. Define your handler
class MyResourceHandler(ScopedResourceHandler):
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION]
    RESOURCE_TYPE = "myresources"

# 2. Initialize in your provider
handler = MyResourceHandler(storage_dict)

# 3. Create resources
try:
    resource_id, data = handler.create_resource(
        "my-resource",
        {"config": "value"},
        "ITL.Custom/myresources",
        {"subscription_id": "sub-123"}
    )
except ValueError as e:
    # Handle duplicate: "Resource 'my-resource' already exists in [subscription]: /subscriptions/..."
```

### Advanced Configuration

```python
# Subscription-scoped (Resource Groups, Subscriptions)
class RGHandler(ScopedResourceHandler):
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION]

# Resource Group-scoped (VMs, Disks, NICs)
class VMHandler(ScopedResourceHandler):
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION, UniquenessScope.RESOURCE_GROUP]

# Management Group-scoped (Policies, Blueprint)
class PolicyHandler(ScopedResourceHandler):
    UNIQUENESS_SCOPE = [UniquenessScope.MANAGEMENT_GROUP]

# Globally unique (Storage Accounts, App Services)
class StorageHandler(ScopedResourceHandler):
    UNIQUENESS_SCOPE = [UniquenessScope.GLOBAL]
```

## Integration with Core Provider

The `CoreProvider` now uses `ResourceGroupHandler`:

```python
class CoreProvider(ResourceProvider):
    def __init__(self):
        super().__init__("ITL.Core")
        self.resource_groups = {}
        
        # Initialize the handler
        self.rg_handler = ResourceGroupHandler(self.resource_groups)
    
    async def _handle_resource_group(self, name, properties, operation):
        subscription_id = properties.get("_subscription_id")
        
        if operation == "create_or_update":
            try:
                response = self.rg_handler.create_from_properties(
                    name, properties, subscription_id, self.default_location
                )
                return ResourceResponse(**response)
            except ValueError:
                # Duplicate detected - return 409 Conflict
                return ResourceResponse(properties={"error": ...})
```

## Storage Key Format

Automatic storage key generation based on scope configuration:

```
GLOBAL:                    "resource-name"
SUBSCRIPTION:              "sub:sub-123/resource-name"
SUBSCRIPTION+RESOURCE_GROUP: "sub:sub-123/rg:rg-prod/resource-name"
MANAGEMENT_GROUP:          "mg:mg-prod/resource-name"
```

## Resource ID Format

Automatic resource ID generation:

```
SUBSCRIPTION:    "/subscriptions/{sub}/ITL.Core/resourcegroups/{name}"
SUBSCRIPTION+RG: "/subscriptions/{sub}/resourceGroups/{rg}/providers/ITL.Resources/vms/{name}"
MANAGEMENT_GROUP: "/providers/Microsoft.Management/managementGroups/{mg}/providers/ITL.Policies/policies/{name}"
```

## Test Results

All existing tests pass with the new handler-based implementation:

✅ **test_rg_scoping.py** - Basic operations
- Create subscription
- Create resource group
- Verify duplicate detection (409)
- List resource groups
- Get specific resource group

✅ **test_rg_uniqueness.py** - Duplicate prevention
- Create first RG
- Verify GET returns it
- Attempt duplicate (blocked)
- Create different RG in same subscription

✅ **test_rg_cross_subscription.py** - Cross-subscription isolation
- Create two subscriptions
- Create RG with same name in each (works)
- Verify different IDs
- Verify duplicate detection only within subscription
- Verify list/get are subscription-scoped

## Files Modified

### SDK Changes
1. **New:** `itl_controlplane_sdk/providers/scoped_resources.py` (370+ lines)
   - Core `ScopedResourceHandler` base class
   - `UniquenessScope` enum

2. **New:** `itl_controlplane_sdk/providers/resource_group_handler.py` (160+ lines)
   - `ResourceGroupHandler` example implementation
   - Domain-specific convenience methods

3. **Updated:** `itl_controlplane_sdk/providers/__init__.py`
   - Export `ScopedResourceHandler` and `UniquenessScope`
   - Export `ResourceGroupHandler`

### Provider Changes
1. **Updated:** `core-provider/src/core_provider.py`
   - Import `ResourceGroupHandler`
   - Initialize `self.rg_handler` in `__init__`
   - Refactored `_handle_resource_group()` to use handler
   - Simplified from ~115 lines to ~75 lines (40% reduction)
   - All logic delegated to handler with error handling

### Documentation
1. **New:** `ITL.ControlPanel.SDK/docs/SCOPED_RESOURCE_HANDLER.md` (500+ lines)
   - Complete API reference
   - Configuration examples for different resource types
   - Best practices and patterns
   - Migration guide
   - Testing examples

## Key Capabilities

### 1. Automatic Duplicate Detection
```python
try:
    handler.create_resource("name", data, type, scope)
except ValueError as e:
    # "Resource 'name' already exists in subscription: /subscriptions/sub/..."
```

### 2. Flexible Scope Configuration
```python
# Same resource name allowed across different scopes
UNIQUENESS_SCOPE = [
    UniquenessScope.SUBSCRIPTION,
    UniquenessScope.RESOURCE_GROUP
]
# Now unique only within the combination of sub + RG
```

### 3. Transparent Storage Key Management
```python
# Handler generates: "sub:sub-123/rg:prod-rg/resource-name"
# User only provides: name and scope_context
scope_context = {"subscription_id": "sub-123", "resource_group": "prod-rg"}
```

### 4. Scope-Aware Operations
```python
# List returns only resources in specified subscription
resources = handler.list_resources({"subscription_id": "sub-1"})

# Get only finds resources in specified scope
result = handler.get_resource("name", {"subscription_id": "sub-1"})
```

### 5. Backward Compatibility
```python
# Old format: storage["name"]
# New format: storage["sub:sub-1/name"]
# Handler checks new first, falls back to old
```

## How to Use in Your Resources

### For Resource Group-Scoped Resources (e.g., Virtual Machines)

```python
class VirtualMachineHandler(ScopedResourceHandler):
    UNIQUENESS_SCOPE = [
        UniquenessScope.SUBSCRIPTION,
        UniquenessScope.RESOURCE_GROUP
    ]
    RESOURCE_TYPE = "virtualmachines"
    
    def __init__(self, storage_dict):
        super().__init__(storage_dict)
    
    def create_from_spec(self, name, vm_spec, subscription_id, resource_group):
        """Create VM with automatic duplicate detection within RG"""
        return self.create_resource(
            name,
            vm_spec,
            "ITL.Compute/virtualmachines",
            {
                "subscription_id": subscription_id,
                "resource_group": resource_group
            }
        )

# Usage
handler = VirtualMachineHandler(vm_storage)
try:
    vm_id, vm_data = handler.create_from_spec(
        "web-server-01",
        {"size": "Standard_B2s", ...},
        "prod-sub",
        "app-rg"
    )
except ValueError:
    # VM with this name already exists in prod-sub/app-rg
```

### For Globally Unique Resources (e.g., Storage Accounts)

```python
class StorageAccountHandler(ScopedResourceHandler):
    UNIQUENESS_SCOPE = [UniquenessScope.GLOBAL]
    RESOURCE_TYPE = "storageaccounts"

# Usage - storage account name must be globally unique
handler = StorageAccountHandler(storage)
try:
    sa_id, sa_data = handler.create_resource(
        "myuniqueaccount123",  # Must be globally unique
        {"replication": "RA-GRS", ...},
        "ITL.Storage/storageaccounts",
        {}  # No scope needed for global
    )
except ValueError:
    # Storage account name already taken globally
```

## Future Enhancements

1. **Rate Limiting per Scope** - Limit resource creation rate per subscription
2. **Quotas** - Enforce limits on resources per scope
3. **Tagging by Scope** - Automatically tag resources by their scope
4. **Retention Policies** - Delete old resources based on scope
5. **Audit Logging** - Per-scope operation audit trails
6. **Soft Delete** - Implement soft delete with restore per scope
7. **Multi-Scope Uniqueness** - Support "unique within subscription" OR "unique globally"

## Migration Path

For existing implementations without the handler:

1. **Phase 1:** Create your handler class (inherits `ScopedResourceHandler`)
2. **Phase 2:** Update provider to use handler (delegate operations)
3. **Phase 3:** Test backward compatibility with old resources
4. **Phase 4:** Migrate old resources to new storage format (optional)

No breaking changes required - the handler supports both old and new storage formats simultaneously.

## References

- [ScopedResourceHandler Implementation](../src/itl_controlplane_sdk/providers/scoped_resources.py)
- [ResourceGroupHandler Example](../src/itl_controlplane_sdk/providers/resource_group_handler.py)
- [Core Provider Integration](../../ITL.ControlPlane.ResourceProvider.Core/core-provider/src/core_provider.py)
- [Complete Documentation](../docs/SCOPED_RESOURCE_HANDLER.md)

---

**Status:** ✅ Production Ready

All tests pass. Implementation is backward compatible. Ready for deployment to production and for extending to additional resource types.
