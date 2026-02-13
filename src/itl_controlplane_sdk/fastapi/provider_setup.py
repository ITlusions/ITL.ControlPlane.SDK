"""
Middleware and provider setup utilities for ITL ControlPlane.

Provides common setup functions for audit middleware, provider registration,
and other standardized configurations.
"""

import logging
from typing import List
from fastapi import FastAPI
from itl_controlplane_sdk.persistence.audit import AuditContextMiddleware
from itl_controlplane_sdk.providers import ResourceProviderRegistry

logger = logging.getLogger(__name__)


def add_audit_middleware(app: FastAPI, extract_actor_from_jwt: bool = True) -> None:
    """Add audit context middleware to the FastAPI application.
    
    The audit context middleware captures request metadata (actor, scope, action)
    for audit logging and compliance tracking.
    
    Args:
        app: FastAPI application to add middleware to
        extract_actor_from_jwt: Whether to extract actor ID from JWT token (default True)
    """
    app.add_middleware(
        AuditContextMiddleware,
        extract_actor_from_jwt=extract_actor_from_jwt
    )
    logger.debug("Added audit context middleware")


def setup_standard_openapi_tags(app: FastAPI) -> None:
    """Setup standard OpenAPI tags for resource providers.
    
    Registers the standard tag groupings used across all resource providers
    for consistent API documentation.
    
    Args:
        app: FastAPI application to configure
    
    Tags:
    - Resources: Resource CRUD and management operations
    - System: System health, readiness, and infrastructure checks
    - Infrastructure: Infrastructure monitoring and telemetry
    """
    app.openapi_tags = [
        {
            "name": "Resources",
            "description": "Resource management operations (CRUD)"
        },
        {
            "name": "System",
            "description": "System health and readiness checks"
        },
        {
            "name": "Infrastructure",
            "description": "Infrastructure monitoring and observability"
        },
    ]
    logger.debug("Setup standard OpenAPI tags")


def register_resource_types(
    registry: ResourceProviderRegistry,
    provider_namespace: str,
    provider_instance,
    resource_types: List[str]
) -> None:
    """Register resource types with the provider registry.
    
    Registers a list of resource types for a given provider namespace,
    enabling the discovery and routing of provider endpoints.
    
    Args:
        registry: ResourceProviderRegistry instance
        provider_namespace: Namespace (e.g., "ITL.Core", "ITL.Compute")
        provider_instance: The ResourceProvider instance handling these types
        resource_types: List of resource type names (e.g., ["subscriptions", "resourcegroups"])
    """
    for resource_type in resource_types:
        registry.register_provider(provider_namespace, resource_type, provider_instance)
    logger.info(f"Registered {len(resource_types)} resource types for {provider_namespace}")
