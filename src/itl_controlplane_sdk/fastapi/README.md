# FastAPI Module: itl_controlplane_sdk.fastapi

Reusable FastAPI utilities for building applications in the ITL ControlPlane ecosystem.

Provides:
- **AppFactory**: Simplified FastAPI app creation with common setup
- **Middleware**: Logging, error handling, CORS configuration
- **Routes**: Standard health checks
- **Models**: Common request/response types
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

# Add app-specific startup/shutdown
@app.on_event("startup")
async def startup():
    await initialize_database()
    await initialize_message_broker()
```

### Provider Server

```python
from itl_controlplane_sdk.fastapi import AppFactory

factory = AppFactory("Keycloak Provider", "1.0.0")
app = factory.create_app(
    cors_origins=["*"]
)

@app.on_event("startup")
async def startup():
    await initialize_keycloak()
```

## Components

### AppFactory

Creates a configured FastAPI application with:
- CORS middleware
- Logging middleware
- Global exception handlers
- Health check routes
- OpenAPI documentation

**Options:**
- `routers`: List of APIRouter instances
- `cors_origins`: CORS allowed origins
- `add_health_routes`: Include /health and /ready endpoints
- `add_exception_handlers`: Install global exception handlers
- `add_logging_middleware`: Add request/response logging

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
Configured by AppFactory. Customize with `CORSConfig`:

```python
from itl_controlplane_sdk.fastapi.middleware.cors import CORSConfig

# Production config
config = CORSConfig.production("https://app.example.com")

# Development config (allow all)
config = CORSConfig.development()
```

### Routes

#### Health Checks
Standard endpoints for all applications:

- `GET /health` - Liveness probe (returns 200)
- `GET /ready` - Readiness probe (returns 200)

Both return:
```json
{
  "status": "ok/ready",
  "timestamp": "2024-01-31T12:34:56"
}
```

Can be disabled with `add_health_routes=False` if you need custom health checks.

### Models

Common Pydantic models for standardized responses:

- `ErrorResponse`: Error with code and details
- `HealthResponse`: Health check response
- `PaginatedResponse`: Paginated list results
- `MessageResponse`: Simple message

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
- `enable_metrics`: Enable metrics collection
- `enable_tracing`: Enable request tracing

## File Structure

```
src/itl_controlplane_sdk/fastapi/
├── __init__.py                 # Exports AppFactory, FastAPIConfig
├── app_factory.py              # Main factory class
├── config.py                   # Configuration management
├── models.py                   # Common request/response models
├── middleware/
│   ├── __init__.py
│   ├── logging.py              # Request/response logging
│   ├── error_handling.py       # Exception handlers
│   └── cors.py                 # CORS configuration
└── routes/
    ├── __init__.py
    └── health.py               # Health check endpoints
```

## Examples

### Full API Gateway

```python
from fastapi import APIRouter
from itl_controlplane_sdk.fastapi import AppFactory
from itl_controlplane_sdk.registry import resource_registry

# Create routers
resource_router = APIRouter()
provider_router = APIRouter()

@resource_router.get("/resources/{resource_id}")
async def get_resource(resource_id: str):
    return {"id": resource_id}

# Create app
factory = AppFactory("ControlPlane API", "1.0.0")
app = factory.create_app(
    routers=[resource_router, provider_router],
    cors_origins=["https://ui.example.com"]
)

# App-specific setup
@app.on_event("startup")
async def startup():
    # Initialize services
    logger.info("API Gateway started")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Resource Provider

```python
from itl_controlplane_sdk.fastapi import AppFactory

factory = AppFactory("Keycloak Provider", "1.0.0")
app = factory.create_app(
    cors_origins=["*"],
    add_health_routes=True
)

@app.on_event("startup")
async def startup():
    # Connect to Keycloak
    logger.info("Keycloak Provider started")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
```

## Migration Guide

### From Custom Middleware to FastAPI Module

**Before:**
```python
# src/server.py - lots of boilerplate
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .middleware.logging import LoggingMiddleware

app = FastAPI(title="My API")
app.add_middleware(CORSMiddleware, allow_origins=["*"])
app.add_middleware(LoggingMiddleware)
# ... setup exception handlers
# ... include routers
# ... define startup/shutdown
```

**After:**
```python
# src/server.py - clean and simple
from itl_controlplane_sdk.fastapi import AppFactory

factory = AppFactory("My API", "1.0.0")
app = factory.create_app(routers=[...])

@app.on_event("startup")
async def startup():
    # Only app-specific setup here
    pass
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
```

## Troubleshooting

### "Import 'fastapi' could not be resolved"
Install with FastAPI support:
```bash
pip install itl-controlplane-sdk[fastapi]
```

### Custom Exception Not Caught
Register custom exception handler after creating app:
```python
from itl_controlplane_sdk.fastapi.middleware.error_handling import APIError

@app.exception_handler(CustomError)
async def custom_handler(request, exc):
    return JSONResponse(status_code=400, content={"error": str(exc)})
```

### Disable Default Health Routes
```python
app = factory.create_app(add_health_routes=False)

# Then add custom health checks
@app.get("/health")
async def custom_health():
    # Your logic
    pass
```

## Best Practices

1. **Use AppFactory** for all FastAPI applications in ControlPlane
2. **Extend with startup/shutdown** for app-specific initialization
3. **Use FastAPIConfig** for environment-specific configuration
4. **Leverage error models** for consistent error responses
5. **Keep routers separate** from app creation
6. **Test with TestClient** from fastapi

## Future Enhancements

Potential additions to fastapi module:
- OpenTelemetry tracing support
- Prometheus metrics middleware
- Request ID propagation
- Rate limiting middleware
- Authentication/authorization patterns
- Dependency injection helpers
