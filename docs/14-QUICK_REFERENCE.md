# Quick Reference: ScopedResourceHandler

## For the Impatient

**Q: What is this?**
A: A base class that handles duplicate detection and storage key management for any Azure-like resource with configurable uniqueness scope.

**Q: How do I use it?**
A: 3 lines to define, 1 line to initialize, 1 line to use.

```python
# Define (once)
class MyHandler(ScopedResourceHandler):
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION]
    RESOURCE_TYPE = "myresources"

# Initialize (once)
handler = MyHandler(storage_dict)

# Use (many times)
handler.create_resource(name, data, type, {"subscription_id": sub_id})
```

---

## Scope Cheat Sheet

```python
# Global unique (Storage Accounts, Subscriptions)
UNIQUENESS_SCOPE = [UniquenessScope.GLOBAL]
Example: name must be globally unique

# Subscription unique (Resource Groups)
UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION]
Example: same RG name allowed in different subscriptions

# RG unique (VMs, Disks, NICs)
UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION, UniquenessScope.RESOURCE_GROUP]
Example: same VM name allowed in different RGs

# Management Group unique (Policies, Blueprints)
UNIQUENESS_SCOPE = [UniquenessScope.MANAGEMENT_GROUP]
Example: same policy allowed in different MGs

# Parent Resource unique (Subnets, IP Configs)
UNIQUENESS_SCOPE = [UniquenessScope.PARENT_RESOURCE]
Example: unique within parent resource
```

---

## Common Task: Add a New Resource Type

### For Subscription-Scoped (like Resource Groups)
```python
from itl_controlplane_sdk.providers import ScopedResourceHandler, UniquenessScope

class SubscriptionHandler(ScopedResourceHandler):
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION]
    RESOURCE_TYPE = "subscriptions"
```

### For RG-Scoped (like Virtual Machines)
```python
class VirtualMachineHandler(ScopedResourceHandler):
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION, UniquenessScope.RESOURCE_GROUP]
    RESOURCE_TYPE = "virtualmachines"
```

### For Globally Unique (like Storage Accounts)
```python
class StorageAccountHandler(ScopedResourceHandler):
    UNIQUENESS_SCOPE = [UniquenessScope.GLOBAL]
    RESOURCE_TYPE = "storageaccounts"
```

---

## API Cheat Sheet

```python
# Create with automatic duplicate check
try:
    resource_id, config = handler.create_resource(
        name="my-resource",
        resource_data={"key": "value"},
        resource_type="Namespace/resourcetype",
        scope_context={"subscription_id": "sub-123"}
    )
except ValueError as e:
    # Duplicate! "Resource 'my-resource' already exists..."
    pass

# Get a resource
result = handler.get_resource(
    name="my-resource",
    scope_context={"subscription_id": "sub-123"}
)
if result:
    resource_id, config = result

# List resources in scope
resources = handler.list_resources(
    scope_context={"subscription_id": "sub-123"}
)
for name, resource_id, config in resources:
    print(name, resource_id)

# Delete a resource
deleted = handler.delete_resource(
    name="my-resource",
    scope_context={"subscription_id": "sub-123"}
)

# Check if name exists (without creating)
existing_id = handler.check_duplicate(
    name="my-resource",
    scope_context={"subscription_id": "sub-123"}
)
if existing_id:
    print(f"Exists: {existing_id}")
```

---

## Storage Key Format

```
GLOBAL:                    "name"
SUBSCRIPTION:              "sub:{sub-id}/name"
SUBSCRIPTION+RG:           "sub:{sub-id}/rg:{rg}/name"
MANAGEMENT_GROUP:          "mg:{mg-id}/name"
PARENT_RESOURCE:           "parent:{parent-id}/name"
```

---

## Resource ID Format

```
SUBSCRIPTION:    /subscriptions/{sub}/resourceGroups/{name}
SUBSCRIPTION+RG: /subscriptions/{sub}/resourceGroups/{rg}/providers/Namespace/type/{name}
GLOBAL:          /providers/Namespace/type/{name}
MANAGEMENT_GROUP: /providers/Microsoft.Management/managementGroups/{mg}/providers/Namespace/type/{name}
```

---

## Error Handling

```python
# Correct way - explicit error handling
try:
    handler.create_resource(name, data, type, scope)
except ValueError as e:
    print(f"Duplicate: {e}")  # Message includes existing resource ID

# Wrong way - silent failures
result = handler.create_resource(name, data, type, scope)
if result is None:  # Won't happen - raises exception instead
    ...
```

---

## With a Provider

```python
class MyProvider(ResourceProvider):
    def __init__(self):
        self.my_resources = {}
        self.handler = MyResourceHandler(self.my_resources)
    
    async def _handle_my_resource(self, name, properties, operation):
        try:
            if operation == "create_or_update":
                resource_id, config = self.handler.create_resource(
                    name, properties, "Namespace/myresource",
                    {"subscription_id": properties.get("_subscription_id")}
                )
                return ResourceResponse(
                    id=resource_id,
                    name=name,
                    properties=config,
                    provisioning_state=ProvisioningState.SUCCEEDED
                )
            
            elif operation == "get":
                result = self.handler.get_resource(
                    name,
                    {"subscription_id": properties.get("_subscription_id")}
                )
                if result:
                    resource_id, config = result
                    return ResourceResponse(id=resource_id, ...)
                else:
                    return error_response("Not found")
            
            elif operation == "delete":
                deleted = self.handler.delete_resource(
                    name,
                    {"subscription_id": properties.get("_subscription_id")}
                )
                return ResourceResponse(
                    properties={"deleted": deleted},
                    provisioning_state=ProvisioningState.SUCCEEDED
                )
        
        except ValueError as e:
            # Duplicate detected
            return ResourceResponse(
                properties={"error": str(e)},
                provisioning_state=ProvisioningState.FAILED
            )
```

---

## Testing Your Handler

```python
def test_duplicate_detection():
    handler = MyHandler({})
    
    # Create first resource
    id1, _ = handler.create_resource(
        "test", {"config": 1}, "Type/test",
        {"subscription_id": "sub-1"}
    )
    
    # Try duplicate (should raise)
    with pytest.raises(ValueError):
        handler.create_resource(
            "test", {"config": 2}, "Type/test",
            {"subscription_id": "sub-1"}
        )
    
    # Same name, different scope (should work)
    id2, _ = handler.create_resource(
        "test", {"config": 3}, "Type/test",
        {"subscription_id": "sub-2"}
    )
    assert id1 != id2
```

---

## Where to Go for More

| Need | Reference |
|------|-----------|
| Full API | `docs/SCOPED_RESOURCE_HANDLER.md` |
| Examples | `examples/scoped_resource_examples.py` |
| Design | `ARCHITECTURE_SUMMARY.md` |
| Usage | Test files: `test_rg_*.py` |
| Source | `providers/scoped_resources.py` |

---

## Common Mistakes

❌ **Wrong:** Checking result for None on duplicate
```python
if handler.create_resource(...) is None:  # Won't work
```

✅ **Right:** Catch ValueError
```python
try:
    handler.create_resource(...)
except ValueError:
    # Handle duplicate
```

---

❌ **Wrong:** Forgetting to set UNIQUENESS_SCOPE
```python
class MyHandler(ScopedResourceHandler):
    RESOURCE_TYPE = "something"
    # Missing UNIQUENESS_SCOPE!
```

✅ **Right:** Set both
```python
class MyHandler(ScopedResourceHandler):
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION]
    RESOURCE_TYPE = "something"
```

---

❌ **Wrong:** Manually checking storage keys
```python
if f"{sub}/{name}" in self.storage:  # Don't do this
```

✅ **Right:** Use the handler
```python
existing = handler.check_duplicate(name, {"subscription_id": sub})
```

---

## Bottom Line

- **Don't** manually manage storage keys (handler does it)
- **Don't** manually check for duplicates (handler does it)
- **Don't** manually generate IDs (handler does it)
- **Do** inherit from ScopedResourceHandler
- **Do** set UNIQUENESS_SCOPE
- **Do** catch ValueError on create

**That's it!** Everything else is automatic.
