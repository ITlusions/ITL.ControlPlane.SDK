# Core - Intermediate Level

SDK fundamentals and resource handler patterns.

## Files
- **`quickstart.py`** (via [core/beginner/](../beginner/)) - SDK basics

## What You'll Learn

This section covers:
- Resource handlers and how they work
- The provider interface and registry
- Resource lifecycle (CRUD operations)
- Validation patterns (Pydantic)
- Scoping concepts (RG-scoped vs. Global)

## Handler Pattern

Handlers manage specific resource types:

```python
from abc import ABC, abstractmethod
from pydantic import BaseModel, validator

class ResourceHandler(ABC):
    """Base class for all handlers"""
    
    RESOURCE_TYPE: str = "Microsoft.Resources/default"
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION]
    
    @abstractmethod
    async def create(self, spec: dict) -> Resource:
        """Create a resource"""
        pass
    
    @abstractmethod
    async def delete(self, resource_id: str) -> None:
        """Delete a resource"""
        pass
    
    @abstractmethod
    async def get_status(self, resource_id: str) -> dict:
        """Get resource status"""
        pass
```

## Pydantic Validation

Handlers use Pydantic for input validation:

```python
from pydantic import BaseModel, Field, validator

class VMSchema(BaseModel):
    """VM resource specification"""
    name: str = Field(..., min_length=1, max_length=64, description="VM name")
    size: str = Field(..., description="VM size (e.g., Standard_D2s_v3)")
    os_type: str = Field(default="Windows", description="OS type")
    
    @validator('name')
    def name_alphanumeric(cls, v):
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Name must be alphanumeric')
        return v

# Use in handler
schema = VMSchema(name="web-vm", size="Standard_D2s_v3")
print(schema.dict())  # {"name": "web-vm", "size": "Standard_D2s_v3", "os_type": "Windows"}
```

## Resource Lifecycle

Resources go through states:

```
┌─────────────────────────────────────┐
│  Creation Workflow                  │
├─────────────────────────────────────┤
│                                     │
│  Validation  →  Provisioning  →  Succeeded
│                                     │
│                        ↓            │
│                   Failed (error)    │
│                                     │
└─────────────────────────────────────┘
```

## Scoping Concepts

Resources can be scoped at different levels:

### RG-Scoped (e.g., VMs, NICs)
```python
class ComputeHandler(ResourceHandler):
    UNIQUENESS_SCOPE = [
        UniquenessScope.SUBSCRIPTION,
        UniquenessScope.RESOURCE_GROUP
    ]
    # Can have same name in different RGs
```

**Use Case:**
- Typically: Compute, Network, Database resources
- Scope context needed: subscription_id + resource_group
- Example: `"web-vm"` unique per RG, not globally

### Global-Scoped (e.g., Storage)
```python
class StorageHandler(ResourceHandler):
    UNIQUENESS_SCOPE = [UniquenessScope.GLOBAL]
    # Cannot have same name anywhere
```

**Use Case:**
- Typically: Storage accounts (DNS-based names)
- Scope context needed: None
- Example: `"mystorage2025"` globally unique

## Resource Models

SDK provides typed models for all resources:

```python
from itl_control_plane_sdk import Resource, ResourceProperties

class VirtualMachine(Resource):
    """Represents an Azure VM"""
    resource_type = "Microsoft.Compute/virtualMachines"
    
    properties: VMProperties
    
    class VMProperties(ResourceProperties):
        size: str
        os_type: str
        admin_username: str

# Create instance
vm = VirtualMachine(
    id="/subscriptions/.../virtualMachines/web-vm",
    name="web-vm",
    properties=VMProperties(
        size="Standard_D2s_v3",
        os_type="Windows",
        admin_username="azureuser"
    )
)
```

## Provider Interface

Providers coordinate handlers:

```python
class ResourceProvider:
    """Coordinates handlers for resource management"""
    
    def __init__(self, name: str):
        self.name = name
        self._handlers = {}
    
    def register_handler(self, handler: ResourceHandler):
        """Register a handler"""
        self._handlers[handler.RESOURCE_TYPE] = handler
    
    async def create_resource(self, spec: dict, resource_type: str):
        """Create resource via appropriate handler"""
        handler = self._handlers[resource_type]
        return await handler.create(spec)

# Use
provider = ResourceProvider("my-provider")
provider.register_handler(ComputeHandler())
provider.register_handler(StorageHandler())

# Creates VM via ComputeHandler
vm = await provider.create_resource(
    {"name": "web-vm", "size": "Standard_D2s_v3"},
    "Microsoft.Compute/virtualMachines"
)
```

## Validation, Provisioning, Timestamps

The "Big 3" patterns every handler should implement:

1. **Validation** - Input validation via Pydantic
2. **Provisioning State** - Track resource state
3. **Timestamps** - Track creation/modification times

```python
class ResourceHandler(ABC):
    def create_resource(self, name: str, spec: dict, scope: dict = None):
        # 1. VALIDATION
        validated_spec = self.schema(**spec)  # Pydantic validates
        
        # 2. CREATE
        resource = self._create_impl(name, validated_spec)
        resource.provisioning_state = "Provisioning"
        
        # 3. TIMESTAMPS
        resource.created_at = datetime.utcnow()
        resource.modified_at = datetime.utcnow()
        
        return resource
```

## Prerequisites
- Python 3.9+
- Basic understanding of OOP and abstract classes
- Familiarity with Pydantic (validation library)

## Next Steps
→ **[Advanced](../advanced/)** - Learn custom handlers and extensions
