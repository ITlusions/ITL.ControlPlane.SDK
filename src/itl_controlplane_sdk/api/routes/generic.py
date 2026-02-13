"""
Generic resource routes for ITL ControlPlane providers.

Provides standard CRUD endpoints for generic resource operations.
These are placeholder routes that dispatch to type-specific handlers.

Providers should override these with type-specific implementations
or use this as a fallback for unsupported resource types.
"""

import logging
from fastapi import FastAPI
from ..base.models import GenericResourceBase, GenericResourceRequest, GenericResourceResponse

logger = logging.getLogger(__name__)


def setup_generic_routes(app: FastAPI) -> None:
    """Setup generic / placeholder resource routes.
    
    Registers 4 standard CRUD endpoints that raise NotImplementedError.
    Providers should override these with type-specific implementations.
    
    Args:
        app: FastAPI application to register routes on
    
    Routes registered:
    - POST /resources/{resource_type}
    - GET /resources/{resource_type}
    - GET /resources/{resource_type}/{resource_name}
    - DELETE /resources/{resource_type}/{resource_name}
    """
    
    @app.post(
        "/resources/{resource_type}",
        summary="Create Resource",
        response_model=GenericResourceResponse,
        tags=["Resources"]
    )
    async def create_resource(resource_type: str, request: GenericResourceRequest):
        """Create a new resource - dispatches to type-specific handler
        
        **Note**: This is a placeholder route. Providers should implement
        type-specific creation logic in their own routes.
        """
        logger.info(f"POST /resources/{resource_type}")
        raise NotImplementedError("Use type-specific routes instead")
    
    @app.get(
        "/resources/{resource_type}/{resource_name}",
        summary="Get Resource",
        response_model=GenericResourceResponse,
        tags=["Resources"]
    )
    async def get_resource(resource_type: str, resource_name: str):
        """Get a specific resource by type and name
        
        **Note**: This is a placeholder route. Providers should implement
        type-specific retrieval logic in their own routes.
        """
        logger.info(f"GET /resources/{resource_type}/{resource_name}")
        raise NotImplementedError("Use type-specific routes instead")
    
    @app.get(
        "/resources/{resource_type}",
        summary="List Resources",
        tags=["Resources"]
    )
    async def list_resources(resource_type: str):
        """List all resources of a specific type
        
        **Note**: This is a placeholder route. Providers should implement
        type-specific listing logic in their own routes.
        """
        logger.info(f"GET /resources/{resource_type}")
        raise NotImplementedError("Use type-specific routes instead")
    
    @app.delete(
        "/resources/{resource_type}/{resource_name}",
        summary="Delete Resource",
        tags=["Resources"]
    )
    async def delete_resource(resource_type: str, resource_name: str):
        """Delete a specific resource by type and name
        
        **Note**: This is a placeholder route. Providers should implement
        type-specific deletion logic in their own routes.
        """
        logger.info(f"DELETE /resources/{resource_type}/{resource_name}")
        raise NotImplementedError("Use type-specific routes instead")
