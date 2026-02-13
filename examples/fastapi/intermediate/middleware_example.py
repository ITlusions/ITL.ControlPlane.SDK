"""
Middleware Example - Logging and Error Handling

Demonstrates the SDK's middleware components:
1. LoggingMiddleware - Request/response logging with timing
2. Error handling - APIError, ValueError, KeyError, generic exceptions
3. Combining middleware in a FastAPI app
4. Custom error responses with structured format
5. Practical patterns for production APIs

These middleware components provide consistent logging and error
handling across all ITL ControlPlane APIs.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, FastAPI, Request, Query
from fastapi.responses import JSONResponse

from itl_controlplane_sdk.api import AppFactory, FastAPIConfig
from itl_controlplane_sdk.api.middleware.logging import LoggingMiddleware
from itl_controlplane_sdk.api.middleware.error_handling import (
    APIError,
    setup_exception_handlers,
)


# ============================================================================
# EXAMPLE 1: APIError for structured error responses
# ============================================================================

def example_1_api_errors():
    """Demonstrate structured API error creation."""
    print("=" * 60)
    print("EXAMPLE 1: Structured API Errors")
    print("=" * 60)

    # 404 Not Found
    not_found = APIError(
        status_code=404,
        code="RESOURCE_NOT_FOUND",
        message="Virtual machine 'web-server-01' not found in resource group 'prod-rg'",
        details={
            "resource_type": "ITL.Compute/virtualMachines",
            "resource_name": "web-server-01",
            "resource_group": "prod-rg",
        },
    )
    print(f"\n404 Error:")
    print(f"   Status:  {not_found.status_code}")
    print(f"   Code:    {not_found.code}")
    print(f"   Message: {not_found.message}")
    print(f"   Details: {not_found.details}")

    # 400 Validation Error
    validation_err = APIError(
        status_code=400,
        code="VALIDATION_ERROR",
        message="Invalid VM size 'Standard_XYZ'",
        details={
            "field": "properties.vmSize",
            "value": "Standard_XYZ",
            "allowed": ["Standard_D2s_v3", "Standard_D4s_v3"],
        },
    )
    print(f"\n400 Error:")
    print(f"   Code:    {validation_err.code}")
    print(f"   Message: {validation_err.message}")

    # 409 Conflict
    conflict_err = APIError(
        status_code=409,
        code="RESOURCE_ALREADY_EXISTS",
        message="Resource group 'prod-rg' already exists in subscription 'sub-001'",
    )
    print(f"\n409 Error:")
    print(f"   Code:    {conflict_err.code}")
    print(f"   Message: {conflict_err.message}")

    # 500 Internal Error
    internal_err = APIError(
        status_code=500,
        code="INTERNAL_ERROR",
        message="Failed to connect to backend storage",
        details={"backend": "graph-db", "retry_after_seconds": 30},
    )
    print(f"\n500 Error:")
    print(f"   Code:    {internal_err.code}")
    print(f"   Details: {internal_err.details}")


# ============================================================================
# EXAMPLE 2: Build API routes that raise structured errors
# ============================================================================

def example_2_error_raising_routes():
    """Show how API routes should raise errors for consistent handling."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Routes with Error Handling")
    print("=" * 60)

    router = APIRouter(prefix="/api/v1", tags=["Resources"])

    @router.get("/resources/{name}")
    async def get_resource(name: str):
        """
        Get a resource by name.
        
        Exception handlers will automatically format errors:
        - APIError → structured response with code, message, details
        - ValueError → 400 Bad Request
        - KeyError → 404 Not Found
        - Exception → 500 Internal Server Error
        """
        # Simulated resource lookup
        resources = {
            "web-server": {"type": "vm", "size": "Standard_D2s_v3"},
            "prod-db": {"type": "vm", "size": "Standard_E4s_v3"},
        }

        if name not in resources:
            # Option 1: Raise APIError for detailed response
            raise APIError(
                status_code=404,
                code="RESOURCE_NOT_FOUND",
                message=f"Resource '{name}' not found",
                details={"searched_in": list(resources.keys())},
            )

        return {"name": name, **resources[name]}

    @router.post("/resources")
    async def create_resource(body: Dict[str, Any]):
        """Create a resource with validation."""
        if "name" not in body:
            # Option 2: Raise ValueError → auto-converted to 400
            raise ValueError("'name' is required in request body")

        if "location" not in body:
            raise ValueError("'location' is required")

        return {"name": body["name"], "provisioning_state": "Creating"}

    @router.delete("/resources/{name}")
    async def delete_resource(name: str):
        """Delete with not-found handling."""
        known = {"web-server", "prod-db"}
        if name not in known:
            # Option 3: Raise KeyError → auto-converted to 404
            raise KeyError(name)

        return {"name": name, "provisioning_state": "Deleting"}

    print(f"\nRoutes with error handling:")
    print(f"   GET    /api/v1/resources/{{name}}  → APIError(404) if not found")
    print(f"   POST   /api/v1/resources           → ValueError(400) if invalid")
    print(f"   DELETE /api/v1/resources/{{name}}  → KeyError(404) if not found")
    print(f"")
    print(f"Auto-handled exceptions:")
    print(f"   APIError   → status_code + {{error, code, request_id, timestamp, details}}")
    print(f"   ValueError → 400 + {{error, code: VALIDATION_ERROR, timestamp}}")
    print(f"   KeyError   → 404 + {{error: 'Resource not found: ...', code: NOT_FOUND}}")
    print(f"   Exception  → 500 + {{error: 'Internal server error', code: INTERNAL_ERROR}}")

    return router


# ============================================================================
# EXAMPLE 3: LoggingMiddleware output format
# ============================================================================

def example_3_logging_middleware():
    """Show what LoggingMiddleware logs for each request."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Logging Middleware")
    print("=" * 60)

    print(f"""
LoggingMiddleware logs for every request:

  Incoming request:
    → GET /api/v1/resources/web-server

  Outgoing response:
    ← GET /api/v1/resources/web-server [200] (0.003s)

  Response headers added:
    X-Process-Time: 0.003

Log levels:
  DEBUG  → Incoming request details
  INFO   → Response with status code and timing

Configuration:
  Enabled by default in AppFactory.create_app()
  Disable with: add_logging_middleware=False
""")


# ============================================================================
# EXAMPLE 4: Complete app with all middleware
# ============================================================================

def example_4_complete_app():
    """Build a complete API with logging + error handling middleware."""
    print("=" * 60)
    print("EXAMPLE 4: Complete App with All Middleware")
    print("=" * 60)

    # Create router with routes that exercise error handling
    demo_router = APIRouter(prefix="/api/v1", tags=["Demo"])

    @demo_router.get("/vms/{name}")
    async def get_vm(name: str):
        vms = {"web-01": {"size": "D2s_v3"}, "db-01": {"size": "E4s_v3"}}
        if name not in vms:
            raise APIError(404, "VM_NOT_FOUND", f"VM '{name}' not found")
        return {"name": name, **vms[name]}

    @demo_router.post("/vms")
    async def create_vm(body: Dict[str, Any]):
        if not body.get("name"):
            raise ValueError("VM name is required")
        return {"name": body["name"], "state": "Creating"}

    # Create app with full middleware stack
    factory = AppFactory("Middleware Demo API", version="1.0.0")
    app = factory.create_app(
        routers=[demo_router],
        add_health_routes=True,        # /health and /ready
        add_exception_handlers=True,   # APIError, ValueError, KeyError handlers
        add_logging_middleware=True,    # Request/response logging with timing
        cors_origins=["https://portal.example.com"],
    )

    print(f"\nApp with full middleware stack:")
    print(f"   Title: {app.title}")
    print(f"")
    print(f"   Middleware stack (inside → outside):")
    print(f"   ┌─────────────────────────────────────────┐")
    print(f"   │  1. LoggingMiddleware                   │")
    print(f"   │     → Logs request/response + timing    │")
    print(f"   │     → Adds X-Process-Time header        │")
    print(f"   ├─────────────────────────────────────────┤")
    print(f"   │  2. CORSMiddleware                      │")
    print(f"   │     → Handles CORS preflight requests   │")
    print(f"   │     → Adds Access-Control-* headers     │")
    print(f"   ├─────────────────────────────────────────┤")
    print(f"   │  3. Exception Handlers                  │")
    print(f"   │     → APIError → structured JSON        │")
    print(f"   │     → ValueError → 400 Bad Request      │")
    print(f"   │     → KeyError → 404 Not Found          │")
    print(f"   │     → Exception → 500 Server Error      │")
    print(f"   └─────────────────────────────────────────┘")

    # Show all routes
    print(f"\nRoutes:")
    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            methods = ", ".join(route.methods - {"HEAD", "OPTIONS"})
            if methods:
                print(f"   {methods:6s} {route.path}")

    return app


# ============================================================================
# EXAMPLE 5: Error response format
# ============================================================================

def example_5_error_response_format():
    """Show the exact JSON format of error responses."""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Error Response Format")
    print("=" * 60)

    print(f"""
All errors follow this JSON structure:

  APIError (custom):
  {{
    "error": "Virtual machine 'web-01' not found",
    "code": "RESOURCE_NOT_FOUND",
    "request_id": "abc-123-def",
    "timestamp": "2026-02-07T10:30:00",
    "details": {{
      "resource_type": "ITL.Compute/virtualMachines",
      "resource_name": "web-01"
    }}
  }}

  ValueError (auto-converted to 400):
  {{
    "error": "VM name is required",
    "code": "VALIDATION_ERROR",
    "request_id": "abc-123-def",
    "timestamp": "2026-02-07T10:30:00"
  }}

  KeyError (auto-converted to 404):
  {{
    "error": "Resource not found: 'web-01'",
    "code": "NOT_FOUND",
    "request_id": "abc-123-def",
    "timestamp": "2026-02-07T10:30:00"
  }}

  Generic Exception (auto-converted to 500):
  {{
    "error": "Internal server error",
    "code": "INTERNAL_ERROR",
    "request_id": "abc-123-def",
    "timestamp": "2026-02-07T10:30:00"
  }}

Notes:
  - request_id comes from X-Request-ID header (if provided by client)
  - timestamp is UTC ISO 8601
  - details is optional (only for APIError)
  - Generic 500 errors hide internal details for security
""")


if __name__ == "__main__":
    example_1_api_errors()
    example_2_error_raising_routes()
    example_3_logging_middleware()
    example_4_complete_app()
    example_5_error_response_format()
    print("All Middleware examples completed!")
