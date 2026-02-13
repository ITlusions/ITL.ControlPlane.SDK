"""
FastAPI utility functions.

Provides schema discovery and other utility functions.
"""

from .schema_discovery import (
    discover_resource_schema,
    get_operation_schema,
    create_schema_routes,
)

__all__ = [
    "create_schema_routes",
    "discover_resource_schema",
    "get_operation_schema",
]
