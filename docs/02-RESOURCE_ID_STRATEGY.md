# Resource ID Strategy: Path-Based + GUID Hybrid Approach

## Overview

The ITL ControlPlane SDK now supports a **hybrid resource identification strategy** that provides both human-readable path-based IDs (Azure ARM-style) and globally unique GUIDs for guaranteed uniqueness.

## Current Implementation

### ✅ **What You Get Out of the Box:**

1. **Automatic GUID Generation**: Every `ResourceResponse` and `ResourceMetadata` now includes an auto-generated `resource_guid` field
2. **Backward Compatibility**: Existing path-based IDs continue to work unchanged
3. **Enhanced Utilities**: New helper functions for ID generation and parsing

### 🔄 **ID Strategies Available:**

#### **Strategy 1: Path-Based IDs (Current/Default)**
```python
# Human-readable, hierarchical structure
"/subscriptions/sub-123/resourceGroups/rg-test/providers/Microsoft.Compute/virtualMachines/vm-1"
```

**Use when:**
- Human readability is important
- Following Azure ARM conventions
- Debugging and logging
- Backward compatibility needed

#### **Strategy 2: Path + GUID Suffix**
```python
# Path-based with unique suffix
"/subscriptions/sub-123/resourceGroups/rg-test/providers/Microsoft.Compute/virtualMachines/vm-1?guid=550e8400-e29b-41d4-a716-446655440000"
```

**Use when:**
- Need guaranteed uniqueness
- Allowing resource name reuse
- Distributed systems with potential conflicts

#### **Strategy 3: Dual Identity (Recommended)**
```python
# Both path and separate GUID maintained
ResourceResponse(
    id="/subscriptions/.../vm-1",           # Path-based for readability
    resource_guid="550e8400-...",            # GUID for uniqueness
    # ... other fields
)
```

**Use when:**
- Best of both worlds needed
- Building new systems
- Maximum flexibility required

## Implementation Examples

### **For Resource Providers:**

```python
from itl_controlplane_sdk import generate_resource_id, ResourceResponse, ProvisioningState

class MyResourceProvider(ResourceProvider):
    async def create_or_update_resource(self, request: ResourceRequest) -> ResourceResponse:
        # Generate hierarchical ID (current approach)
        resource_id = generate_resource_id(
            subscription_id=request.subscription_id,
            resource_group=request.resource_group,
            provider_namespace=request.provider_namespace,
            resource_type=request.resource_type,
            resource_name=request.resource_name
        )
        
        # Create response - GUID is auto-generated
        response = ResourceResponse(
            id=resource_id,
            name=request.resource_name,
            type=f"{request.provider_namespace}/{request.resource_type}",
            location=request.location,
            properties=request.body.get("properties", {}),
            provisioning_state=ProvisioningState.SUCCEEDED
            # resource_guid is automatically generated!
        )
        
        # Store by both ID and GUID for flexible lookup
        self._resources[resource_id] = response
        self._resources_by_guid[response.resource_guid] = response
        
        return response
```

### **For Resource Consumers:**

```python
from itl_controlplane_sdk import parse_resource_id

# Parse any resource ID format
resource_info = parse_resource_id(
    "/subscriptions/sub-123/resourceGroups/rg-test/providers/Microsoft.Compute/virtualMachines/vm-1"
)

print(f"Subscription: {resource_info['subscription_id']}")
print(f"Resource Group: {resource_info['resource_group']}")
print(f"Provider: {resource_info['provider_namespace']}")
print(f"Type: {resource_info['resource_type']}")
print(f"Name: {resource_info['resource_name']}")
```

### **For Advanced Scenarios:**

```python
from itl_controlplane_sdk import ResourceIdentity

# Create comprehensive identity
identity = ResourceIdentity.create(
    subscription_id="sub-123",
    resource_group="rg-test",
    provider_namespace="Microsoft.Compute",
    resource_type="virtualMachines",
    resource_name="vm-1"
)

print(f"Human-readable ID: {identity.resource_id}")
print(f"Unique GUID: {identity.resource_guid}")

# Use for external references, indexing, etc.
external_system.register_resource(
    path_id=identity.resource_id,      # For humans/debugging
    unique_id=identity.resource_guid   # For systems/indexing
)
```

## Migration Guidelines

### **Immediate Actions (No Breaking Changes):**

1. **Continue using existing code** - everything still works
2. **Start using `resource_guid`** in new integrations:
   ```python
   # Old way (still works)
   resource_lookup[response.id] = response
   
   # Enhanced way (recommended for new code)
   resource_lookup[response.id] = response
   guid_lookup[response.resource_guid] = response
   ```

### **Recommended Enhancements:**

1. **Update resource storage** to index by both ID and GUID
2. **Use GUIDs for external integrations** (databases, message queues, etc.)
3. **Keep path-based IDs for logging and user interfaces**
4. **Add GUID-based lookup methods** to your providers

### **Long-term Considerations:**

1. **Database schemas**: Add `resource_guid` columns for faster lookups
2. **API responses**: Include both `id` and `resource_guid` in responses
3. **Monitoring/metrics**: Use GUIDs for correlation across systems
4. **Caching strategies**: Consider GUID-based cache keys for better distribution

## Best Practices

### **✅ Do:**
- Use path-based IDs for logging and user-facing operations
- Use GUIDs for internal system operations and external integrations
- Store and index both ID types for maximum flexibility
- Include both in API responses for future-proofing

### **❌ Don't:**
- Rely solely on path-based IDs for uniqueness in distributed systems
- Expose GUIDs to end users unless necessary
- Break existing path-based ID assumptions without migration plan
- Store only one ID type if you can avoid it

## Performance Considerations

- **GUID generation**: Minimal overhead (microseconds)
- **Storage**: Additional 36 characters per resource
- **Indexing**: GUIDs provide better distribution for database indexes
- **Lookup**: Both ID types should be indexed for optimal performance

## Questions & Troubleshooting

**Q: Do I need to change my existing code?**
A: No, existing path-based IDs continue to work unchanged.

**Q: When should I use GUIDs vs path-based IDs?**
A: Use path-based for human interaction, GUIDs for system-to-system communication.

**Q: Are GUIDs guaranteed unique across all providers?**
A: Yes, UUID4 provides global uniqueness across all systems and time.

**Q: Can I specify my own GUID?**
A: Yes, you can provide a custom `resource_guid` when creating responses.

**Q: How do I migrate existing resources to include GUIDs?**
A: The SDK auto-generates GUIDs for any response that doesn't have one, ensuring seamless migration.