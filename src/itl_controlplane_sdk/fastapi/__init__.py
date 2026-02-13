"""
FastAPI utilities for ITL ControlPlane SDK

Provides factory, middleware, and common patterns for building FastAPI applications
in the ITL ControlPlane ecosystem (API gateway and resource providers).

Module structure:
    base/          - App factory, configuration, models
    providers/     - Provider server base class and setup utilities
    routes/        - HTTP route handlers (health, CRUD, observability, schema)
    middleware/    - Logging and error handling middleware
    utilities/     - Schema discovery and other utility functions
"""

from .base import (
    AppFactory,
    FastAPIConfig,
)
from .base.models import GenericResourceBase
from .providers import (
    BaseProviderServer,
    add_audit_middleware,
    setup_standard_openapi_tags,
    register_resource_types,
)
from .routes.crud import create_crud_routes
from .routes.generic import setup_generic_routes
from .routes.observability import setup_observability_routes
from .utilities import (
    discover_resource_schema,
    get_operation_schema,
    create_schema_routes,
)

__all__ = [
    "AppFactory",
    "add_audit_middleware",
    "BaseProviderServer",
    "create_crud_routes",
    "create_schema_routes",
    "discover_resource_schema",
    "FastAPIConfig",
    "GenericResourceBase",
    "get_operation_schema",
    "register_resource_types",
    "setup_generic_routes",
    "setup_observability_routes",
    "setup_standard_openapi_tags",
]
