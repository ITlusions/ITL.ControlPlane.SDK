# FastAPI Module: Quick Reference

**Status:** ✅ Ready to use
**Location:** `itl_controlplane_sdk.fastapi`
**Namespace:** `from itl_controlplane_sdk.fastapi import ...`

---

## Install

```bash
pip install itl-controlplane-sdk[fastapi]
```

---

## Basic Usage

```python
from itl_controlplane_sdk.fastapi import AppFactory

# Create factory
factory = AppFactory("My App", "1.0.0")

# Create app with middleware, health routes, exception handlers
app = factory.create_app(routers=[router1, router2])

# Add app-specific logic
@app.on_event("startup")
async def startup():
    pass
```

---

## AppFactory Options

```python
app = factory.create_app(
    routers=[...],                    # APIRouter instances
    cors_origins=["https://example.com"],  # CORS allowed origins
    add_health_routes=True,           # Include /health, /ready
    add_exception_handlers=True,      # Global error handling
    add_logging_middleware=True,      # Request/response logging
    docs_url="/docs",                 # Swagger UI
    redoc_url="/redoc",               # ReDoc
    openapi_url="/openapi.json",      # OpenAPI schema
)
```

---

## Endpoints (Automatic)

| Endpoint | Purpose | Response |
|----------|---------|----------|
| `GET /health` | Liveness | `{"status": "ok", "timestamp": "..."}` |
| `GET /ready` | Readiness | `{"status": "ready", "timestamp": "..."}` |
| `GET /docs` | Swagger UI | Interactive API docs |
| `GET /redoc` | ReDoc | API reference |
| `GET /openapi.json` | OpenAPI Schema | Machine-readable spec |

---

## Middleware (Automatic)

| Middleware | What it does |
|-----------|--------------|
| **LoggingMiddleware** | Logs all requests/responses with timing |
| **CORSMiddleware** | Handles cross-origin requests |
| **Error Handlers** | Consistent error responses |

---

## Error Handling

### Raise errors in your routes:

```python
from itl_controlplane_sdk.fastapi.middleware.error_handling import APIError

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    if item_id < 0:
        raise APIError(
            status_code=400,
            code="INVALID_ID",
            message="Item ID must be positive",
            details={"item_id": item_id}
        )
    return {"id": item_id}
```

### Automatic handling:

```python
# ValueError → 400 VALIDATION_ERROR
# KeyError → 404 NOT_FOUND
# APIError → custom status/code
# Exception → 500 INTERNAL_ERROR
```

### Response format:

```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "request_id": "...",
  "timestamp": "2024-01-31T12:34:56",
  "details": {...}
}
```

---

## Configuration

```python
from itl_controlplane_sdk.fastapi import FastAPIConfig

# Development (allow all CORS)
config = FastAPIConfig.development()

# Production (restricted CORS)
config = FastAPIConfig.production()

# Custom
config = FastAPIConfig(
    cors_origins=["https://app.com"],
    cors_methods=["GET", "POST"],
    log_level="WARNING"
)

factory = AppFactory("App", "1.0.0", config=config)
app = factory.create_app()
```

---

## Common Models

```python
from itl_controlplane_sdk.fastapi.models import (
    ErrorResponse,
    HealthResponse,
    PaginatedResponse,
    MessageResponse
)

# Use in routes
@app.get("/items", response_model=PaginatedResponse)
async def list_items(skip: int = 0, limit: int = 10):
    return PaginatedResponse(
        items=[...],
        total=100,
        skip=skip,
        limit=limit
    )
```

---

## Health Checks

Disable and customize:

```python
app = factory.create_app(add_health_routes=False)

# Custom health with dependency checks
@app.get("/health")
async def health():
    db_healthy = await check_database()
    broker_healthy = await check_message_broker()
    return {
        "status": "ok" if (db_healthy and broker_healthy) else "degraded",
        "database": db_healthy,
        "broker": broker_healthy
    }
```

---

## Logging

```python
import logging

logger = logging.getLogger(__name__)

@app.get("/items")
async def list_items():
    logger.info("Fetching items")  # Logged automatically
    logger.debug("Debug info")      # Depends on log_level
    return [...]
```

---

## Testing

```python
from fastapi.testclient import TestClient
from itl_controlplane_sdk.fastapi import AppFactory

factory = AppFactory("Test", "1.0.0")
app = factory.create_app()
client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

---

## Full Example: API Gateway

```python
from fastapi import APIRouter
from itl_controlplane_sdk.fastapi import AppFactory

# Create routers
resource_router = APIRouter()

@resource_router.get("/resources/{resource_id}")
async def get_resource(resource_id: str):
    return {"id": resource_id}

# Create app
factory = AppFactory("ControlPlane API", "1.0.0")
app = factory.create_app(routers=[resource_router])

# Setup
@app.on_event("startup")
async def startup():
    logger.info("API started")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## Full Example: Provider

```python
from itl_controlplane_sdk.fastapi import AppFactory

factory = AppFactory("Keycloak Provider", "1.0.0")
app = factory.create_app()

@app.on_event("startup")
async def startup():
    await connect_to_keycloak()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
```

---

## File Structure

```
src/itl_controlplane_sdk/fastapi/
├── __init__.py                    # Exports
├── app_factory.py                 # Main factory
├── config.py                      # Configuration
├── models.py                      # Common models
├── README.md                      # Full docs (350 lines)
├── middleware/
│   ├── __init__.py
│   ├── logging.py
│   ├── error_handling.py
│   └── cors.py
└── routes/
    ├── __init__.py
    └── health.py
```

---

## Common Patterns

### Environment-based Config
```python
import os
from itl_controlplane_sdk.fastapi import FastAPIConfig

if os.getenv("ENV") == "production":
    config = FastAPIConfig.production()
else:
    config = FastAPIConfig.development()

factory = AppFactory("App", "1.0.0", config=config)
app = factory.create_app()
```

### Multiple Routers
```python
from .routes import users, items, admin

app = factory.create_app(routers=[
    users.router,
    items.router,
    admin.router
])
```

### Custom Startup/Shutdown
```python
@app.on_event("startup")
async def startup():
    await initialize_database()
    await initialize_cache()
    logger.info("All services started")

@app.on_event("shutdown")
async def shutdown():
    await close_database()
    logger.info("Shutdown complete")
```

---

## Troubleshooting

### "ImportError: No module named 'fastapi'"
```bash
pip install itl-controlplane-sdk[fastapi]
```

### Custom exception not caught
Register handler after creating app:
```python
@app.exception_handler(MyError)
async def my_handler(request, exc):
    return JSONResponse(status_code=400, content={...})
```

### Need custom health checks
```python
app = factory.create_app(add_health_routes=False)

@app.get("/health")
async def health():
    # Your logic
    return {...}
```

---

## What You Get

✅ AppFactory for consistent app creation
✅ Logging middleware (all requests/responses)
✅ CORS configuration (dev/prod profiles)
✅ Error handling (structured responses)
✅ Health routes (/health, /ready)
✅ Common Pydantic models
✅ Full documentation

---

## Documentation

- **Module Docs:** `fastapi/README.md` (350 lines)
- **Integration Guide:** `FASTAPI_MODULE_INTEGRATION.md`
- **This Reference:** Quick copy/paste examples

---

**Status:** ✅ Ready to use
**Import:** `from itl_controlplane_sdk.fastapi import AppFactory`

