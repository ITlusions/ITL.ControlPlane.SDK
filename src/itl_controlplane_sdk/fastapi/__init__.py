"""
FastAPI utilities for ITL ControlPlane SDK

Thin alias of itl_controlplane_sdk.api — exists for callers that import from
itl_controlplane_sdk.fastapi directly (this package's own name matches the
"fastapi" extra). Re-exports the real implementation rather than duplicating
it; this module's own provider_server.py/provider_setup.py/routes/ are a
byte-identical, unused fork of api/providers/ kept only for backward
compatibility with any code importing those submodules by path directly.
"""

from itl_controlplane_sdk.api import (
    AppFactory,
    FastAPIConfig,
    GenericResourceBase,
    GenericResourceRequest,
    GenericResourceResponse,
    BaseProviderServer,
    add_audit_middleware,
    setup_standard_openapi_tags,
    register_resource_types,
    create_crud_routes,
    setup_generic_routes,
    setup_observability_routes,
    discover_resource_schema,
    get_operation_schema,
    create_schema_routes,
    ResourceTypeSchema,
    SchemaRegistry,
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
    "GenericResourceRequest",
    "GenericResourceResponse",
    "get_operation_schema",
    "register_resource_types",
    "ResourceTypeSchema",
    "SchemaRegistry",
    "setup_generic_routes",
    "setup_observability_routes",
    "setup_standard_openapi_tags",
]
