# Concurrency, Async, and Performance Best Practices

Guide to writing efficient, non-blocking code in resource providers.

---

## Understanding Async/Await

### Async vs Sync

```python
# SYNC - blocks entire thread while waiting
def sync_get_resource():
    result = requests.get('http://api.example.com/resource')  # Blocks!
    return result.json()

# ASYNC - releases thread while waiting
async def async_get_resource():
    async with httpx.AsyncClient() as client:
        result = await client.get('http://api.example.com/resource')  # Non-blocking!
    return result.json()
```

### The Event Loop

```python
# The event loop runs many async functions "concurrently"
# It doesn't truly run in parallel, but switches between them
# while waiting for I/O

async def fast_io():
    await asyncio.sleep(0.1)  # Yields control
    return "done"

async def main():
    # Run 10 concurrently (not sequentially)
    results = await asyncio.gather(*[fast_io() for _ in range(10)])
    # Takes ~0.1s, not ~1s
```

---

## AsyncIO Patterns

### Sequential vs Concurrent

```python
import asyncio
import time

# WRONG - sequential (slow)
async def slow():
    for i in range(10):
        result = await fetch_data(i)  # Waits for each
        print(f"Got {i}: {result}")
    # Total: ~10 seconds

# RIGHT - concurrent (fast)
async def fast():
    tasks = [fetch_data(i) for i in range(10)]
    results = await asyncio.gather(*tasks)  # All at once
    for i, result in enumerate(results):
        print(f"Got {i}: {result}")
    # Total: ~1 second (duration of slowest)
```

### Common Patterns

```python
import asyncio

# Pattern 1: Create and gather tasks
async def multiple_concurrent_operations():
    tasks = [
        self._fetch_data("a"),
        self._fetch_data("b"),
        self._fetch_data("c"),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

# Pattern 2: Wait for first to complete
async def race_to_first():
    tasks = [
        self._fetch_from_primary(),
        self._fetch_from_backup(),
    ]
    result = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    return result

# Pattern 3: Process as they complete
async def process_as_ready():
    tasks = [self._long_operation(i) for i in range(10)]
    for coro in asyncio.as_completed(tasks):
        result = await coro
        print(f"Got result: {result}")

# Pattern 4: Create task for background work
async def background_work():
    # Start but don't wait
    task = asyncio.create_task(self._sync_in_background())
    
    # Continue immediately
    return "started"
```

---

## Handling Concurrency Issues

### Race Conditions

```python
# WRONG - race condition
async def unsafe_increment():
    value = self.counter  # Read
    await asyncio.sleep(0.1)  # Other tasks might run here
    self.counter = value + 1  # Write might be stale

# RIGHT - use lock
async def safe_increment():
    async with self.counter_lock:  # Ensure atomic
        value = self.counter
        await asyncio.sleep(0.1)
        self.counter = value + 1

# Setup
def __init__(self):
    self.counter = 0
    self.counter_lock = asyncio.Lock()
```

### Resource Exhaustion

```python
# WRONG - unlimited concurrent requests (DOS risk)
async def create_all_resources(resources):
    tasks = [self._create(r) for r in resources]  # 1000+ tasks!
    return await asyncio.gather(*tasks)

# RIGHT - limit concurrency with Semaphore
async def create_all_resources_safely(resources):
    semaphore = asyncio.Semaphore(10)  # Max 10 concurrent
    
    async def limited_create(resource):
        async with semaphore:
            return await self._create(resource)
    
    tasks = [limited_create(r) for r in resources]
    return await asyncio.gather(*tasks)
```

### Deadlock Prevention

```python
# WRONG - can deadlock if functions call each other
async def func_a():
    async with lock_a:
        await asyncio.sleep(0)
        async with lock_b:  # Waiting for func_b
            pass

async def func_b():
    async with lock_b:
        await asyncio.sleep(0)
        async with lock_a:  # Func A holds this!
            pass

# RIGHT - always acquire locks in same order
async def func_a():
    async with lock_a:
        async with lock_b:
            await the_work()

async def func_b():
    async with lock_a:
        async with lock_b:
            await the_other_work()
```

---

## Connection Pooling

### Database Connection Pool

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import QueuePool

# Create pooled engine
engine = create_async_engine(
    "postgresql+asyncpg://user:pass@host/db",
    poolclass=QueuePool,
    pool_size=10,        # Min connections
    max_overflow=20,     # Additional temporary connections
    pool_recycle=3600,   # Recycle connections after 1 hour
    echo=False,
)

# Use in provider
class MyProvider(ResourceProvider):
    def __init__(self):
        super().__init__("ITL.MyProvider")
        self.engine = engine
    
    async def create_or_update_resource(self, request):
        async with AsyncSession(self.engine) as session:
            # Connection from pool automatically returned
            resource = await self._create_in_db(session, request)
        return resource
```

### HTTP Client Connection Pool

```python
import httpx

class MyProvider(ResourceProvider):
    def __init__(self):
        super().__init__("ITL.MyProvider")
        # Reuse client for connection pooling
        self.http_client = httpx.AsyncClient(
            limits=httpx.Limits(
                max_connections=10,
                max_keepalive_connections=5
            )
        )
    
    async def cleanup(self):
        await self.http_client.aclose()
    
    async def create_or_update_resource(self, request):
        response = await self.http_client.get("http://api.example.com/...")
        return response.json()
```

---

## Caching for Performance

### Simple TTL Cache

```python
from datetime import datetime, timedelta
from typing import Dict, Any, Callable

class TTLCache:
    def __init__(self, ttl_seconds: int = 300):
        self.ttl = timedelta(seconds=ttl_seconds)
        self.cache: Dict[str, tuple] = {}
    
    def get(self, key: str) -> Any:
        if key not in self.cache:
            return None
        
        value, created = self.cache[key]
        if datetime.now() - created > self.ttl:
            del self.cache[key]
            return None
        
        return value
    
    def set(self, key: str, value: Any):
        self.cache[key] = (value, datetime.now())

# Usage
class CachingProvider(ResourceProvider):
    def __init__(self):
        super().__init__("ITL.Caching")
        self.cache = TTLCache(ttl_seconds=300)
    
    async def get_resource(self, request):
        cache_key = f"{request.subscription_id}:{request.resource_name}"
        
        # Check cache
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        # Fetch and cache
        resource = await self._fetch(request)
        self.cache.set(cache_key, resource)
        return resource
```

### Cache Invalidation

```python
class CachingProvider(ResourceProvider):
    async def create_or_update_resource(self, request):
        # Create
        resource = await self._create(request)
        
        # Invalidate cache
        cache_key = f"{request.subscription_id}:{request.resource_name}"
        self.cache.cache.pop(cache_key, None)
        
        return resource
```

---

## Performance Optimization Tips

### 1. Batch Database Operations

```python
# WRONG - N database round trips
async def create_bulk(requests):
    resources = []
    for request in requests:
        resource = await self._save_to_db(request)  # 1000 queries!
        resources.append(resource)
    return resources

# RIGHT - single operation
async def create_bulk(requests):
    resources = await self._batch_save_to_db(requests)  # 1 query
    return resources

# Implementation
async def _batch_save_to_db(self, requests):
    async with AsyncSession(self.engine) as session:
        objs = [self._create_model(r) for r in requests]
        session.add_all(objs)
        await session.commit()
        return objs
```

### 2. Use Streaming for Large Lists

```python
# WRONG - load all in memory
async def list_all_resources(self):
    resources = await self._fetch_all()  # Could be millions
    return resources

# RIGHT - use generator
async def list_all_resources_streaming(self):
    async for resource in self._fetch_streaming():
        yield resource

# Usage
async for resource in provider.list_all_resources_streaming():
    print(resource)
```

### 3. Index Frequently Queried Fields

```python
# Database migration
from alembic import op

# Example for SQLAlchemy
class Resource(Base):
    __tablename__ = "resources"
    
    id = Column(String, primary_key=True)
    subscription_id = Column(String, index=True)  # Add index
    resource_group = Column(String, index=True)   # Add index
    provisioning_state = Column(String, index=True)  # Add index
```

### 4. Use Pagination

```python
# WRONG - GET all
async def list_resources(self, request):
    return await self._fetch_all()  # Load entire database!

# RIGHT - paginate
async def list_resources(self, request):
    # Default to first 20
    skip = int(request.query_params.get('$skip', 0))
    top = int(request.query_params.get('$top', 20))
    top = min(top, 100)  # Cap at 100
    
    resources = await self._fetch_paginated(skip, top)
    
    return {
        "value": resources,
        "nextLink": f"...?$skip={skip + top}" if len(resources) == top else None
    }
```

---

## Monitoring Performance

### Async Debugging

```python
import asyncio

# Enable debug mode for development
asyncio.run(main(), debug=True)

# This shows:
# - Slow callbacks
# - Coroutines not awaited
# - Tasks not awaited
```

### Profiling Async Code

```python
import asyncio
import cProfile
import pstats

async def main():
    # Your provider code
    pass

# Profile
profiler = cProfile.Profile()
profiler.enable()
asyncio.run(main())
profiler.disable()

stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)
```

### Measure Concurrency

```python
import asyncio
import time

active_tasks = set()

async def track_concurrency(coro):
    task = asyncio.current_task()
    active_tasks.add(task)
    
    try:
        return await coro
    finally:
        active_tasks.discard(task)

async def log_concurrency():
    while True:
        print(f"Active tasks: {len(active_tasks)}")
        await asyncio.sleep(1)

# Usage
async def main():
    monitor_task = asyncio.create_task(log_concurrency())
    
    tasks = [track_concurrency(work()) for _ in range(100)]
    await asyncio.gather(*tasks)
    
    monitor_task.cancel()
```

---

## Best Practices

✅ **Use async everywhere** - Consistency prevents bugs  
✅ **Apply Semaphore for limits** - Prevent resource exhaustion  
✅ **Batch operations** - Reduce database round trips  
✅ **Use connection pools** - Don't create new connections  
✅ **Cache appropriately** - With proper TTL  
✅ **Paginate large lists** - Don't load everything  
✅ **Index common queries** - Faster database lookups  
✅ **Monitor concurrency** - Detect bottlenecks  
✅ **Test under load** - Find performance issues early  

---

## Related Documentation

- [12-TESTING_GUIDE.md](12-TESTING_GUIDE.md) - Load testing patterns
- [14-MONITORING.md](14-MONITORING.md) - Performance monitoring
- [10-ADVANCED_PATTERNS.md](10-ADVANCED_PATTERNS.md) - Async patterns
- [SDK API Reference](../03-API_REFERENCE.md) - All async methods

---

Well-designed async code scales efficiently and provides responsive providers.
