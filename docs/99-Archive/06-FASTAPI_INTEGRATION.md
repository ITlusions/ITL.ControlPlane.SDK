# FastAPI Module Integration Guide

**Date:** January 31, 2026
**Status:** ✅ Complete - fastapi submodule created in SDK

---

## What Was Created

New FastAPI utilities submodule in `ITL.ControlPlane.SDK`:

```
src/itl_controlplane_sdk/fastapi/
├── __init__.py                 # Exports AppFactory, FastAPIConfig
├── app_factory.py              # Main factory class (170 lines)
├── config.py                   # Configuration (70 lines)
├── models.py                   # Common Pydantic models (40 lines)
├── README.md                   # Full documentation
├── middleware/
│   ├── __init__.py
│   ├── logging.py              # Request/response logging
│   ├── error_handling.py       # Global exception handlers
│   └── cors.py                 # CORS configuration
└── routes/
    ├── __init__.py
    └── health.py               # /health, /ready endpoints
```

---

## Installation

Add FastAPI support to SDK:

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

## Quick Integration Examples

### 1. API Gateway (ITL.ControlPlane.Api)

**Current code** (d:\repos\ITL.ControlPlane.Api\src\server.py):

```python
# ~50 lines of boilerplate setup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .middleware.logging import LoggingMiddleware

app = FastAPI(...)
app.add_middleware(CORSMiddleware, ...)
app.add_middleware(LoggingMiddleware)
# ... exception handlers
# ... routers
```

**New code with FastAPI module:**

```python
from itl_controlplane_sdk.api import AppFactory

def create_app() -> FastAPI:
    factory = AppFactory("ITL ControlPlane API", "1.0.0")
    app = factory.create_app(
        routers=[
            health_routes.router,
            provider_routes.router,
            resource_routes.router,
            metadata_router,
        ],
        cors_origins=["*"]
    )
    
    # API-specific setup only
    @app.on_event("startup")
    async def startup():
        await initialize_graph_database()
        await initialize_message_broker()
    
    @app.on_event("shutdown")
    async def shutdown():
        await shutdown_graph_database()
        await shutdown_message_broker()
    
    return app
```

**Benefits:**
- ✅ Removes 30+ lines of boilerplate
- ✅ Standard middleware (logging, CORS, error handling)
- ✅ Health routes included
- ✅ Consistent with all other ControlPlane apps

---

### 2. Keycloak Provider (keycloak-provider/src/main.py)

**Current code:**
```python
# Custom setup for each provider
app = FastAPI(...)
app.add_middleware(CORSMiddleware, ...)
# ... custom health checks
# ... custom error handling
```

**New code with FastAPI module:**

```python
from itl_controlplane_sdk.api import AppFactory

factory = AppFactory("Keycloak Provider", "1.0.0")
app = factory.create_app(cors_origins=["*"])

@app.on_event("startup")
async def startup():
    await initialize_message_broker()
    await initialize_keycloak_connection()
```

**Benefits:**
- ✅ Same patterns as API gateway
- ✅ Automatic health checks
- ✅ Consistent error handling
- ✅ Easier onboarding for new developers

---

### 3. Core Provider (core-provider/src/main.py)

```python
from itl_controlplane_sdk.api import AppFactory

factory = AppFactory("Core Provider", "1.0.0")
app = factory.create_app(cors_origins=["*"])

@app.on_event("startup")
async def startup():
    await initialize_message_broker()
    # Core-specific setup
```

---

### 4. Compute Provider (vm-provider/src/main.py)

```python
from itl_controlplane_sdk.api import AppFactory

factory = AppFactory("VM Provider", "1.0.0")
app = factory.create_app(cors_origins=["*"])

@app.on_event("startup")
async def startup():
    await initialize_message_broker()
    # Compute-specific setup
```

---

## Architecture Benefits

### Before (Duplicated)
```
API Gateway          Keycloak Provider     Core Provider      Compute Provider
├── FastAPI          ├── FastAPI           ├── FastAPI        ├── FastAPI
├── CORS MW          ├── CORS MW           ├── CORS MW        ├── CORS MW
├── Logging MW       ├── Logging MW        ├── Logging MW      ├── Logging MW
├── Error Handlers   ├── Error Handlers    ├── Error Handlers  ├── Error Handlers
├── Health Routes    ├── Health Routes     ├── Health Routes   ├── Health Routes
└── Custom Setup     └── Custom Setup      └── Custom Setup    └── Custom Setup
```

**Problem:** Maintenance burden, inconsistency, duplication

### After (Unified)
```
SDK: itl_controlplane_sdk.api
├── AppFactory
├── Middleware (logging, error handling, cors)
├── Routes (health checks)
├── Models
└── Config

↑ Used by all ↑

API Gateway        Keycloak Provider     Core Provider      Compute Provider
├── AppFactory     ├── AppFactory        ├── AppFactory      ├── AppFactory
└── Custom Setup   └── Custom Setup      └── Custom Setup    └── Custom Setup
```

**Benefits:**
- ✅ Single source of truth for middleware/routing
- ✅ Consistent patterns everywhere
- ✅ Easier to update (fix once, everywhere)
- ✅ Reduced code duplication
- ✅ Standardized error handling
- ✅ Better for new developers

---

## What's Included

### AppFactory
- Creates FastAPI apps with sensible defaults
- Configurable middleware and routes
- Supports custom startup/shutdown handlers
- Minimal code to get working app

### Middleware
1. **LoggingMiddleware** - Request/response logging with timing
2. **Error Handlers** - Global exception handling with consistent responses
3. **CORS** - Configurable CORS with production/dev profiles

### Routes
- `GET /health` - Liveness probe
- `GET /ready` - Readiness probe

### Models
- `ErrorResponse` - Structured error with code and details
- `HealthResponse` - Health check response
- `PaginatedResponse` - For list endpoints
- `MessageResponse` - Simple message responses

### Configuration
- `FastAPIConfig.development()` - Allow all CORS, debug logging
- `FastAPIConfig.production()` - Restricted CORS, warning logging
- Customizable via dataclass

---

## Next Steps to Integrate

### 1. API Gateway (Low Priority)

Update [ITL.ControlPlane.Api/src/server.py](../../ITL.ControlPlane.Api/src/server.py):

```python
# Replace:
# - Custom middleware setup
# - Custom exception handlers
# - Manual router inclusion

# With:
from itl_controlplane_sdk.api import AppFactory

def create_app() -> FastAPI:
    factory = AppFactory("ITL ControlPlane API", "1.0.0")
    app = factory.create_app(routers=[...])
    
    @app.on_event("startup")
    async def startup():
        # API-specific only
```

**Effort:** 30 minutes
**Lines Saved:** ~40 lines

### 2. Keycloak Provider (Medium Priority)

Update [keycloak-provider/src/main.py](../../ITL.ControlPlane.ResourceProvider.IAM/keycloak-provider/src/main.py):

```python
# Replace custom FastAPI setup with AppFactory
```

**Effort:** 20 minutes
**Lines Saved:** ~30 lines

### 3. Core Provider (Medium Priority)

Same as Keycloak provider

**Effort:** 20 minutes

### 4. Compute Provider (Medium Priority)

Same as Keycloak provider

**Effort:** 20 minutes

---

## Testing the Module

```python
from fastapi.testclient import TestClient
from itl_controlplane_sdk.api import AppFactory

# Create test app
factory = AppFactory("Test App", "1.0.0")
app = factory.create_app()
client = TestClient(app)

# Test health endpoints
def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_readiness():
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
```

---

## File Locations

**SDK Module:**
- `d:\repos\ITL.ControlPanel.SDK\src\itl_controlplane_sdk\fastapi\`

**Documentation:**
- `src/itl_controlplane_sdk/fastapi/README.md` - Full usage guide
- `pyproject.toml` - Updated with fastapi optional dependency

---

## Summary

✅ **Created:** FastAPI utilities submodule in SDK
✅ **Included:** AppFactory, middleware, routes, models, config
✅ **Documented:** Full README with examples
✅ **Ready to use:** All files in place, can be imported immediately

**Next:** Integrate into API Gateway and providers to reduce code duplication

**Estimated effort for full integration:** 1.5-2 hours across all 4 applications
**Lines of code saved:** ~100-150 lines
**Consistency improvement:** Significant (all apps use same patterns)

