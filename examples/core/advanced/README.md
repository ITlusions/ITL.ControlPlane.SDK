# Core - Advanced Level

Custom handlers and advanced SDK patterns.

## Files
- (Advanced patterns in repository)

## Custom Handler Development

Create custom handlers for domain-specific resources:

```python
from itl_control_plane_sdk import ResourceHandler, Resource, UniquenessScope
from pydantic import BaseModel, validator

# Step 1: Define schema
class CustomResourceSchema(BaseModel):
    """Custom resource specification"""
    resource_name: str
    config: dict
    
    @validator('resource_name')
    def validate_name(cls, v):
        if len(v) < 3:
            raise ValueError('Name must be at least 3 characters')
        return v

# Step 2: Implement handler
class CustomResourceHandler(ResourceHandler):
    """Handler for custom resources"""
    
    RESOURCE_TYPE = "Custom.Org/customResources"
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION]
    
    def __init__(self):
        self.schema = CustomResourceSchema
        self._resources = {}
    
    async def create(self, spec: dict, scope: dict) -> Resource:
        """Create custom resource"""
        # Validate
        validated = self.schema(**spec)
        
        # Persist
        resource_id = self._generate_id(scope, validated.resource_name)
        self._resources[resource_id] = validated
        
        # Return as Resource
        return Resource(
            id=resource_id,
            name=validated.resource_name,
            resource_type=self.RESOURCE_TYPE,
            properties=validated.dict()
        )
    
    async def delete(self, resource_id: str) -> None:
        """Delete custom resource"""
        if resource_id in self._resources:
            del self._resources[resource_id]

# Step 3: Register handler
from itl_control_plane_sdk import ResourceProvider

provider = ResourceProvider("my-org")
provider.register_handler(CustomResourceHandler())

# Step 4: Use handler
resource = await provider.create_resource(
    {
        "resource_name": "my-custom-resource",
        "config": {"setting1": "value1"}
    },
    "Custom.Org/customResources",
    {"subscription_id": "sub-123"}
)
```

## Advanced Scoping Patterns

### Multi-Level Scoping

Resources can be scoped at multiple levels:

```python
class AdvancedHandler(ResourceHandler):
    # Unique at multiple levels
    UNIQUENESS_SCOPE = [
        UniquenessScope.SUBSCRIPTION,
        UniquenessScope.RESOURCE_GROUP,
        UniquenessScope.PARENT_RESOURCE
    ]
```

Example: Databases under servers

```python
# Database scoped to: subscription + server
database1 = db_handler.create_resource(
    "mydb",
    {...},
    {...},
    {
        "subscription_id": "sub",
        "parent_resource_id": "/subscriptions/.../servers/server1"
    }
)

# Same database name OK under different server
database2 = db_handler.create_resource(
    "mydb",  # Same name!
    {...},
    {...},
    {
        "subscription_id": "sub",
        "parent_resource_id": "/subscriptions/.../servers/server2"
    }
)
```

## Asynchronous Operations

Handlers support async operations:

```python
from typing import AsyncIterator

class AsyncResourceHandler(ResourceHandler):
    async def create(self, spec: dict, scope: dict) -> Resource:
        """Async creation"""
        # Validate
        validated = self.schema(**spec)
        
        # Async operations
        async with self.client_session() as session:
            response = await session.post(
                "/api/resources",
                json=validated.dict()
            )
        
        return Resource(**response.json())
    
    async def monitor_creation(self, resource_id: str) -> AsyncIterator[dict]:
        """Monitor resource creation status"""
        while True:
            status = await self.get_status(resource_id)
            
            yield {
                "state": status["provisioning_state"],
                "timestamp": datetime.utcnow(),
                "progress": status.get("progress", 0)
            }
            
            if status["provisioning_state"] in ["Succeeded", "Failed"]:
                break
            
            await asyncio.sleep(5)

# Usage
handler = AsyncResourceHandler()
resource = await handler.create({...}, {...})

async for status in handler.monitor_creation(resource.id):
    print(f"Progress: {status['progress']}%")
```

## Validation Hooks

Advanced validation patterns:

```python
from pydantic import root_validator, field_validator

class AdvancedSchema(BaseModel):
    name: str
    tier: str  # Basic, Standard, Premium
    redundancy: str  # Local, Geo
    
    @field_validator('name')
    @classmethod
    def validate_name_format(cls, v):
        # Custom format validation
        if not v.replace('-', '').isalnum():
            raise ValueError('Invalid name format')
        return v.lower()
    
    @root_validator
    def validate_tier_redundancy(cls, values):
        # Cross-field validation
        tier = values.get('tier')
        redundancy = values.get('redundancy')
        
        if tier == 'Basic' and redundancy == 'Geo':
            raise ValueError('Basic tier does not support Geo redundancy')
        
        return values

# Results in validation at construction
schema = AdvancedSchema(
    name="MyResource",
    tier="Basic",
    redundancy="Geo"  # ValueError!
)
```

## Handler Composition

Combine multiple handlers:

```python
class CompositeHandler(ResourceHandler):
    """Composite handler that uses multiple sub-handlers"""
    
    def __init__(self):
        self.compute_handler = ComputeHandler()
        self.storage_handler = StorageHandler()
        self.network_handler = NetworkHandler()
    
    async def create_complete_stack(self, spec: dict, scope: dict):
        """Create related resources together"""
        
        # Create storage
        storage = await self.storage_handler.create(
            spec["storage"], {}
        )
        
        # Create network
        network = await self.network_handler.create(
            spec["network"], scope
        )
        
        # Create compute (depends on network)
        spec["compute"]["network_id"] = network.id
        compute = await self.compute_handler.create(
            spec["compute"], scope
        )
        
        return {
            "storage": storage,
            "network": network,
            "compute": compute
        }
```

## Error Handling

Production-grade error handling:

```python
from enum import Enum

class ErrorCode(Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONFLICT_ERROR = "CONFLICT_ERROR"
    NOT_FOUND_ERROR = "NOT_FOUND_ERROR"
    SERVICE_ERROR = "SERVICE_ERROR"

class ResourceError(Exception):
    def __init__(self, code: ErrorCode, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

class RobustHandler(ResourceHandler):
    async def create(self, spec: dict, scope: dict) -> Resource:
        try:
            # Validate
            validated = self.schema(**spec)
        except ValueError as e:
            raise ResourceError(
                ErrorCode.VALIDATION_ERROR,
                f"Invalid specification: {str(e)}",
                {"field_errors": e.errors()}
            )
        
        try:
            # Create resource
            resource = await self._create_impl(validated)
        except DuplicateError:
            raise ResourceError(
                ErrorCode.CONFLICT_ERROR,
                f"Resource '{validated.name}' already exists",
                {"resource_name": validated.name}
            )
        except ServiceUnavailable:
            raise ResourceError(
                ErrorCode.SERVICE_ERROR,
                "Service temporarily unavailable",
                {"retry_after": 60}
            )
        
        return resource
```

## Caching and Performance

Optimize handler performance:

```python
from functools import lru_cache
from datetime import timedelta

class CachedHandler(ResourceHandler):
    def __init__(self):
        self._cache = {}
        self._cache_ttl = timedelta(minutes=5)
    
    @lru_cache(maxsize=1024)
    async def get(self, resource_id: str) -> Resource:
        """Get with caching"""
        if resource_id in self._cache:
            cached, timestamp = self._cache[resource_id]
            if datetime.utcnow() - timestamp < self._cache_ttl:
                return cached
        
        # Fetch from backend
        resource = await self._fetch(resource_id)
        self._cache[resource_id] = (resource, datetime.utcnow())
        return resource
    
    def invalidate_cache(self, resource_id: str = None):
        """Invalidate cache entries"""
        if resource_id:
            self._cache.pop(resource_id, None)
        else:
            self._cache.clear()
```

## Prerequisites
- Complete [intermediate/](../intermediate/) level
- Advanced Python knowledge (async/await, decorators, metaclasses)
- Understanding of handler patterns and composition

## Next Steps
→ **[Deployment](../../deployment/advanced/)** - Deploy custom handlers
