# Troubleshooting Guide

Solutions to common issues when building with the ITL ControlPlane SDK.

---

## Quick Diagnosis

Start here if something isn't working:

### 1. Provider Won't Start

**Symptoms:** Container exits immediately, no logs

**Diagnosis:**
```bash
# Check container logs
docker logs my-provider

# Check entrypoint syntax
python -m py_compile src/my_provider/server.py

# Try running locally first
python src/my_provider/server.py
```

**Common Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| Import error | Check `pip list` for missing dependencies |
| Port conflict | Use `lsof -i :8000` to find process |
| File permissions | Ensure `Dockerfile` COPY preserves permissions |
| Python path | Check `PYTHONPATH` env var |
| Syntax error | Run `python -m py_compile src/...` |

---

### 2. API Gateway Can't Find Provider

**Symptoms:** 404 when calling resource endpoints

**Diagnosis:**
```bash
# Check provider registration
curl http://localhost:9050/api/providers

# Check provider health
curl http://provider:8000/health

# Check gateway logs
docker logs api-gateway

# Verify network connectivity
docker exec api-gateway ping provider
```

**Common Causes:**

| Cause | Solution |
|-------|----------|
| Provider not registered | Call `/api/providers/register` endpoint |
| Wrong namespace | Check provider namespace vs API Gateway config |
| Health check failing | Fix `/health` endpoint to return 200 |
| Wrong port | SDK defaults to 8000, check config |
| Network isolation | Use same docker network or configure DNS |

---

### 3. Resources Not Persisting

**Symptoms:** Create resource, get 200, but get returns 404

**Diagnosis:**
```python
# Check if resources are in memory
provider.resources  # Should show resources

# Check database connection
await db.first("SELECT 1")

# Check if handler is using correct storage
print(handler.storage)
```

**Common Causes:**

| Cause | Solution |
|-------|----------|
| In-memory only | Use database storage instead of dict |
| Handler not saving | Ensure handler returns storage correctly |
| Async/sync mismatch | All handler methods must be async |
| Database not connected | Check `DATABASE_URL` env var |
| Table not created | Run migrations: `alembic upgrade head` |

---

### 4. Validation Always Fails

**Symptoms:** All create requests fail with validation error

**Diagnosis:**
```python
# Test validation directly
from pydantic import ValidationError

try:
    properties = MyProperties(**request_data)
    print("Valid!")
except ValidationError as e:
    print(e.errors())

# Check schema definition
print(MyProperties.schema())
```

**Common Causes:**

| Cause | Solution |
|-------|----------|
| Wrong property names | Use exact names from schema |
| Type mismatch | Properties must match schema types |
| Validator too strict | Review validator functions |
| Schema not updated | Restart provider after schema change |
| Missing required field | Check `required` in schema |

---

### 5. Duplicate Resource Errors

**Symptoms:** Can't create second resource, "already exists" error

**Diagnosis:**
```python
# Check handler scope configuration
print(handler.UNIQUENESS_SCOPE)

# Check storage keys
for key in handler.storage:
    print(f"Key: {key}")

# Manually create similar resources
res1 = handler.create("res-001", {}, "type", {"sub": "s1", "rg": "r1"})
res2 = handler.create("res-001", {}, "type", {"sub": "s1", "rg": "r2"})
```

**Common Causes:**

| Cause | Solution |
|-------|----------|
| Scope too broad | Add subscription or RG to scope |
| Keys not including scope | Check key generation |
| Handler not checking storage | Use `ScopedResourceHandler` |
| Case sensitivity | Resource names are case-sensitive |
| Old data in storage | Clear storage or database |

---

## Error Messages Reference

### BadRequest (400)

```
"Invalid resource name 'my@resource'"
```

**Cause:** Resource name contains invalid characters  
**Solution:** Use only alphanumerics, hyphens, underscores

---

### Unauthorized (401)

```
"No authentication token provided"
```

**Cause:** Missing or invalid API key  
**Solution:** Add `Authorization: Bearer <token>` header

---

### NotFound (404)

```
"Resource not found: my-resource"
```

**Cause:** Resource doesn't exist or wrong subscription/RG  
**Solution:** Check resource name, subscription, and resource group

---

### Conflict (409)

```
"Resource 'my-resource' already exists"
```

**Cause:** Duplicate creation attempt  
**Solution:** Check if resource was created, use PUT for update instead

---

### TooManyRequests (429)

```
"Rate limit exceeded: 100 requests per minute"
```

**Cause:** Hitting rate limit  
**Solution:** Implement exponential backoff in client

---

### InternalServerError (500)

```
"Unhandled exception in provider"
```

**Cause:** Provider logic error  
**Solution:** Check provider logs for detailed error

---

### ServiceUnavailable (503)

```
"Provider is not responding"
```

**Cause:** Provider crashed or unreachable  
**Solution:** Restart provider and check health endpoint

---

## Performance Issues

### Slow Creation

**Diagnosis:**
```python
import time

async def create_or_update_resource(self, request):
    start = time.time()
    
    # ... creation logic ...
    
    duration = time.time() - start
    logger.info(f"Creation took {duration}s")
```

**Solutions:**

1. **Add caching** - Cache frequently accessed resources
2. **Parallelize** - Use asyncio for concurrent operations
3. **Batch operations** - Process multiple resources together
4. **Move to background** - Return 202 Accepted, process async

---

### High Memory Usage

**Diagnosis:**
```python
import tracemalloc

tracemalloc.start()

# ... do work ...

current, peak = tracemalloc.get_traced_memory()
print(f"Current: {current / 1024 / 1024}MB; Peak: {peak / 1024 / 1024}MB")
```

**Solutions:**

1. **Don't cache everything** - Implement TTL cache
2. **Paginate results** - Don't load all resources at once
3. **Use generators** - Yield results instead of building list
4. **Close connections** - Don't keep DB connections open

---

## Common Patterns That Look Like Bugs

### Async Function Not Awaited

```python
# WRONG - returns coroutine, not result
async def create_resource(self, request):
    result = db.save(resource)  # Forgot await!
    return result

# RIGHT
async def create_resource(self, request):
    result = await db.save(resource)
    return result
```

---

### Sync Function Called from Async

```python
# WRONG - blocking call in async context
async def create_resource(self, request):
    result = time.sleep(5)  # Blocks entire event loop!
    return result

# RIGHT
async def create_resource(self, request):
    await asyncio.sleep(5)  # Non-blocking
    return result
```

---

### Handler Not Inheriting from Base

```python
# WRONG - handler doesn't work
from itl_controlplane_sdk.providers import ValidatedResourceHandler

class MyHandler:  # Missing inheritance!
    pass

# RIGHT
class MyHandler(ValidatedResourceHandler):
    pass
```

---

## Testing in Isolation

### Test Handler Directly

```python
import pytest

@pytest.mark.asyncio
async def test_handler_basic():
    from my_provider.handlers import MyHandler
    
    storage = {}
    handler = MyHandler(storage)
    
    # Test directly
    id, data = handler.create_resource("test", {}, "type", {})
    print(f"Created: {id}")
    
    assert "test" in id
    assert storage  # Storage should be populated
```

### Test Provider in Memory

```python
@pytest.mark.asyncio
async def test_provider_in_memory():
    from my_provider import MyProvider
    from itl_controlplane_sdk import ResourceRequest
    
    provider = MyProvider(in_memory=True)
    
    request = ResourceRequest(
        resource_type="myresource",
        resource_name="test-001",
        subscription_id="sub-123",
        resource_group="rg-test"
    )
    
    response = await provider.create_or_update_resource(request)
    assert response.name == "test-001"
```

### Test with Docker Locally

```bash
# Build and run
docker build -t test-provider .
docker run -p 8000:8000 test-provider

# Test endpoints
curl http://localhost:8000/health
curl -X PUT \
  http://localhost:8000/create \
  -H "Content-Type: application/json" \
  -d '{"properties": {}}'
```

---

## Collecting Debug Information

When reporting issues, collect:

```bash
# 1. Provider logs
docker logs my-provider > provider.log 2>&1

# 2. API Gateway logs
docker logs api-gateway > gateway.log 2>&1

# 3. System info
python --version > debug.txt
pip list >> debug.txt
docker version >> debug.txt

# 4. Network connectivity
docker network inspect itl-network >> debug.txt

# 5. Provider health
curl -v http://localhost:8000/health >> debug.txt 2>&1

# 6. Create test resource
curl -X PUT \
  http://localhost:8000/subscriptions/test/create \
  -H "Content-Type: application/json" \
  -d '{}' -v >> debug.txt 2>&1
```

---

## SDK Version Issues

Check compatibility:

```bash
# Check installed version
pip show itl-controlplane-sdk

# Check for breaking changes in release notes
https://github.com/ITL/ControlPlane.SDK/releases

# Upgrade to latest
pip install --upgrade itl-controlplane-sdk

# Pin to specific version
pip install itl-controlplane-sdk==1.2.3
```

---

## Getting Help

1. **Check this guide first** - Most issues documented here
2. **Check SDK examples** - Look at `/examples` in SDK repo
3. **Search issues** - Look on GitHub for similar problems
4. **Ask in Slack** - Post in #itl-sdk channel
5. **File bug report** - Include debug info collected above

---

## Related Documentation

- [10-ADVANCED_PATTERNS.md](10-ADVANCED_PATTERNS.md) - Design patterns
- [12-TESTING_GUIDE.md](12-TESTING_GUIDE.md) - Testing strategies
- [14-MONITORING.md](14-MONITORING.md) - Monitoring troubleshooting
- [SDK API Reference](../03-API_REFERENCE.md) - All methods

---

## Checklist for New Providers

Before deploying to production:

- [ ] All endpoints respond to health checks
- [ ] Validation rejects invalid input
- [ ] Error messages are clear
- [ ] Resources persist after restart
- [ ] Duplicate detection works
- [ ] Delete is idempotent
- [ ] Logs are structured and searchable
- [ ] Metrics are exported
- [ ] Load tested at expected volume
- [ ] Error paths tested
- [ ] Recovery procedures documented

---

Most issues are one of these five: misconfiguration, missing dependencies, networking, async/await, or scope/storage. Check in that order!
