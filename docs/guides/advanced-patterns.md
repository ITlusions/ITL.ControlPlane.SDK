# Advanced Patterns: Complex SDK Scenarios

This guide covers advanced patterns for building sophisticated resource providers with the ITL ControlPlane SDK.

---

## Pattern 1: Scope-Aware Resources with Custom Handlers

### The Problem
Resource uniqueness varies by type. Resource groups are unique per subscription, but VMs are unique per resource group.

### The Solution
Use `ScopedResourceHandler` with custom scope configuration:

```python
from itl_controlplane_sdk.providers import ScopedResourceHandler, UniquenessScope
from itl_controlplane_sdk import ResourceProvider, ResourceRequest, ResourceResponse, ProvisioningState

# Define handler with subscription + RG scope
class VirtualMachineHandler(ScopedResourceHandler):
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION, UniquenessScope.RESOURCE_GROUP]
    RESOURCE_TYPE = "virtualmachines"

class ComputeProvider(ResourceProvider):
    def __init__(self):
        super().__init__("ITL.Compute")
        self.virtual_machines = {}
        self.vm_handler = VirtualMachineHandler(self.virtual_machines)
    
    async def create_or_update_resource(self, request: ResourceRequest) -> ResourceResponse:
        try:
            vm_id, vm_data = self.vm_handler.create_resource(
                request.resource_name,
                request.properties,
                f"{self.provider_namespace}/virtualmachines",
                {
                    "subscription_id": request.subscription_id,
                    "resource_group": request.resource_group
                }
            )
            return ResourceResponse(
                id=vm_id,
                name=request.resource_name,
                provisioning_state=ProvisioningState.SUCCEEDED,
                properties=vm_data
            )
        except ValueError as e:
            # Duplicate detected automatically
            return ResourceResponse(
                provisioning_state=ProvisioningState.FAILED,
                properties={"error": str(e)}
            )
```

### Key Benefits
- Automatic duplicate detection
- Correct storage key formatting
- Zero manual scope management
- Works for any resource type

---

## Pattern 2: The Big 3 Handler Mixins

### Combining Timestamp, State, and Validation

```python
from itl_controlplane_sdk.providers import ScopedResourceHandler, UniquenessScope
from itl_controlplane_sdk import TimestampedResourceHandler, ProvisioningStateHandler, ValidatedResourceHandler

# Create a handler with all three features
class AdvancedResourceHandler(
    TimestampedResourceHandler,
    ProvisioningStateHandler,
    ValidatedResourceHandler,
    ScopedResourceHandler
):
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION]
    RESOURCE_TYPE = "advancedresources"
    
    def __init__(self, storage_dict):
        super().__init__(storage_dict)
        # Now you have:
        # - Automatic timestamps (createdTime, modifiedTime, createdBy, modifiedBy)
        # - Provisioning state machine (Accepted -> Provisioning -> Succeeded/Failed)
        # - Schema validation
        # - Scope-aware uniqueness
```

### Features Combined
- **TimestampedResourceHandler**: Automatic audit trail
- **ProvisioningStateHandler**: State machine management
- **ValidatedResourceHandler**: Schema validation
- **ScopedResourceHandler**: Duplicate prevention

---

## Pattern 3: Async Long-Running Operations

### Handling Operations That Take Time

```python
import asyncio
from itl_controlplane_sdk import ResourceProvider, ProvisioningState, ResourceResponse

class LongRunningProvider(ResourceProvider):
    def __init__(self):
        super().__init__("ITL.LongRunning")
        self.operations = {}
    
    async def create_or_update_resource(self, request):
        # Start operation in Accepted state
        operation_id = str(uuid.uuid4())
        
        response = ResourceResponse(
            id=f"/subscriptions/{request.subscription_id}/providers/{self.provider_namespace}/operations/{operation_id}",
            name=request.resource_name,
            provisioning_state=ProvisioningState.ACCEPTED
        )
        
        # Start async background task
        asyncio.create_task(self._async_provision(operation_id, request))
        
        return response
    
    async def _async_provision(self, operation_id, request):
        """Long-running operation in background"""
        try:
            # Transition to Provisioning
            self.operations[operation_id] = {
                "state": ProvisioningState.PROVISIONING,
                "request": request
            }
            
            # Do long-running work
            await asyncio.sleep(5)  # Simulate work
            
            # Complete successfully
            self.operations[operation_id]["state"] = ProvisioningState.SUCCEEDED
            
        except Exception as e:
            # Mark as failed
            self.operations[operation_id] = {
                "state": ProvisioningState.FAILED,
                "error": str(e)
            }
    
    async def get_resource(self, request):
        operation_id = request.resource_name
        
        if operation_id not in self.operations:
            raise Exception("Operation not found")
        
        op = self.operations[operation_id]
        
        return ResourceResponse(
            id=f"...",
            name=request.resource_name,
            provisioning_state=op["state"]
        )
```

---

## Pattern 4: Multi-Provider Composition

### Coordinating Multiple Providers

```python
from itl_controlplane_sdk import ResourceProviderRegistry, ResourceRequest

class CompositeProvider(ResourceProvider):
    def __init__(self, registry: ResourceProviderRegistry):
        super().__init__("ITL.Composite")
        self.registry = registry
    
    async def create_or_update_resource(self, request: ResourceRequest):
        # Delegate to specialized providers based on resource type
        if "compute" in request.resource_type:
            return await self.registry.create_or_update_resource(
                "ITL.Compute", request.resource_type, request
            )
        elif "storage" in request.resource_type:
            return await self.registry.create_or_update_resource(
                "ITL.Storage", request.resource_type, request
            )
        else:
            return await self.registry.create_or_update_resource(
                "ITL.Core", request.resource_type, request
            )
```

---

## Pattern 5: Webhooks and Event Publishing

### Reacting to Resource Changes

```python
from typing import Callable, List
from itl_controlplane_sdk import ResourceProvider, ResourceResponse

class EventDrivenProvider(ResourceProvider):
    def __init__(self):
        super().__init__("ITL.EventDriven")
        self.webhooks: List[Callable] = []
        self.resources = {}
    
    def register_webhook(self, callback: Callable):
        """Register a callback for resource events"""
        self.webhooks.append(callback)
    
    async def _publish_event(self, event_type: str, resource: ResourceResponse):
        """Publish event to all registered webhooks"""
        for webhook in self.webhooks:
            try:
                # Fire and forget, or await?
                if asyncio.iscoroutinefunction(webhook):
                    await webhook(event_type, resource)
                else:
                    webhook(event_type, resource)
            except Exception as e:
                # Log error but continue
                print(f"Webhook error: {e}")
    
    async def create_or_update_resource(self, request):
        # ... create resource ...
        response = ResourceResponse(...)
        
        # Publish event
        await self._publish_event("resource.created", response)
        
        return response

# Usage
provider = EventDrivenProvider()

# Subscribe to events
async def on_resource_created(event_type, resource):
    print(f"Event: {event_type} - {resource.name}")

provider.register_webhook(on_resource_created)
```

---

## Pattern 6: Validation and Sanitization

### Safe Resource Creation

```python
from pydantic import BaseModel, Field, validator

class ResourceProperties(BaseModel):
    name: str = Field(..., min_length=3, max_length=63)
    location: str = Field(..., description="Azure region")
    tags: dict = Field(default_factory=dict)
    
    @validator('name')
    def name_must_be_valid(cls, v):
        # Only alphanumeric and hyphens
        if not all(c.isalnum() or c == '-' for c in v):
            raise ValueError('Name must contain only alphanumeric and hyphens')
        return v
    
    @validator('location')
    def location_must_be_valid(cls, v):
        valid_locations = [
            "eastus", "westus", "northeurope", "westeurope",
            "southeastasia", "eastasia", # ... more regions
        ]
        if v not in valid_locations:
            raise ValueError(f'Location must be one of {valid_locations}')
        return v

class SafeProvider(ResourceProvider):
    async def create_or_update_resource(self, request):
        try:
            # Validate using Pydantic
            props = ResourceProperties(**request.properties)
            
            # Now props are guaranteed to be valid
            resource_id = f".../resources/{props.name}"
            
            return ResourceResponse(
                id=resource_id,
                name=props.name,
                properties=props.dict()
            )
        
        except ValueError as e:
            # Return validation error
            return ResourceResponse(
                provisioning_state=ProvisioningState.FAILED,
                properties={"error": str(e)}
            )
```

---

## Related Documentation

- [03-CORE_CONCEPTS.md](../architecture/core-concepts.md) - Scoped handlers deep dive
- [06-HANDLER_MIXINS.md](../features/handler-mixins.md) - Big 3 handler details
- [09-ASYNC_PATTERNS.md](../features/async-patterns.md) - Async patterns and Service Bus
- [12-TESTING_GUIDE.md](../10-GUIDES/12-TESTING_GUIDE.md) - Testing these patterns
- [15-EXAMPLES](../../examples/) - Complete working examples

---

## Best Practices

 **Always use scope-aware handlers** - Prevents subtle scoping bugs  
 **Combine Big 3 mixins** - Get timestamps, state, and validation
 **Validate early** - Use Pydantic for schema validation  
 **Handle errors explicitly** - Don't silently ignore failures  
 **Use async properly** - Don't block on long operations  
 **Test edge cases** - Duplicates, validation failures, state transitions

---

These advanced patterns enable you to build production-grade resource providers that are maintainable, testable, and following SDK best practices.
