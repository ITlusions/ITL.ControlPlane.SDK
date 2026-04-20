# Common Patterns and Recipes

Quick reference for common provider implementation patterns.

---

## Pattern 1: Read-Only Provider

Providers that only expose existing resources without create/delete capabilities.

```python
class ReadOnlyProvider(ResourceProvider):
    def __init__(self):
        super().__init__("ITL.ReadOnly")
        self.resources = {}  # Populated from external system
    
    async def get_resource(self, request: ResourceRequest) -> ResourceResponse:
        """Get a resource from external system"""
        # Query external API/database
        resource = await self._fetch_from_external(
            request.subscription_id,
            request.resource_group,
            request.resource_name
        )
        
        return ResourceResponse(
            id=f"{resource['id']}",
            name=resource['name'],
            provisioning_state=ProvisioningState.SUCCEEDED,
            properties=resource['properties']
        )
    
    async def list_resources(self, request: ResourceRequest) -> List[ResourceResponse]:
        """List all resources"""
        resources = await self._fetch_all()
        return [ResourceResponse(**r) for r in resources]
    
    async def create_or_update_resource(self, request: ResourceRequest):
        """Not supported"""
        raise NotImplementedError("Read-only provider")
    
    async def delete_resource(self, request: ResourceRequest):
        """Not supported"""
        raise NotImplementedError("Read-only provider")
```

---

## Pattern 2: Delegating Provider

Forward requests to another provider or external service.

```python
class DelegatingProvider(ResourceProvider):
    def __init__(self, backend_url: str):
        super().__init__("ITL.Delegating")
        self.backend_url = backend_url
        self.http_client = httpx.AsyncClient()
    
    async def create_or_update_resource(self, request: ResourceRequest):
        """Delegate to backend"""
        response = await self.http_client.put(
            f"{self.backend_url}/resources/{request.resource_name}",
            json=request.dict()
        )
        
        if response.status_code != 200:
            raise Exception(f"Backend error: {response.text}")
        
        return ResourceResponse(**response.json())
    
    async def get_resource(self, request: ResourceRequest):
        response = await self.http_client.get(
            f"{self.backend_url}/resources/{request.resource_name}"
        )
        
        if response.status_code == 404:
            raise ResourceNotFoundError(request.resource_name)
        
        return ResourceResponse(**response.json())
```

---

## Pattern 3: Caching Provider

Cache responses for frequently accessed resources.

```python
from functools import lru_cache
from datetime import datetime, timedelta
import asyncio

class CachingProvider(ResourceProvider):
    def __init__(self, cache_ttl_seconds: int = 300):
        super().__init__("ITL.Caching")
        self.cache = {}
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
    
    async def get_resource(self, request: ResourceRequest):
        cache_key = f"{request.subscription_id}:{request.resource_name}"
        
        # Check cache
        if cache_key in self.cache:
            cached_item = self.cache[cache_key]
            if datetime.utcnow() - cached_item['created'] < self.cache_ttl:
                return cached_item['value']
            else:
                # Expired
                del self.cache[cache_key]
        
        # Fetch and cache
        resource = await self._fetch_resource(request)
        
        self.cache[cache_key] = {
            'value': resource,
            'created': datetime.utcnow()
        }
        
        return resource
    
    def invalidate_cache(self, subscription_id: str, resource_name: str):
        cache_key = f"{subscription_id}:{resource_name}"
        self.cache.pop(cache_key, None)
```

---

## Pattern 4: Validating Wrapper Provider

Add validation on top of existing provider.

```python
from pydantic import BaseModel, validator

class ValidatedProperties(BaseModel):
    name: str
    region: str
    
    @validator('region')
    def region_must_be_valid(cls, v):
        valid_regions = ["us-east-1", "us-west-2", "eu-west-1"]
        if v not in valid_regions:
            raise ValueError(f"Invalid region: {v}")
        return v

class ValidatingProvider(ResourceProvider):
    def __init__(self, wrapped_provider: ResourceProvider):
        super().__init__("ITL.Validating")
        self.wrapped = wrapped_provider
    
    async def create_or_update_resource(self, request: ResourceRequest):
        # Validate before delegating
        try:
            ValidatedProperties(**request.properties)
        except ValueError as e:
            raise BadRequest(str(e))
        
        # Delegate to wrapped provider
        return await self.wrapped.create_or_update_resource(request)
        
    # ... delegate other methods ...
```

---

## Pattern 5: Rate-Limited Provider

Limit API calls to prevent overload.

```python
from asyncio import Semaphore
import time

class RateLimitedProvider(ResourceProvider):
    def __init__(self, rate_limit: int = 100):
        super().__init__("ITL.RateLimited")
        self.limiter = Semaphore(rate_limit)
        self.request_times = []
    
    async def _acquire_rate_limit(self):
        """Acquire permission to make a request"""
        async with self.limiter:
            # Token bucket algorithm
            now = time.time()
            self.request_times = [t for t in self.request_times if t > now - 60]
            
            if len(self.request_times) >= 100:
                wait_time = 60 - (now - self.request_times[0])
                await asyncio.sleep(wait_time)
            
            self.request_times.append(now)
    
    async def create_or_update_resource(self, request: ResourceRequest):
        await self._acquire_rate_limit()
        
        # Now safe to proceed
        return await self._do_create(request)
```

---

## Pattern 6: Audit Logging Wrapper

Audit all operations.

```python
class AuditingProvider(ResourceProvider):
    def __init__(self, wrapped_provider: ResourceProvider, audit_log_path: str):
        super().__init__("ITL.Auditing")
        self.wrapped = wrapped_provider
        self.audit_log = open(audit_log_path, 'a')
    
    async def _audit(self, operation: str, request: ResourceRequest, result: str):
        """Log operation to audit log"""
        self.audit_log.write(
            f"{datetime.utcnow().isoformat()} | {operation} | "
            f"{request.subscription_id} | {request.resource_name} | {result}\n"
        )
        self.audit_log.flush()
    
    async def create_or_update_resource(self, request: ResourceRequest):
        try:
            result = await self.wrapped.create_or_update_resource(request)
            await self._audit("CREATE/UPDATE", request, "SUCCESS")
            return result
        except Exception as e:
            await self._audit("CREATE/UPDATE", request, f"FAILED: {e}")
            raise
    
    # ... audit other methods ...
```

---

## Pattern 7: Tenant-Aware Provider

Isolate resources by tenant.

```python
class TenantAwareProvider(ResourceProvider):
    def __init__(self):
        super().__init__("ITL.TenantAware")
        self.tenant_storage = {}  # tenant_id -> resources
    
    def _get_tenant_id(self, subscription_id: str) -> str:
        """Map subscription to tenant"""
        # In reality, query a tenancy service
        return f"tenant-{subscription_id.split('-')[0]}"
    
    async def create_or_update_resource(self, request: ResourceRequest):
        tenant_id = self._get_tenant_id(request.subscription_id)
        
        # Ensure tenant storage exists
        if tenant_id not in self.tenant_storage:
            self.tenant_storage[tenant_id] = {}
        
        # Store in tenant-specific namespace
        storage = self.tenant_storage[tenant_id]
        
        # Create with tenant scoping
        resource_id = f"/subscriptions/{request.subscription_id}/providers/..."
        storage[resource_id] = request.properties
        
        return ResourceResponse(id=resource_id, name=request.resource_name)
    
    async def get_resource(self, request: ResourceRequest):
        tenant_id = self._get_tenant_id(request.subscription_id)
        
        if tenant_id not in self.tenant_storage:
            raise ResourceNotFoundError("Tenant not found")
        
        storage = self.tenant_storage[tenant_id]
        # ... access only tenant's resources ...
```

---

## Pattern 8: Eventual Consistency Provider

Asynchronously sync external state.

```python
import asyncio

class EventualConsistencyProvider(ResourceProvider):
    def __init__(self):
        super().__init__("ITL.Eventually")
        self.resources = {}
        self.sync_task = None
    
    async def start(self):
        """Start background sync"""
        self.sync_task = asyncio.create_task(self._sync_loop())
    
    async def _sync_loop(self):
        """Periodically sync with external system"""
        while True:
            try:
                await self._sync_with_external()
                await asyncio.sleep(30)  # Sync every 30 seconds
            except Exception as e:
                logger.error(f"Sync error: {e}")
    
    async def _sync_with_external(self):
        """Fetch latest state from external system"""
        external_resources = await self._fetch_external()
        
        for ext_resource in external_resources:
            self.resources[ext_resource['id']] = ext_resource
    
    async def get_resource(self, request: ResourceRequest):
        # Return potentially stale data
        resource = self.resources.get(request.resource_name)
        
        if not resource:
            raise ResourceNotFoundError(request.resource_name)
        
        return ResourceResponse(**resource)
```

---

## Pattern 9: Bulkhead Pattern

Isolate failure domains.

```python
from concurrent.futures import ThreadPoolExecutor

class BulkheadProvider(ResourceProvider):
    def __init__(self, max_concurrent_ops: int = 10):
        super().__init__("ITL.Bulkhead")
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_ops)
    
    async def create_or_update_resource(self, request: ResourceRequest):
        loop = asyncio.get_event_loop()
        
        # Run in isolated executor to prevent resource exhaustion
        return await loop.run_in_executor(
            self.executor,
            self._sync_create,
            request
        )
    
    def _sync_create(self, request):
        # Long-running operation in thread pool
        # If this fails, other operations continue
        return self._do_create(request)
```

---

## Pattern 10: Circuit Breaker

Fail fast when backing service is down.

```python
from enum import Enum
import time

class CircuitState(Enum):
    CLOSED = "closed"      # Working normally
    OPEN = "open"          # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreakerProvider(ResourceProvider):
    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60):
        super().__init__("ITL.CircuitBreaker")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.last_failure_time = None
    
    async def create_or_update_resource(self, request: ResourceRequest):
        if self.state == CircuitState.OPEN:
            # Check if we should try to recover
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpenException("Service unavailable")
        
        try:
            result = await self._do_create(request)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
```

---

## Quick Reference

| Pattern | Use When | Benefit |
|---------|----------|---------|
| Read-Only | Exposing external resources | Minimal complexity |
| Delegating | Proxying to another service | Loose coupling |
| Caching | Expensive queries | Reduced latency |
| Validating | Strict schema enforcement | Error prevention |
| Rate-Limited | Preventing overload | Stability |
| Auditing | Compliance requirements | Traceability |
| Tenant-Aware | Multi-tenant systems | Data isolation |
| Eventual Consistency | Background sync | High availability |
| Bulkhead | Preventing cascading failures | Resilience |
| Circuit Breaker | Failing gracefully | Fail-fast behavior |

---

## Combining Patterns

Most real-world providers combine multiple patterns:

```python
class ProductionProvider(
    AuditingProvider,
    RateLimitedProvider,
    CircuitBreakerProvider,
    ValidatingProvider,
    CachingProvider,
):
    pass
```

---

## Related Documentation

- [10-ADVANCED_PATTERNS.md](10-ADVANCED_PATTERNS.md) - Complex patterns
- [15-EXAMPLES](../15-EXAMPLES/) - Complete working examples
- [12-TESTING_GUIDE.md](12-TESTING_GUIDE.md) - Testing patterns

---

Choose the right patterns for your use case and combine them for production-grade providers.
