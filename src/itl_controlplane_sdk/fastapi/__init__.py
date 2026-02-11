"""
FastAPI utilities for ITL ControlPlane SDK

Provides factory, middleware, and common patterns for building FastAPI applications
in the ITL ControlPlane ecosystem (API gateway and resource providers).
"""

from .app_factory import AppFactory
from .config import FastAPIConfig
from .crud_routes import create_crud_routes
from .generic_routes import setup_generic_routes
from .models import GenericResourceBase
from .observability_routes import setup_observability_routes
from .provider_server import BaseProviderServer
from .provider_setup import (
    add_audit_middleware,
    setup_standard_openapi_tags,
    register_resource_types,
)
from .schema_discovery import (
    ResourceTypeSchema,
    SchemaRegistry,
    create_schema_routes,
)

__all__ = [
    "AppFactory",
    "add_audit_middleware",
    "BaseProviderServer",
    "create_crud_routes",
    "GenericResourceBase",
    "register_resource_types",
    "setup_generic_routes",
    "setup_observability_routes",
    "setup_standard_openapi_tags",
    "ResourceTypeSchema",
    "SchemaRegistry",
    "create_schema_routes",
]
