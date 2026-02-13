"""
Schema Discovery and Publishing for Resource Providers.

Provides automatic schema discovery endpoints and registry for resource types.
Enables clients to discover available resources, their schemas, and examples.
"""

from typing import Dict, Type, Any, List, Optional, Callable
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class ResourceTypeSchema:
    """Container for a resource type's schema information."""
    
    def __init__(
        self,
        name: str,
        short_name: str,
        description: str,
        api_versions: List[str],
        request_model: Type[BaseModel],
        response_model: Type[BaseModel],
        operations: List[str] = None,
        scope: str = "resource_group",
        examples_fn: Optional[Callable] = None
    ):
        """
        Initialize resource type schema.
        
        Args:
            name: Full resource type name (e.g., "ITL.Core/resourcegroups")
            short_name: Short reference name (e.g., "resourcegroups")
            description: Human-readable description
            api_versions: Supported API versions
            request_model: Pydantic model for requests
            response_model: Pydantic model for responses
            operations: List of supported operations (create, read, update, delete, list)
            scope: Resource scope (resource_group, subscription, global)
            examples_fn: Optional callable that returns examples dict
        """
        self.name = name
        self.short_name = short_name
        self.description = description
        self.api_versions = api_versions or ["2024-01-01"]
        self.request_model = request_model
        self.response_model = response_model
        self.operations = operations or ["create", "read", "update", "delete", "list"]
        self.scope = scope
        self.examples_fn = examples_fn
    
    def get_request_schema(self) -> Dict[str, Any]:
        """Get JSON schema for request body."""
        return self.request_model.model_json_schema()
    
    def get_response_schema(self) -> Dict[str, Any]:
        """Get JSON schema for response body."""
        return self.response_model.model_json_schema()
    
    def get_examples(self) -> Dict[str, Any]:
        """Get usage examples."""
        if self.examples_fn:
            return self.examples_fn()
        
        # Auto-generate from schema examples if available
        request_schema = self.get_request_schema()
        response_schema = self.get_response_schema()
        
        return {
            "create_request": {
                "method": "POST",
                "description": f"Create {self.short_name}",
                "body": request_schema.get("example", {})
            },
            "list_response": {
                "method": "GET",
                "description": f"List {self.short_name}",
                "response": {
                    "value": [response_schema.get("example", {})]
                }
            },
            "get_response": {
                "method": "GET",
                "description": f"Get a {self.short_name}",
                "response": response_schema.get("example", {})
            }
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "name": self.name,
            "short_name": self.short_name,
            "description": self.description,
            "apiVersions": self.api_versions,
            "operations": self.operations,
            "scope": self.scope,
            "schema_url": f"/schemas/{self.short_name}",
            "request_schema_url": f"/schemas/{self.short_name}/request",
            "response_schema_url": f"/schemas/{self.short_name}/response",
            "examples_url": f"/schemas/{self.short_name}/examples"
        }


class SchemaRegistry:
    """Registry of all resource type schemas."""
    
    def __init__(self):
        """Initialize empty registry."""
        self._schemas: Dict[str, ResourceTypeSchema] = {}
    
    def register(self, schema: ResourceTypeSchema) -> None:
        """
        Register a resource type schema.
        
        Args:
            schema: ResourceTypeSchema instance
        """
        self._schemas[schema.short_name.lower()] = schema
        logger.info(f"Registered schema for {schema.name}")
    
    def register_multiple(self, schemas: List[ResourceTypeSchema]) -> None:
        """Register multiple schemas."""
        for schema in schemas:
            self.register(schema)
    
    def get(self, resource_type: str) -> Optional[ResourceTypeSchema]:
        """Get schema by short name."""
        return self._schemas.get(resource_type.lower())
    
    def list_all(self) -> List[ResourceTypeSchema]:
        """Get all registered schemas."""
        return list(self._schemas.values())
    
    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """Convert registry to dict for API responses."""
        return {
            schema.short_name: schema.to_dict()
            for schema in self._schemas.values()
        }


def create_schema_routes(app: FastAPI, registry: SchemaRegistry) -> None:
    """
    Create and register schema discovery endpoints.
    
    Endpoints added:
    - GET /schemas — List all resource types
    - GET /schemas/{resource_type} — Combined request + response schema
    - GET /schemas/{resource_type}/request — Request schema only
    - GET /schemas/{resource_type}/response — Response schema only
    - GET /schemas/{resource_type}/examples — Usage examples
    
    Args:
        app: FastAPI application instance
        registry: SchemaRegistry instance with registered schemas
    """
    
    @app.get(
        "/schemas",
        summary="List Available Resource Types",
        description="Discover all resource types provided by this provider.",
        tags=["Schema Discovery"],
        include_in_schema=True,
    )
    async def list_schemas() -> Dict[str, Dict[str, Any]]:
        """
        List all available resource type schemas.
        
        Returns a map of resource type short name → schema metadata.
        """
        return registry.to_dict()
    
    @app.get(
        "/schemas/{resource_type}",
        summary="Get Resource Type Schema",
        description="Get complete schema for a resource type (request + response).",
        tags=["Schema Discovery"],
    )
    async def get_combined_schema(resource_type: str) -> Dict[str, Any]:
        """
        Get combined schema (request + response + metadata).
        
        Returns:
            {
              "resourceType": "ITL.Core/subscriptions",
              "apiVersions": ["2024-01-01"],
              "description": "...",
              "request": { ... JSON Schema ... },
              "response": { ... JSON Schema ... },
              "metadata": { ...}
            }
        """
        schema = registry.get(resource_type)
        if not schema:
            raise HTTPException(
                status_code=404,
                detail=f"Schema not found for resource type: {resource_type}"
            )
        
        return {
            "resourceType": schema.name,
            "apiVersions": schema.api_versions,
            "description": schema.description,
            "scope": schema.scope,
            "request": schema.get_request_schema(),
            "response": schema.get_response_schema(),
            "metadata": {
                "operations": schema.operations,
            }
        }
    
    @app.get(
        "/schemas/{resource_type}/request",
        summary="Get Request Schema",
        description="Get JSON Schema for request body to this resource type.",
        tags=["Schema Discovery"],
    )
    async def get_request_schema(resource_type: str) -> Dict[str, Any]:
        """Get request schema only (what clients should send)."""
        schema = registry.get(resource_type)
        if not schema:
            raise HTTPException(status_code=404, detail=f"Schema not found for {resource_type}")
        return schema.get_request_schema()
    
    @app.get(
        "/schemas/{resource_type}/response",
        summary="Get Response Schema",
        description="Get JSON Schema for response body from this resource type.",
        tags=["Schema Discovery"],
    )
    async def get_response_schema(resource_type: str) -> Dict[str, Any]:
        """Get response schema only (what clients will receive)."""
        schema = registry.get(resource_type)
        if not schema:
            raise HTTPException(status_code=404, detail=f"Schema not found for {resource_type}")
        return schema.get_response_schema()
    
    @app.get(
        "/schemas/{resource_type}/examples",
        summary="Get Request/Response Examples",
        description="Get real-world examples of using this resource type.",
        tags=["Schema Discovery"],
    )
    async def get_examples(resource_type: str) -> Dict[str, Any]:
        """Get usage examples for the resource type."""
        schema = registry.get(resource_type)
        if not schema:
            raise HTTPException(status_code=404, detail=f"Examples not found for {resource_type}")
        return schema.get_examples()


__all__ = [
    "ResourceTypeSchema",
    "SchemaRegistry",
    "create_schema_routes",
]
