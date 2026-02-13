# FastAPI Module: itl_controlplane_sdk.fastapi

Reusable FastAPI utilities for building applications in the ITL ControlPlane ecosystem.

Provides:
- **AppFactory**: Simplified FastAPI app creation with common setup (lifespan events, middleware, exception handlers)
- **BaseProviderServer**: Base class for resource providers with lifecycle management
- **Provider Setup**: Common utilities for audit middleware, OpenAPI tags, resource registration
- **Generic Routes**: Placeholder CRUD endpoints for generic resources
- **Observability Routes**: Admin endpoints for storage stats and Neo4j sync
- **Models**: Common request/response types (GenericResourceBase)
- **Middleware**: Logging, error handling, CORS configuration
- **Routes**: Standard health checks (/health, /ready)
- **Config**: Centralized configuration

## Installation

Install SDK with FastAPI support:

```bash
pip install itl-controlplane-sdk[fastapi]
```

## Quick Start

### Basic Usage (API Gateway)

```python
from itl_controlplane_sdk.fastapi import AppFactory
from myapp.routes import routers

# Create app with common setup
factory = AppFactory("My API Gateway", "1.0.0")
app = factory.create_app(
    routers=routers,
    cors_origins=["https://example.com"]
)

# Custom lifecycle management
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await initialize_database()
    await initialize_message_broker()
    yield
    # Shutdown
    await close_database()
    await close_message_broker()

# Pass to create_app
factory = AppFactory("My API", "1.0.0")
app = factory.create_app(lifespan=lifespan)
```

### Resource Provider Server

```python
from itl_controlplane_sdk.fastapi import (
    AppFactory,
    BaseProviderServer,
    setup_generic_routes,
    setup_observability_routes,
    add_audit_middleware,
    setup_standard_openapi_tags,
    register_resource_types,
)
from itl_controlplane_sdk.storage import SQLAlchemyStorageEngine

class MyProviderServer(BaseProviderServer):
    def __init__(self):
        self.engine = SQLAlchemyStorageEngine()
        self.provider = MyProvider(engine=self.engine)
        self.registry = ResourceProviderRegistry()
        self.app = None
        self.audit_publisher = None
    
    def create_app(self):
        # Lifespan context manager for startup/shutdown
        from contextlib import asynccontextmanager
        
        server = self
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            await self.engine.initialize()
            await self._initialize_audit_system()  # From BaseProviderServer
            yield
            # Shutdown handled by _create_shutdown_handler()
        
        # Create base app
        factory = AppFactory("MyProvider", "1.0.0")
        app = factory.create_app(cors_origins=["*"], lifespan=lifespan)
        
        # Add provider utilities
        add_audit_middleware(app)
        setup_standard_openapi_tags(app)
        register_resource_types(
            self.registry, 
            "ITL.MyDomain",
            self.provider,
            ["resource1", "resource2", "resource3"]
        )
        
        # Add standard endpoints
        setup_generic_routes(app)
        setup_observability_routes(app, self.engine)
        
        return app
    
    def run(self, host="0.0.0.0", port=8000):
        # Inherited from BaseProviderServer
        self._validate_and_log_config(host, port, "api")
        # ... rest of run implementation
```

## Components

### AppFactory

Creates a configured FastAPI application with:
- CORS middleware
- Logging middleware
- Global exception handlers
- Health check routes (/health, /ready)
- OpenAPI documentation
- Support for lifespan event handlers (FastAPI 0.93+)

**Options:**
- `routers`: List of APIRouter instances
- `cors_origins`: CORS allowed origins
- `add_health_routes`: Include /health and /ready endpoints (default: True)
- `add_exception_handlers`: Install global exception handlers (default: True)
- `add_logging_middleware`: Add request/response logging (default: True)
- `lifespan`: Async context manager for app lifecycle (optional, recommended over on_event)

**Example with lifespan:**
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code
    print("App starting up...")
    yield
    # Shutdown code
    print("App shutting down...")

factory = AppFactory("My App", "1.0.0")
app = factory.create_app(lifespan=lifespan)
```

### BaseProviderServer

Base class for all resource providers with common lifecycle management methods:

- `_validate_and_log_config()` - Validate provider mode and log configuration
- `_initialize_audit_system()` - Setup SQL/RabbitMQ audit adapters
- `_create_shutdown_handler()` - Return async shutdown coroutine
- `_register_with_gateway()` - Register provider with API Gateway

**Subclass Requirements:**
```python
def __init__(self):
    self.engine = SQLAlchemyStorageEngine()
    self.app = None
    self.audit_publisher = None
```

### Provider Setup Utilities

#### register_resource_types()
Register resource types with the provider registry.

```python
from itl_controlplane_sdk.fastapi import register_resource_types

register_resource_types(
    registry=self.registry,
    provider_namespace="ITL.Core",
    provider_instance=self.provider,
    resource_types=["subscriptions", "resourcegroups", "deployments"]
)
```

#### add_audit_middleware()
Add audit context middleware to capture request metadata for logging.

```python
from itl_controlplane_sdk.fastapi import add_audit_middleware

add_audit_middleware(app, extract_actor_from_jwt=True)
```

#### setup_standard_openapi_tags()
Setup standard OpenAPI tags for consistent API documentation.

```python
from itl_controlplane_sdk.fastapi import setup_standard_openapi_tags

setup_standard_openapi_tags(app)
# Adds: Resources, System, Infrastructure tags
```

### Generic Routes

Placeholder CRUD endpoints for generic resource operations. Providers should override with type-specific implementations.

```python
from itl_controlplane_sdk.fastapi import setup_generic_routes

setup_generic_routes(app)

# Registers endpoints:
# POST   /resources/{resource_type}
# GET    /resources/{resource_type}
# GET    /resources/{resource_type}/{resource_name}
# DELETE /resources/{resource_type}/{resource_name}
```

### Observability Routes

Admin and observability endpoints for monitoring.

```python
from itl_controlplane_sdk.fastapi import setup_observability_routes

setup_observability_routes(app, engine)

# Registers endpoints:
# GET  /admin/stats       - Get resource counts from PostgreSQL and Neo4j
# POST /admin/neo4j-sync  - Trigger full sync to Neo4j
```

### Models

Common Pydantic models for standardized responses:

- `GenericResourceBase` - Base model with location and tags fields (for all resources)
- `GenericResourceRequest` - Provider-agnostic resource creation request
- `GenericResourceResponse` - Provider-agnostic resource response

```python
from itl_controlplane_sdk.fastapi import GenericResourceBase

class CustomResourceRequest(GenericResourceBase):
    custom_field: str
    another_field: int
```

### Middleware

#### LoggingMiddleware
Logs all HTTP requests and responses with timing information.

```python
# Automatically added by AppFactory
# Logs format: "← GET /path [200] (0.123s)"
```

#### Error Handling
Global exception handlers for consistent error responses:

- `APIError`: Structured application errors
- `ValueError`: Validation errors (400)
- `KeyError`: Not found errors (404)
- `Exception`: Server errors (500)

**Error Response Format:**
```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "request_id": "xxx",
  "timestamp": "2024-01-31T12:34:56",
  "details": {}
}
```

#### CORS
Configured by AppFactory. Customize with `cors_origins` parameter:

```python
factory = AppFactory("My App", "1.0.0")
app = factory.create_app(
    cors_origins=["https://app.example.com", "https://ui.example.com"]
)
```

### Routes

#### Health Checks
Standard endpoints for all applications:

- `GET /health` - Liveness probe (returns 200)
- `GET /ready` - Readiness probe (returns 200)

Both return:
```json
{
  "status": "ok",
  "timestamp": "2024-01-31T12:34:56"
}
```

Can be disabled with `add_health_routes=False`.

### Configuration

Use `FastAPIConfig` for centralized configuration:

```python
from itl_controlplane_sdk.fastapi import AppFactory, FastAPIConfig

# Development config
config = FastAPIConfig.development()

# Production config
config = FastAPIConfig.production()

factory = AppFactory("My App", "1.0.0", config=config)
app = factory.create_app()
```

**Available Options:**
- `cors_origins`: List of allowed origins
- `cors_credentials`: Allow credentials
- `cors_methods`: Allowed HTTP methods
- `cors_headers`: Allowed request headers
- `log_level`: Logging level (DEBUG, INFO, WARNING, ERROR)

## File Structure

```
src/itl_controlplane_sdk/fastapi/
├── __init__.py                      # Main exports
├── app_factory.py                   # AppFactory class
├── config.py                        # Configuration management
├── models.py                        # GenericResourceBase model
├── provider_server.py               # BaseProviderServer class
├── provider_setup.py                # Provider utilities
├── generic_routes.py                # setup_generic_routes()
├── observability_routes.py          # setup_observability_routes()
├── crud_routes.py                   # CRUD route generation
├── schema_discovery.py              # Resource type schemas
├── README.md                        # Complete documentation
├── CRUD_CHEATSHEET.md               # ⭐ Quick reference (1 page)
├── CRUD_SIDE_BY_SIDE.md             # ⭐ curl, Python, PowerShell comparison
├── CRUD_EXAMPLES.md                 # ⭐ Complete practical examples
├── examples_crud_operations.py      # ⭐ Full virtualNetwork implementation
├── minimal_provider_example.py      # ⭐ Minimal 150-line working provider
├── middleware/
│   ├── __init__.py
│   ├── logging.py                   # Request/response logging
│   ├── error_handling.py            # Exception handlers
│   └── __init__.py
└── routes/
    ├── __init__.py
    └── health.py                    # Health check endpoints
```

## CRUD Operations Quick Start ⭐

New to implementing CRUD endpoints? Start here:

1. **[CRUD_CHEATSHEET.md](./CRUD_CHEATSHEET.md)** — 1-page reference for all patterns
2. **[minimal_provider_example.py](./minimal_provider_example.py)** — 150-line complete working example
3. **[CRUD_SIDE_BY_SIDE.md](./CRUD_SIDE_BY_SIDE.md)** — Same operations in curl, Python, PowerShell
4. **[CRUD_EXAMPLES.md](./CRUD_EXAMPLES.md)** — Practical examples in curl, Python, PowerShell
5. **[examples_crud_operations.py](./examples_crud_operations.py)** — Full virtualNetwork resource implementation

Each file can be run standalone to see CRUD in action!

## Examples

### Full Provider with All Utilities

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from itl_controlplane_sdk.fastapi import (
    AppFactory,
    BaseProviderServer,
    setup_generic_routes,
    setup_observability_routes,
    add_audit_middleware,
    setup_standard_openapi_tags,
    register_resource_types,
)
from itl_controlplane_sdk.storage import SQLAlchemyStorageEngine
from itl_controlplane_sdk.providers import ResourceProviderRegistry

class ComputeProviderServer(BaseProviderServer):
    def __init__(self):
        self.engine = SQLAlchemyStorageEngine()
        self.provider = ComputeProvider(engine=self.engine)
        self.registry = ResourceProviderRegistry()
        self.app = None
        self.audit_publisher = None
    
    def create_app(self) -> FastAPI:
        server = self
        _engine = self.engine
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            await _engine.initialize()
            await server._initialize_audit_system()
            yield
            # Shutdown
            if server.audit_publisher:
                await server.audit_publisher.shutdown()
            await _engine.shutdown()
        
        # Create base app
        factory = AppFactory("ITL Compute Provider", "1.0.0")
        app = factory.create_app(cors_origins=["*"], lifespan=lifespan)
        
        # Setup provider
        add_audit_middleware(app)
        setup_standard_openapi_tags(app)
        register_resource_types(
            self.registry,
            "ITL.Compute",
            self.provider,
            ["virtualMachines", "disks", "networkInterfaces"]
        )
        
        # Setup routes
        setup_generic_routes(app)
        setup_observability_routes(app, _engine)
        
        # Add type-specific routers
        from myapp.routers import vm_router, disk_router
        app.include_router(vm_router)
        app.include_router(disk_router)
        
        return app
    
    def run(self, host="0.0.0.0", port=8003):
        provider_mode = os.getenv("PROVIDER_MODE", "api")
        self._validate_and_log_config(host, port, provider_mode)
        
        if provider_mode == "api":
            if not self.app:
                self.app = self.create_app()
            uvicorn.run(self.app, host=host, port=port)

# Usage
if __name__ == "__main__":
    server = ComputeProviderServer()
    server.run()
```

### Minimal Gateway Application

```python
from itl_controlplane_sdk.fastapi import AppFactory

factory = AppFactory("ControlPlane API Gateway", "1.0.0")
app = factory.create_app(
    cors_origins=["https://ui.example.com"],
    add_exception_handlers=True,
    add_logging_middleware=True
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
```

## Migration Guide

### From Deprecated on_event to Lifespan

**Before (Deprecated):**
```python
@app.on_event("startup")
async def startup():
    await initialize_database()

@app.on_event("shutdown")
async def shutdown():
    await close_database()
```

**After (Modern - FastAPI 0.93+):**
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await initialize_database()
    yield
    # Shutdown
    await close_database()

factory = AppFactory("MyApp", "1.0.0")
app = factory.create_app(lifespan=lifespan)
```

### From Custom Setup to Provider Server

**Before:**
```python
# Lots of boilerplate in main.py
app = FastAPI(title="Provider")
app.add_middleware(...)
# ... setup audit
# ... register resources
# ... define routes
# ... handle startup/shutdown
```

**After:**
```python
from itl_controlplane_sdk.fastapi import BaseProviderServer

class MyProvider(BaseProviderServer):
    def __init__(self):
        # Minimal setup
        self.engine = SQLAlchemyStorageEngine()
        self.provider = MyProvider(engine=self.engine)
        self.registry = ResourceProviderRegistry()
        self.app = None
        self.audit_publisher = None
    
    def create_app(self):
        # Use utilities for standard setup
        add_audit_middleware(app)
        setup_standard_openapi_tags(app)
        register_resource_types(self.registry, "ITL.Domain", self.provider, types)
        setup_generic_routes(app)
        setup_observability_routes(app, self.engine)
```

## Testing

```python
from fastapi.testclient import TestClient
from itl_controlplane_sdk.fastapi import AppFactory

factory = AppFactory("Test App", "1.0.0")
app = factory.create_app()
client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_observability():
    response = client.post("/admin/neo4j-sync")
    assert response.status_code == 200
```

## Best Practices

1. **Use AppFactory** for all FastAPI applications in ControlPlane
2. **Use BaseProviderServer** as base class for resource providers
3. **Use lifespan parameter** instead of deprecated on_event
4. **Use provider setup utilities** for consistent configuration
5. **Register resource types** with register_resource_types()
6. **Setup observability routes** for all providers
7. **Keep routers separate** from app creation
8. **Test with TestClient** from fastapi
9. **Use FastAPIConfig** for environment-specific configuration

## Future Enhancements

Potential additions to fastapi module:
- OpenTelemetry tracing support
- Prometheus metrics middleware
- Request ID propagation
- Rate limiting middleware
- Authentication/authorization patterns
- Dependency injection helpers
