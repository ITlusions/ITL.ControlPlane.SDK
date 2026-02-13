"""
FastAPI App Factory Example

Demonstrates building a complete API application using the SDK's AppFactory:
1. Creating a FastAPI app with AppFactory
2. Adding custom routers
3. CORS configuration (dev vs production)
4. Health check routes (/health, /ready)
5. Lifecycle events (startup/shutdown)
6. FastAPIConfig presets

The AppFactory provides a consistent way to build APIs with
standard middleware, error handling, and health checks.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from datetime import datetime

from itl_controlplane_sdk.api import AppFactory, FastAPIConfig


# ============================================================================
# STEP 1: Define your custom API routers
# ============================================================================

# --- Resources Router ---
resources_router = APIRouter(prefix="/api/v1/resources", tags=["Resources"])


@resources_router.get("/")
async def list_resources(
    subscription_id: str = Query(..., description="Subscription ID"),
    resource_group: str = Query(None, description="Optional resource group filter"),
):
    """List all resources, optionally filtered by resource group."""
    resources = [
        {"name": "web-server-01", "type": "ITL.Compute/virtualMachines", "location": "westeurope"},
        {"name": "prod-db", "type": "ITL.Compute/virtualMachines", "location": "westeurope"},
        {"name": "proddata", "type": "ITL.Storage/storageAccounts", "location": "westeurope"},
    ]
    if resource_group:
        # Filter simulation
        resources = [r for r in resources if True]  # No-op filter for demo
    return {"value": resources, "subscription_id": subscription_id}


@resources_router.get("/{resource_name}")
async def get_resource(resource_name: str):
    """Get a specific resource by name."""
    return {
        "name": resource_name,
        "type": "ITL.Compute/virtualMachines",
        "location": "westeurope",
        "properties": {"vmSize": "Standard_D2s_v3", "osType": "Linux"},
        "provisioning_state": "Succeeded",
    }


@resources_router.post("/")
async def create_resource(body: Dict[str, Any]):
    """Create a new resource."""
    return {
        "name": body.get("name", "unnamed"),
        "provisioning_state": "Creating",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


# --- Subscriptions Router ---
subscriptions_router = APIRouter(prefix="/api/v1/subscriptions", tags=["Subscriptions"])


@subscriptions_router.get("/")
async def list_subscriptions():
    """List all subscriptions."""
    return {
        "value": [
            {"id": "sub-001", "name": "Production", "state": "Active"},
            {"id": "sub-002", "name": "Development", "state": "Active"},
        ]
    }


# ============================================================================
# EXAMPLE 1: Basic app creation with AppFactory
# ============================================================================

def example_1_basic_app():
    """Create a basic FastAPI app with standard features."""
    print("=" * 60)
    print("EXAMPLE 1: Basic App Factory Usage")
    print("=" * 60)

    # Create factory
    factory = AppFactory("ITL Control Plane API", version="1.0.0")

    # Create app with all defaults
    app = factory.create_app(
        routers=[resources_router, subscriptions_router],
    )

    print(f"\nApp created:")
    print(f"   Title:   {app.title}")
    print(f"   Version: {app.version}")
    print(f"   Docs:    /docs (Swagger UI)")
    print(f"   ReDoc:   /redoc")
    print(f"   OpenAPI: /openapi.json")

    # List registered routes
    print(f"\nRegistered routes:")
    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            methods = ", ".join(route.methods - {"HEAD", "OPTIONS"})
            if methods:
                print(f"   {methods:6s} {route.path}")

    return app


# ============================================================================
# EXAMPLE 2: Development vs Production configuration
# ============================================================================

def example_2_environment_configs():
    """Show different configurations for dev and production."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Environment-Specific Configuration")
    print("=" * 60)

    # --- Development config ---
    dev_config = FastAPIConfig.development()
    print(f"\nDevelopment config:")
    print(f"   CORS origins:  {dev_config.cors_origins}")
    print(f"   Log level:     {dev_config.log_level}")
    print(f"   Metrics:       {dev_config.enable_metrics}")
    print(f"   Tracing:       {dev_config.enable_tracing}")

    dev_factory = AppFactory("Dev API", version="0.1.0-dev", config=dev_config)
    dev_app = dev_factory.create_app(
        routers=[resources_router],
        docs_url="/docs",
    )
    print(f"   App title: {dev_app.title}")

    # --- Production config ---
    prod_config = FastAPIConfig.production()
    print(f"\nProduction config:")
    print(f"   CORS origins:  {prod_config.cors_origins}")
    print(f"   Log level:     {prod_config.log_level}")
    print(f"   Metrics:       {prod_config.enable_metrics}")
    print(f"   Tracing:       {prod_config.enable_tracing}")

    prod_factory = AppFactory("Prod API", version="1.0.0", config=prod_config)
    prod_app = prod_factory.create_app(
        routers=[resources_router, subscriptions_router],
        cors_origins=["https://portal.mycompany.com", "https://admin.mycompany.com"],
        docs_url=None,  # Disable Swagger UI in production
        redoc_url=None,  # Disable ReDoc in production
    )
    print(f"   App title: {prod_app.title}")
    print(f"   Docs:      Disabled (production)")

    # --- Custom config ---
    custom_config = FastAPIConfig(
        cors_origins=["https://staging.mycompany.com"],
        cors_credentials=True,
        log_level="INFO",
        enable_metrics=True,
        enable_tracing=False,
    )
    print(f"\nCustom config:")
    print(f"   CORS origins: {custom_config.cors_origins}")
    print(f"   Log level:    {custom_config.log_level}")


# ============================================================================
# EXAMPLE 3: App with lifecycle events
# ============================================================================

def example_3_lifecycle_events():
    """Create app with startup and shutdown event handlers."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Lifecycle Events")
    print("=" * 60)

    # Define startup handler
    async def on_startup():
        """Initialize database connections, caches, etc."""
        print("   App starting up...")
        print("   Connecting to database...")
        print("   Initializing identity provider...")

    # Define shutdown handler
    async def on_shutdown():
        """Clean up resources."""
        print("   Shutting down...")
        print("   Closing database connections...")
        print("   Disconnecting identity provider...")

    factory = AppFactory("Lifecycle Demo", version="1.0.0")
    app = factory.create_app(
        routers=[resources_router],
        custom_startup=on_startup,
        custom_shutdown=on_shutdown,
    )

    print(f"\nApp with lifecycle events created:")
    print(f"   Startup handler:  registered")
    print(f"   Shutdown handler: registered")
    print(f"   These run automatically when uvicorn starts/stops")

    return app


# ============================================================================
# EXAMPLE 4: Selective feature toggles
# ============================================================================

def example_4_feature_toggles():
    """Create app with specific features enabled/disabled."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Feature Toggles")
    print("=" * 60)

    factory = AppFactory("Minimal API", version="1.0.0")

    # Minimal app: no health routes, no logging, no error handlers
    minimal_app = factory.create_app(
        routers=[resources_router],
        add_health_routes=False,
        add_exception_handlers=False,
        add_logging_middleware=False,
    )
    print(f"\nMinimal app (everything off):")
    print(f"   Health routes:     disabled")
    print(f"   Exception handlers: disabled")
    print(f"   Logging middleware: disabled")

    # Full-featured app
    full_app = factory.create_app(
        routers=[resources_router, subscriptions_router],
        add_health_routes=True,
        add_exception_handlers=True,
        add_logging_middleware=True,
        cors_origins=["https://portal.example.com"],
    )
    print(f"\nFull-featured app (everything on):")
    print(f"   Health routes:     enabled (/health, /ready)")
    print(f"   Exception handlers: enabled")
    print(f"   Logging middleware: enabled")
    print(f"   CORS:              ['https://portal.example.com']")


# ============================================================================
# EXAMPLE 5: Running the app
# ============================================================================

def example_5_how_to_run():
    """Show how to run the created app with uvicorn."""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Running the App")
    print("=" * 60)

    print(f"""
To run a FastAPI app created with AppFactory:

    # In your main.py:
    from itl_controlplane_sdk.api import AppFactory
    
    factory = AppFactory("My API", version="1.0.0")
    app = factory.create_app(routers=[my_router])

    # Run with uvicorn:
    # uvicorn main:app --host 0.0.0.0 --port 8000 --reload

    # Or programmatically:
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

Built-in endpoints:
    GET  /health      → {{"status": "healthy", "timestamp": "..."}}
    GET  /ready       → {{"ready": true, "timestamp": "..."}}
    GET  /docs        → Swagger UI
    GET  /redoc       → ReDoc
    GET  /openapi.json → OpenAPI schema
""")


if __name__ == "__main__":
    example_1_basic_app()
    example_2_environment_configs()
    example_3_lifecycle_events()
    example_4_feature_toggles()
    example_5_how_to_run()
    print("All FastAPI App Factory examples completed!")
