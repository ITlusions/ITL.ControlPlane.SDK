# Error Handling Reference

Complete guide to error handling in resource providers.

---

## SDK Error Types

### ResourceNotFoundError

Used when a resource doesn't exist.

```python
from itl_controlplane_sdk.exceptions import ResourceNotFoundError

class MyProvider(ResourceProvider):
    async def get_resource(self, request: ResourceRequest):
        if request.resource_name not in self.storage:
            raise ResourceNotFoundError(
                f"Resource '{request.resource_name}' not found"
            )
```

**Returns:** 404 Not Found

---

### ResourceAlreadyExistsError

Used when creating a duplicate resource.

```python
from itl_controlplane_sdk.exceptions import ResourceAlreadyExistsError

class MyProvider(ResourceProvider):
    async def create_or_update_resource(self, request: ResourceRequest):
        if self._exists(request.resource_name):
            raise ResourceAlreadyExistsError(
                f"Resource '{request.resource_name}' already exists"
            )
```

**Returns:** 409 Conflict

---

### ValidationError

Used for invalid input data.

```python
from pydantic import ValidationError

@app.post("/create")
async def create(data: dict):
    try:
        properties = MyProperties(**data)
    except ValidationError as e:
        raise BadRequest(f"Validation failed: {e.errors()}")
```

**Returns:** 400 Bad Request

---

### InvalidOperationError

Used for operations that can't be performed in current state.

```python
from itl_controlplane_sdk.exceptions import InvalidOperationError

class MyProvider(ResourceProvider):
    async def delete_resource(self, request: ResourceRequest):
        resource = await self.get_resource(request)
        
        if resource.provisioning_state != ProvisioningState.SUCCEEDED:
            raise InvalidOperationError(
                f"Cannot delete resource in {resource.provisioning_state} state"
            )
```

**Returns:** 400 Bad Request

---

### ProviderError

Generic provider error.

```python
from itl_controlplane_sdk.exceptions import ProviderError

class MyProvider(ResourceProvider):
    async def create_or_update_resource(self, request: ResourceRequest):
        try:
            # ... do work ...
        except Exception as e:
            raise ProviderError(f"Failed to create resource: {e}")
```

**Returns:** 500 Internal Server Error

---

## Custom Error Responses

### Format Error Responses Correctly

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list = []

class ErrorResponse(BaseModel):
    error: ErrorDetail

@app.exception_handler(Exception)
async def custom_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error=ErrorDetail(
                code="InternalError",
                message=str(exc),
                details=[]
            )
        ).dict()
    )
```

---

## Error Handling Patterns

### The Try-Catch-Log-Return Pattern

```python
from itl_controlplane_sdk.exceptions import ResourceNotFoundError
import logging

logger = logging.getLogger(__name__)

async def get_resource(self, request: ResourceRequest):
    try:
        resource = await self._fetch(request.resource_name)
        return ResourceResponse(...)
    
    except KeyError:
        # Log error
        logger.warning(
            "Resource not found",
            extra={
                "resource_name": request.resource_name,
                "subscription_id": request.subscription_id
            }
        )
        # Raise SDK exception
        raise ResourceNotFoundError(request.resource_name)
    
    except Exception as e:
        # Log unexpected error
        logger.error(
            "Unexpected error fetching resource",
            extra={
                "resource_name": request.resource_name,
                "error": str(e)
            },
            exc_info=True  # Include traceback
        )
        # Return generic error
        raise ProviderError(str(e))
```

### The Validation-First Pattern

```python
from pydantic import BaseModel, validator, ValidationError
from itl_controlplane_sdk.exceptions import ValidationError as SDK_ValidationError

class ResourceProperties(BaseModel):
    name: str
    size: str = "Standard_D2s_v3"
    
    @validator('name')
    def name_valid(cls, v):
        if len(v) < 3:
            raise ValueError("Name must be at least 3 characters")
        return v

async def create_or_update_resource(self, request: ResourceRequest):
    try:
        props = ResourceProperties(**request.properties)
    except ValidationError as e:
        raise SDK_ValidationError(f"Invalid properties: {e.errors()}")
    
    # Now properties are guaranteed valid
    return await self._create(props)
```

### The Graceful Degradation Pattern

When a secondary operation fails, don't fail the whole request:

```python
async def create_or_update_resource(self, request: ResourceRequest):
    # Create the main resource
    resource = await self._create_core_resource(request)
    
    # Add optional enhancements
    try:
        await self._add_tags(resource, request.tags)
    except Exception as e:
        # Log but don't fail
        logger.warning(f"Failed to add tags: {e}")
    
    try:
        await self._enable_monitoring(resource)
    except Exception as e:
        # Log but don't fail
        logger.warning(f"Failed to enable monitoring: {e}")
    
    # Return successful resource even if enhancements failed
    return ResourceResponse(...)
```

### The Retry Pattern

For transient failures:

```python
import asyncio

async def with_retry(async_fn, max_retries=3, backoff=1):
    """Retry async function with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return await async_fn()
        except TransientError as e:
            if attempt == max_retries - 1:
                raise  # Last attempt, give up
            
            wait_time = backoff * (2 ** attempt)
            logger.warning(
                f"Transient error, retrying in {wait_time}s: {e}"
            )
            await asyncio.sleep(wait_time)

# Usage
async def create_or_update_resource(self, request):
    return await with_retry(
        lambda: self._create_remote_resource(request),
        max_retries=3
    )
```

---

## HTTP Status Codes

### Success Codes

| Code | Meaning | Used For |
|------|---------|----------|
| 200 OK | Request succeeded | Immediate completion (GET, PUT) |
| 201 Created | Resource created | POST (not REST ARM standard) |
| 202 Accepted | Processing started | Long-running operations |
| 204 No Content | Success, no body | DELETE |

### Client Error Codes

| Code | Meaning | Used For |
|------|---------|----------|
| 400 Bad Request | Invalid input | Validation, malformed request |
| 401 Unauthorized | Missing/invalid auth | Authentication failures |
| 403 Forbidden | Not allowed | Authorization failures |
| 404 Not Found | Resource doesn't exist | Missing resources |
| 409 Conflict | Duplicate/state conflict | Duplicate creation, invalid state |
| 429 Too Many Requests | Rate limited | Excessive requests |

### Server Error Codes

| Code | Meaning | Used For |
|------|---------|----------|
| 500 Internal Server Error | Unexpected error | Unhandled exceptions |
| 501 Not Implemented | Not supported | Unsupported operations |
| 503 Service Unavailable | Provider down | Provider crash, maintenance |

---

## Error Response Format

### Standard Error Response

```json
{
  "error": {
    "code": "ResourceNotFound",
    "message": "Resource 'my-resource' not found",
    "target": "/subscriptions/sub-123/resourceGroups/rg-prod/providers/ITL.Compute/virtualmachines/my-resource",
    "details": [
      {
        "code": "ResourceNotFound",
        "message": "The specified resource does not exist"
      }
    ],
    "innererror": {
      "code": "InvalidInputData",
      "message": "Resource name format invalid"
    }
  }
}
```

### Implement Standard Format

```python
from fastapi import FastAPI, Response
from pydantic import BaseModel

class ErrorDetail(BaseModel):
    code: str
    message: str

class ErrorResponse(BaseModel):
    error: ErrorDetail

app = FastAPI()

@app.exception_handler(ResourceNotFoundError)
async def handle_not_found(request, exc):
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(
            error=ErrorDetail(
                code="ResourceNotFound",
                message=str(exc)
            )
        ).dict()
    )
```

---

## Specific Error Scenarios

### Invalid Resource Name

```python
import re

def validate_resource_name(name: str):
    """Validate resource name format"""
    if not re.match(r'^[a-zA-Z0-9-]{1,80}$', name):
        raise ValueError(
            "Resource name must contain only alphanumeric and hyphens, "
            "and be 1-80 characters"
        )

async def create_or_update_resource(self, request):
    try:
        validate_resource_name(request.resource_name)
    except ValueError as e:
        raise BadRequest(str(e))
```

### Resource Already Exists

```python
async def create_or_update_resource(self, request):
    # PUT is idempotent if resource exists
    if await self._exists(request.resource_name):
        # Update existing
        return await self._update(request)
    else:
        # Create new
        return await self._create(request)
```

### Invalid Resource State

```python
async def delete_resource(self, request):
    resource = await self.get_resource(request)
    
    if resource.provisioning_state == ProvisioningState.DELETING:
        raise InvalidOperationError("Resource is already being deleted")
    
    if resource.provisioning_state == ProvisioningState.PROVISIONING:
        raise InvalidOperationError("Cannot delete while provisioning")
    
    return await self._delete(resource)
```

### Rate Limit Exceeded

```python
from fastapi import Response

async def apply_rate_limit(request, call_next):
    if not await rate_limiter.is_allowed(request.client.host):
        return Response(
            status_code=429,
            headers={"Retry-After": "60"},
            content={"error": {"code": "TooManyRequests"}}
        )
    return await call_next(request)

app.middleware("http")(apply_rate_limit)
```

---

## Testing Error Paths

```python
import pytest
from itl_controlplane_sdk.exceptions import ResourceNotFoundError

@pytest.mark.asyncio
async def test_error_not_found(provider):
    from itl_controlplane_sdk import ResourceRequest
    
    request = ResourceRequest(
        resource_type="myresource",
        resource_name="nonexistent"
    )
    
    with pytest.raises(ResourceNotFoundError):
        await provider.get_resource(request)

@pytest.mark.asyncio
async def test_error_validation(provider):
    from itl_controlplane_sdk import ResourceRequest
    
    request = ResourceRequest(
        resource_type="myresource",
        resource_name="invalid@name",  # Invalid char
    )
    
    with pytest.raises(BadRequest, match="invalid"):
        await provider.create_or_update_resource(request)

@pytest.mark.asyncio
async def test_error_duplicate(provider):
    from itl_controlplane_sdk import ResourceRequest
    
    request = ResourceRequest(
        resource_type="myresource",
        resource_name="duplicate-test"
    )
    
    # First create succeeds
    await provider.create_or_update_resource(request)
    
    # Second fails
    with pytest.raises(ResourceAlreadyExistsError):
        await provider.create_or_update_resource(request)
```

---

## Error Recovery Strategies

### Transient Error Retry

```python
import asyncio
from time import time

async def call_with_exponential_backoff(
    fn,
    max_attempts=3,
    initial_wait=1,
    max_wait=30
):
    """Retry with exponential backoff"""
    wait_time = initial_wait
    
    for attempt in range(max_attempts):
        try:
            return await fn()
        except TransientError:
            if attempt == max_attempts - 1:
                raise
            
            logger.info(f"Retrying in {wait_time}s (attempt {attempt + 1})")
            await asyncio.sleep(wait_time)
            wait_time = min(wait_time * 2, max_wait)
```

### Partial Failure Handling

```python
async def create_multiple_resources(requests):
    """Create multiple, fail gracefully on partial failures"""
    results = {"succeeded": [], "failed": []}
    
    for request in requests:
        try:
            result = await self.create_or_update_resource(request)
            results["succeeded"].append(result)
        except Exception as e:
            logger.error(f"Failed to create {request.resource_name}: {e}")
            results["failed"].append({
                "resource": request.resource_name,
                "error": str(e)
            })
    
    return results  # Caller can decide if partial success is acceptable
```

---

## Related Documentation

- [14-MONITORING.md](14-MONITORING.md) - Error monitoring
- [15-TROUBLESHOOTING.md](15-TROUBLESHOOTING.md) - Debugging guide
- [SDK API Reference](../03-API_REFERENCE.md) - All exceptions
- [12-TESTING_GUIDE.md](12-TESTING_GUIDE.md) - Testing errors

---

Robust error handling is essential for reliable production providers.
