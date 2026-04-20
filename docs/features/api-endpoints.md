# FastAPI: Endpoints & Application Factory

**Status**:  Production-Ready  
**Implementation**: Complete fastapi submodule  
**Coverage**: API creation, middleware, routing, error handling

Unified, reusable FastAPI utilities for building consistent API applications across the platform. Eliminates boilerplate middleware setup and promotes standardization.

---

## Overview

The **FastAPI module** (`itl_controlplane_sdk.api`) provides a factory pattern for creating configured FastAPI applications with sensible defaults. Instead of duplicating middleware and error handling setup in every application (API Gateway, Keycloak, Core Provider, Compute Provider), all use the same factory to create consistent applications.

### Architecture: Before vs. After

**Before (Duplicated across 4 apps):**
```
API Gateway              Keycloak Provider     Core Provider      Compute Provider
├── FastAPI             ├── FastAPI           ├── FastAPI        ├── FastAPI
├── Custom CORS         ├── Custom CORS       ├── Custom CORS    ├── Custom CORS
├── Custom logging      ├── Custom logging    ├── Custom logging ├── Custom logging
├── Custom error        ├── Custom error      ├── Custom error   ├── Custom error
└── Custom health       └── Custom health     └── Custom health  └── Custom health
```

**After (Unified):**
```
SDK: itl_controlplane_sdk.api
├── AppFactory (creates configured apps)
├── Middleware (logging, errors, CORS)
├── Routes (health checks)
├── Models (error, health, pagination)
└── Config (dev/prod profiles)

↓ Used by all ↓

API Gateway        Keycloak Provider     Core Provider      Compute Provider
├── AppFactory()   ├── AppFactory()      ├── AppFactory()   ├── AppFactory()
└── Custom logic   └── Custom logic      └── Custom logic   └── Custom logic
```

### Key Benefits

 **Eliminate Duplication** — ~150 lines of boilerplate across 4 apps  
 **Consistency** — All applications use identical patterns  
 **Maintainability** — Fix bugs once, everywhere  
 **Onboarding** — New apps follow proven template  
 **Testability** — Common components tested once  
 **Flexibility** — Extensible without breaking changes

---

## What's Included

### 9 New Files (877 lines total)

| File | Lines | Purpose |
|------|-------|---------|
| `fastapi/__init__.py` | 10 | Module exports |
| `fastapi/app_factory.py` | 170 | Main AppFactory class |
| `fastapi/config.py` | 70 | FastAPIConfig with dev/prod |
| `fastapi/models.py` | 40 | Common Pydantic models |
| `fastapi/middleware/logging.py` | 50 | Request/response logging |
| `fastapi/middleware/error_handling.py` | 100 | Exception handlers + APIError |
| `fastapi/middleware/cors.py` | 45 | CORS configuration |
| `fastapi/routes/health.py` | 40 | Health check endpoints |
| `fastapi/README.md` | 350 | Full documentation |

### Directory Structure

```
src/itl_controlplane_sdk/fastapi/
├── __init__.py                    # Exports (AppFactory, FastAPIConfig)
├── app_factory.py                 # Main factory class
├── config.py                      # Configuration dataclass
├── models.py                      # Common Pydantic response models
├── README.md                       # Comprehensive usage guide
├── middleware/
│   ├── __init__.py
│   ├── logging.py                 # LoggingMiddleware
│   ├── error_handling.py          # Exception handlers + APIError
│   └── cors.py                    # CORS configuration
└── routes/
    ├── __init__.py
    └── health.py                  # /health, /ready endpoints
```

---

## Installation

Add FastAPI support to the SDK:

```bash
pip install itl-controlplane-sdk[fastapi]
```

Updated `pyproject.toml` with optional dependency:
```toml
[project.optional-dependencies]
fastapi = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "starlette>=0.27.0"
]
```

---

## Quick Start

### 5 Lines to Get Started

```python
from itl_controlplane_sdk.api import AppFactory

factory = AppFactory("My App", "1.0.0")
app = factory.create_app(routers=[router1, router2])

# uvicorn main:app --reload
```

### That's It!

You automatically get:
-  CORS middleware (configurable)
-  Request/response logging
-  Global error handling
-  Health check endpoints (`/health`, `/ready`)
-  OpenAPI documentation (`/docs`, `/redoc`)

---

## AppFactory API

### Basic Usage

```python
from itl_controlplane_sdk.api import AppFactory

factory = AppFactory("My Application", "1.0.0")
app = factory.create_app(
    routers=[router1, router2],           # APIRouter instances
    cors_origins=["https://example.com"], # CORS allowed origins
    add_health_routes=True,               # Include /health, /ready
    add_exception_handlers=True,          # Global error handling
    add_logging_middleware=True,          # Request/response logging
    docs_url="/docs",                     # Swagger UI
    redoc_url="/redoc",                   # ReDoc
    openapi_url="/openapi.json",          # OpenAPI schema
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `routers` | List[APIRouter] | `[]` | APIRouter instances to include |
| `cors_origins` | List[str] | `["*"]` | CORS allowed origins |
| `add_health_routes` | bool | `True` | Whether to include health endpoints |
| `add_exception_handlers` | bool | `True` | Whether to setup global error handlers |
| `add_logging_middleware` | bool | `True` | Whether to add logging middleware |
| `docs_url` | str | `"/docs"` | Swagger UI path (None to disable) |
| `redoc_url` | str | `"/redoc"` | ReDoc path (None to disable) |
| `openapi_url` | str | `"/openapi.json"` | OpenAPI schema path (None to disable) |

---

## Middleware Stack

### 1. LoggingMiddleware

Logs all HTTP requests and responses with timing and status:

```
→ GET /resources/res-001
← GET /resources/res-001 [200] (0.045s)

→ POST /subscriptions/sub-123/resourceGroups
← POST /subscriptions/sub-123/resourceGroups [201] (0.150s)
```

**Features:**
- Request method and path
- Response status code
- Response time in milliseconds
- Automatic for all endpoints

**Configuration:**
```python
from itl_controlplane_sdk.api import FastAPIConfig

config = FastAPIConfig(log_level="DEBUG")  # Or INFO, WARNING, ERROR
factory = AppFactory("App", "1.0.0", config=config)
app = factory.create_app()
```

### 2. Error Handling Middleware

Global exception handlers for consistent error responses:

```python
from itl_controlplane_sdk.api.middleware.error_handling import APIError

# Raise structured errors
@app.get("/items/{item_id}")
async def get_item(item_id: int):
    if item_id < 0:
        raise APIError(
            status_code=400,
            code="INVALID_ITEM_ID",
            message="Item ID must be positive",
            details={"item_id": item_id}
        )
    return {"id": item_id}
```

**Automatic Handling:**

| Exception | Status | Code |
|-----------|--------|------|
| `APIError` | Custom | Custom |
| `ValueError` | 400 | `VALIDATION_ERROR` |
| `KeyError` | 404 | `NOT_FOUND` |
| `Exception` | 500 | `INTERNAL_ERROR` |

**Response Format:**

```json
{
  "error": "Item ID must be positive",
  "code": "INVALID_ITEM_ID",
  "request_id": "abc-123-def-456",
  "timestamp": "2024-01-31T12:34:56Z",
  "details": {
    "item_id": -1
  }
}
```

### 3. CORS Middleware

Configurable CORS for cross-origin requests:

```python
from itl_controlplane_sdk.api import FastAPIConfig

# Development (allow all)
config = FastAPIConfig.development()

# Production (restricted)
config = FastAPIConfig.production()

# Custom
config = FastAPIConfig(
    cors_origins=["https://app.com", "https://admin.app.com"],
    cors_credentials=True,
    cors_methods=["GET", "POST", "PUT", "DELETE"],
    cors_headers=["Content-Type", "Authorization"]
)

factory = AppFactory("App", "1.0.0", config=config)
app = factory.create_app()
```

---

## Automatic Routes

### Health Endpoints

| Endpoint | Purpose | Response |
|----------|---------|----------|
| `GET /health` | Liveness probe | `{"status": "ok", "timestamp": "..."}` |
| `GET /ready` | Readiness probe | `{"status": "ready", "timestamp": "..."}` |

```python
# Test health
GET http://localhost:8000/health

# Response
{
  "status": "ok",
  "timestamp": "2024-01-31T12:34:56Z"
}
```

### Documentation Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /docs` | Swagger UI (interactive testing) |
| `GET /redoc` | ReDoc (API reference) |
| `GET /openapi.json` | OpenAPI schema (machine-readable) |

### Custom Health Checks

```python
# Disable automatic health routes
app = factory.create_app(add_health_routes=False)

# Create custom health with dependency checks
@app.get("/health")
async def health():
    db_healthy = await check_database()
    broker_healthy = await check_message_broker()
    
    status = "ok" if (db_healthy and broker_healthy) else "degraded"
    return {
        "status": status,
        "database": db_healthy,
        "broker": broker_healthy,
        "timestamp": datetime.utcnow().isoformat()
    }
```

---

## Common Models

Reusable Pydantic models for consistent responses:

```python
from itl_controlplane_sdk.api.models import (
    ErrorResponse,
    HealthResponse,
    PaginatedResponse,
    MessageResponse
)

# Error responses (automatic)
class ErrorResponse(BaseModel):
    error: str
    code: str
    request_id: Optional[str] = None
    timestamp: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

# Health check responses (automatic)
class HealthResponse(BaseModel):
    status: str  # "ok", "ready", "degraded"
    timestamp: str

# Pagination (for list endpoints)
class PaginatedResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int
    skip: int
    limit: int

# Simple messages
class MessageResponse(BaseModel):
    message: str
    code: Optional[str] = None
    timestamp: Optional[str] = None
```

### Using in Routes

```python
@app.get("/resources", response_model=PaginatedResponse)
async def list_resources(skip: int = 0, limit: int = 10):
    resources = await db.get_resources(skip=skip, limit=limit)
    total = await db.count_resources()
    
    return PaginatedResponse(
        items=resources,
        total=total,
        skip=skip,
        limit=limit
    )

@app.post("/resources", response_model=MessageResponse)
async def create_resource(data: ResourceSchema):
    resource = await db.create_resource(data)
    return MessageResponse(
        message=f"Resource '{resource.name}' created",
        code="CREATED"
    )
```

---

## Configuration

### FastAPIConfig Class

```python
from itl_controlplane_sdk.api import FastAPIConfig

# Development profile (allow all)
config = FastAPIConfig.development()

# Production profile (restricted)
config = FastAPIConfig.production()

# Custom profile
config = FastAPIConfig(
    cors_origins=["https://app.com"],
    cors_credentials=True,
    cors_methods=["GET", "POST", "PUT", "DELETE"],
    cors_headers=["Content-Type", "Authorization"],
    log_level="INFO",
    enable_metrics=False,
    enable_tracing=False
)

factory = AppFactory("App", "1.0.0", config=config)
app = factory.create_app()
```

### Environment-based Configuration

```python
import os
from itl_controlplane_sdk.api import FastAPIConfig, AppFactory

# Load from environment
ENV = os.getenv("ENV", "development")

if ENV == "production":
    config = FastAPIConfig.production()
else:
    config = FastAPIConfig.development()

factory = AppFactory("My App", "1.0.0", config=config)
app = factory.create_app(routers=[...])
```

---

## Real-World Examples

### Example 1: API Gateway

**Before (~60 lines):**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .middleware.logging import custom_logging
from .middleware.errors import setup_errors

def create_app():
    app = FastAPI(
        title="ITL ControlPlane API",
        version="1.0.0"
    )
    
    app.add_middleware(CORSMiddleware, allow_origins=["*"])
    app.add_middleware(custom_logging)
    setup_errors(app)
    
    app.include_router(health_routes.router)
    app.include_router(provider_routes.router)
    app.include_router(resources_routes.router)
    
    @app.on_event("startup")
    async def startup():
        await init_graph_db()
        await init_broker()
    
    return app
```

**After (~15 lines):**
```python
from itl_controlplane_sdk.api import AppFactory
from . import health_routes, provider_routes, resources_routes

def create_app():
    factory = AppFactory("ITL ControlPlane API", "1.0.0")
    app = factory.create_app(routers=[
        health_routes.router,
        provider_routes.router,
        resources_routes.router
    ])
    
    @app.on_event("startup")
    async def startup():
        await init_graph_db()
        await init_broker()
    
    return app
```

**Savings:** 45 lines, much clearer

### Example 2: Keycloak Provider

```python
from fastapi import APIRouter
from itl_controlplane_sdk.api import AppFactory

# Create router for IAM endpoints
iam_router = APIRouter()

@iam_router.post("/tokens")
async def create_token(request: TokenRequest):
    token = await keycloak.create_token(request)
    return {"access_token": token}

# Create app with single line
factory = AppFactory("Keycloak Provider", "1.0.0")
app = factory.create_app(routers=[iam_router])

@app.on_event("startup")
async def startup():
    await keycloak.connect()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
```

### Example 3: Core Provider

```python
from itl_controlplane_sdk.api import AppFactory
from .resource_handlers import core_router

factory = AppFactory("Core Provider", "1.0.0")
app = factory.create_app(routers=[core_router])

@app.on_event("startup")
async def startup():
    await init_messaging()
    await init_resource_handlers()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
```

### Example 4: Multiple Routers with Dependencies

```python
from fastapi import APIRouter, Depends, HTTPException
from itl_controlplane_sdk.api import AppFactory
from itl_controlplane_sdk.api.middleware.error_handling import APIError

# Create routers
users_router = APIRouter(prefix="/users")
items_router = APIRouter(prefix="/items")
admin_router = APIRouter(prefix="/admin")

@users_router.get("/{user_id}")
async def get_user(user_id: int):
    if user_id < 0:
        raise APIError(status_code=400, code="INVALID_ID", 
                      message="User ID must be positive")
    return {"id": user_id}

@items_router.post("/")
async def create_item(name: str):
    return {"name": name}

# Combine into single app
factory = AppFactory("Multi-router App", "1.0.0")
app = factory.create_app(routers=[
    users_router,
    items_router,
    admin_router
])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## Testing

### Unit Tests with TestClient

```python
import pytest
from fastapi.testclient import TestClient
from itl_controlplane_sdk.api import AppFactory

# Create test app
factory = AppFactory("Test App", "1.0.0")
app = factory.create_app()
client = TestClient(app)

def test_health():
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data

def test_readiness():
    """Test readiness endpoint"""
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"

def test_error_handling():
    """Test error response format"""
    from itl_controlplane_sdk.api.middleware.error_handling import APIError
    
    @app.get("/test-error")
    async def test_error():
        raise APIError(
            status_code=400,
            code="TEST_ERROR",
            message="Test error message"
        )
    
    response = client.get("/test-error")
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "TEST_ERROR"
    assert data["error"] == "Test error message"
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_full_request_cycle():
    """Test complete request lifecycle"""
    factory = AppFactory("Test", "1.0.0")
    app = factory.create_app()
    client = TestClient(app)
    
    # Health check
    response = client.get("/health")
    assert response.status_code == 200
    
    # OpenAPI docs
    response = client.get("/docs")
    assert response.status_code == 200
    
    # Schema
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
```

---

## Integration Guide

### Step 1: For API Gateway

Update [ITL.ControlPlane.Api/src/server.py](../../../ITL.ControlPlane.Api/src/server.py):

```python
# Before: ~50 lines of FastAPI setup
# After: Use AppFactory

from itl_controlplane_sdk.api import AppFactory

def create_app():
    factory = AppFactory("ITL ControlPlane API", "1.0.0")
    return factory.create_app(routers=[...])
```

**Effort:** 30 minutes  
**Lines Saved:** ~40 lines

### Step 2: For Keycloak Provider

Update keycloak-provider/src/main.py:

```python
from itl_controlplane_sdk.api import AppFactory

factory = AppFactory("Keycloak Provider", "1.0.0")
app = factory.create_app(routers=[iam_router])
```

**Effort:** 20 minutes  
**Lines Saved:** ~30 lines

### Step 3: For Core Provider

Same as Keycloak provider update.

### Step 4: For Compute Provider

Same as Keycloak provider update.

### Total Benefits

 130+ lines of code removed  
 Consistent patterns everywhere  
 Standardized error handling  
 Unified logging  
 Easier to maintain

---

## Troubleshooting

### "ImportError: No module named 'fastapi'"

**Solution:** Install with optional dependency
```bash
pip install itl-controlplane-sdk[fastapi]
```

### Custom exception not being caught

**Solution:** Register exception handler after creating app
```python
@app.exception_handler(MyCustomError)
async def custom_error_handler(request, exc):
    return JSONResponse(status_code=400, content={...})
```

### Need different health logic

**Solution:** Disable automatic routes and create custom
```python
app = factory.create_app(add_health_routes=False)

@app.get("/health")
async def custom_health():
    return {...}
```

### CORS errors in frontend

**Solution:** Configure CORS origins appropriately
```python
config = FastAPIConfig(
    cors_origins=["http://localhost:3000", "https://app.com"]
)
```

### Too verbose logging

**Solution:** Adjust log level
```python
config = FastAPIConfig(log_level="WARNING")
```

---

## Related Documentation

- [07-LOCATION_VALIDATION.md](07-LOCATION_VALIDATION.md) - Location validation in endpoints
- [06-HANDLER_MIXINS.md](06-HANDLER_MIXINS.md) - Handler patterns for endpoints
- [23-BEST_PRACTICES.md](23-BEST_PRACTICES.md) - API design patterns

---

## Quick Reference

### Installation
```bash
pip install itl-controlplane-sdk[fastapi]
```

### Create App
```python
from itl_controlplane_sdk.api import AppFactory

factory = AppFactory("App", "1.0.0")
app = factory.create_app(routers=[router1, router2])
```

### Error Handling
```python
from itl_controlplane_sdk.api.middleware.error_handling import APIError

raise APIError(status_code=400, code="ERROR", message="...")
```

### Configuration
```python
from itl_controlplane_sdk.api import FastAPIConfig

config = FastAPIConfig.production()  # or .development()
factory = AppFactory("App", "1.0.0", config=config)
```

### Health Checks
```
GET /health   → {"status": "ok", "timestamp": "..."}
GET /ready    → {"status": "ready", "timestamp": "..."}
```

### Testing
```python
from fastapi.testclient import TestClient

client = TestClient(app)
response = client.get("/health")
assert response.status_code == 200
```

---

**Document Version**: 1.0 (Consolidated from 3 docs)  
**Last Updated**: February 14, 2026  
**Status**:  Production-Ready

