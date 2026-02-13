"""
FastAPI routes for ITL ControlPlane.

Provides standard CRUD, health, observability, metadata, and schema discovery routes.
"""

from .health import router as health_router
from .crud import create_crud_routes
from .generic import setup_generic_routes
from .observability import setup_observability_routes
from .metadata import create_metadata_router

__all__ = [
    "health_router",
    "create_crud_routes",
    "setup_generic_routes",
    "setup_observability_routes",
    "create_metadata_router",
]
