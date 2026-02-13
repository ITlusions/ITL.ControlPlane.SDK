"""
ITL ControlPlane SDK - Core Framework

This package provides the core framework for building resource providers
and managing cloud resources through a unified interface.

Install only what you need::

    pip install itl-controlplane-sdk            # core + providers
    pip install itl-controlplane-sdk[identity]   # + identity framework
    pip install itl-controlplane-sdk[fastapi]    # + FastAPI integration
    pip install itl-controlplane-sdk[pulumi]     # + Pulumi helpers
    pip install itl-controlplane-sdk[all]        # everything

Modules:
    core: Core models, exceptions, infrastructure definitions
    providers: Resource provider base classes and registry
    identity: Identity provider framework (Keycloak, Azure AD, etc.)
    fastapi: HTTP routing and middleware
    services: Application-layer service patterns
    pulumi: Pulumi IaC helpers
"""

from __future__ import annotations

import importlib as _importlib
from typing import TYPE_CHECKING

__version__ = "1.0.0"

# ---------------------------------------------------------------------------
# Eager imports: core + providers (always needed, small footprint)
# ---------------------------------------------------------------------------
from itl_controlplane_sdk.core import (
    # Models
    ResourceRequest,
    ResourceResponse,
    ResourceListResponse,
    ResourceMetadata,
    ErrorResponse,
    ProvisioningState,
    # Exceptions (simple)
    ResourceProviderError,
    ResourceNotFoundError,
    ResourceConflictError,
    # Exceptions (structured)
    ErrorCategory,
    ControlPlaneError,
    ConfigurationError,
    ValidationError,
    AuthorizationError,
    ProviderError as ProviderOperationError,
    TransientError,
    ExternalServiceError,
    CascadeDeletionError,
    TransactionError,
    # Infrastructure models
    ResourceGroup,
    ManagementGroup,
    Deployment,
    Subscription,
    Location,
    ExtendedLocation,
    Tag,
    Policy,
    ProviderConfiguration,
    # Constants
    DEFAULT_LOCATIONS,
    EXTENDED_LOCATIONS,
    PROVIDER_NAMESPACE,
    RESOURCE_TYPE_RESOURCE_GROUPS,
    RESOURCE_TYPE_MANAGEMENT_GROUPS,
    RESOURCE_TYPE_DEPLOYMENTS,
    RESOURCE_TYPE_SUBSCRIPTIONS,
    RESOURCE_TYPE_TAGS,
    RESOURCE_TYPE_POLICIES,
    RESOURCE_TYPE_LOCATIONS,
    RESOURCE_TYPE_EXTENDED_LOCATIONS,
    RESOURCE_TYPE_TENANTS,
    DEFAULT_TENANT_ID,
    ITL_RESOURCE_TYPES,
)

from itl_controlplane_sdk.providers import (
    ResourceProvider,
    ResourceProviderRegistry,
    resource_registry,
    ResourceIdentity,
    generate_resource_id,
    parse_resource_id,
    LocationsHandler,
    RegionMeta,
    ProviderServer,
)

# Service Bus utilities for message-based provider modes
from itl_controlplane_sdk.messaging.servicebus import (
    GenericServiceBusProvider,
    ProviderModeManager,
    run_generic_servicebus_provider,
)

# Auto-initialize Locations Handler with default locations
LocationsHandler.initialize()

# ---------------------------------------------------------------------------
# Lazy imports: identity, api, services, pulumi
# Loaded on first attribute access so consumers who only need core/providers
# don't pay the import cost (or need the optional dependencies).
# ---------------------------------------------------------------------------

# Maps attribute name -> (module_path, attribute_name_in_module)
_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # Identity framework
    "IdentityProvider":          ("itl_controlplane_sdk.identity", "IdentityProvider"),
    "IdentityProviderFactory":   ("itl_controlplane_sdk.identity", "IdentityProviderFactory"),
    "get_identity_factory":      ("itl_controlplane_sdk.identity", "get_factory"),
    "register_identity_provider":("itl_controlplane_sdk.identity", "register_provider"),
    # Tenant models
    "Tenant":                    ("itl_controlplane_sdk.identity", "Tenant"),
    "TenantSpec":                ("itl_controlplane_sdk.identity", "TenantSpec"),
    "TenantStatus":              ("itl_controlplane_sdk.identity", "TenantStatus"),
    "TenantResponse":            ("itl_controlplane_sdk.identity", "TenantResponse"),
    "TenantWithOrganizations":   ("itl_controlplane_sdk.identity", "TenantWithOrganizations"),
    # Organization models
    "Organization":              ("itl_controlplane_sdk.identity", "Organization"),
    "OrganizationSpec":          ("itl_controlplane_sdk.identity", "OrganizationSpec"),
    "OrganizationStatus":        ("itl_controlplane_sdk.identity", "OrganizationStatus"),
    "OrganizationResponse":      ("itl_controlplane_sdk.identity", "OrganizationResponse"),
    "OrganizationWithDomains":   ("itl_controlplane_sdk.identity", "OrganizationWithDomains"),
    "TenantAdminUser":           ("itl_controlplane_sdk.identity", "TenantAdminUser"),
    "TenantAdminRole":           ("itl_controlplane_sdk.identity", "TenantAdminRole"),
    "CustomDomain":              ("itl_controlplane_sdk.identity", "CustomDomain"),
    "DomainStatus":              ("itl_controlplane_sdk.identity", "DomainStatus"),
    "DomainVerificationMethod":  ("itl_controlplane_sdk.identity", "DomainVerificationMethod"),
    # Services
    "BaseResourceService":       ("itl_controlplane_sdk.providers.base", "BaseResourceService"),
    # Graph Database
    "MetadataService":           ("itl_controlplane_sdk.graphdb", "MetadataService"),
    "GraphDatabaseInterface":    ("itl_controlplane_sdk.graphdb", "GraphDatabaseInterface"),
    "InMemoryGraphDatabase":     ("itl_controlplane_sdk.graphdb", "InMemoryGraphDatabase"),
    "SQLGraphDatabase":          ("itl_controlplane_sdk.graphdb", "SQLGraphDatabase"),
    "SQLiteGraphDatabase":       ("itl_controlplane_sdk.graphdb", "SQLiteGraphDatabase"),
    "PostgresGraphDatabase":     ("itl_controlplane_sdk.graphdb", "PostgresGraphDatabase"),
    "create_graph_database":     ("itl_controlplane_sdk.graphdb", "create_graph_database"),
    "GraphNode":                 ("itl_controlplane_sdk.graphdb", "GraphNode"),
    "GraphRelationship":         ("itl_controlplane_sdk.graphdb", "GraphRelationship"),
    "NodeType":                  ("itl_controlplane_sdk.graphdb", "NodeType"),
    "RelationshipType":          ("itl_controlplane_sdk.graphdb", "RelationshipType"),
    "SubscriptionNode":          ("itl_controlplane_sdk.graphdb", "SubscriptionNode"),
    "ResourceGroupNode":         ("itl_controlplane_sdk.graphdb", "ResourceGroupNode"),
    "ResourceNode":              ("itl_controlplane_sdk.graphdb", "ResourceNode"),
    # Persistence (SQL data layer)
    "ResourceStore":             ("itl_controlplane_sdk.persistence", "ResourceStore"),
    "TupleResourceStore":        ("itl_controlplane_sdk.persistence", "TupleResourceStore"),
    "StorageBackend":            ("itl_controlplane_sdk.persistence", "StorageBackend"),
    # Messaging
    "MessageBroker":             ("itl_controlplane_sdk.messaging", "MessageBroker"),
    "InMemoryBroker":            ("itl_controlplane_sdk.messaging", "InMemoryBroker"),
    "MessageBrokerManager":      ("itl_controlplane_sdk.messaging", "MessageBrokerManager"),
}


def __getattr__(name: str):
    """Lazy-load optional modules on first access."""
    if name in _LAZY_IMPORTS:
        module_path, attr = _LAZY_IMPORTS[name]
        try:
            module = _importlib.import_module(module_path)
        except ImportError as exc:
            # Give a helpful message pointing to the correct extras install
            extra = _MODULE_TO_EXTRA.get(module_path, "")
            hint = (
                f"pip install itl-controlplane-sdk[{extra}]"
                if extra
                else f"pip install the required dependencies for {module_path}"
            )
            raise ImportError(
                f"'{name}' requires the '{module_path}' module. "
                f"Install it with: {hint}"
            ) from exc
        value = getattr(module, attr)
        # Cache on the module so __getattr__ is only called once per name
        globals()[name] = value
        return value
    raise AttributeError(f"module 'itl_controlplane_sdk' has no attribute {name!r}")


# Maps module path -> extras_require key (for error messages)
_MODULE_TO_EXTRA: dict[str, str] = {
    "itl_controlplane_sdk.identity": "identity",
    "itl_controlplane_sdk.api": "fastapi",
    "itl_controlplane_sdk.pulumi": "pulumi",
    "itl_controlplane_sdk.graphdb": "graphdb",
    "itl_controlplane_sdk.persistence": "persistence",
    "itl_controlplane_sdk.messaging": "messaging",
}

# For type checkers: make lazy imports visible without runtime cost
if TYPE_CHECKING:
    from itl_controlplane_sdk.identity import (
        IdentityProvider,
        IdentityProviderFactory,
        get_factory as get_identity_factory,
        register_provider as register_identity_provider,
        Tenant,
        TenantSpec,
        TenantStatus,
        TenantResponse,
        TenantWithOrganizations,
        Organization,
        OrganizationSpec,
        OrganizationStatus,
        OrganizationResponse,
        OrganizationWithDomains,
        TenantAdminUser,
        TenantAdminRole,
        CustomDomain,
        DomainStatus,
        DomainVerificationMethod,
    )
    from itl_controlplane_sdk.providers.base import BaseResourceService


__all__ = [
    # --- Eager: Core Models ---
    "ResourceRequest",
    "ResourceResponse",
    "ResourceListResponse",
    "ResourceMetadata",
    "ProvisioningState",
    # --- Eager: Exceptions ---
    "ResourceProviderError",
    "ResourceNotFoundError",
    "ResourceConflictError",
    "ErrorCategory",
    "ControlPlaneError",
    "ConfigurationError",
    "ValidationError",
    "AuthorizationError",
    "ProviderOperationError",
    "TransientError",
    "ExternalServiceError",
    "CascadeDeletionError",
    "TransactionError",
    # --- Eager: Infrastructure Models ---
    "ResourceGroup",
    "ManagementGroup",
    "Deployment",
    "Subscription",
    "Location",
    "ExtendedLocation",
    "Tag",
    "Policy",
    "ProviderConfiguration",
    # --- Eager: Constants ---
    "DEFAULT_LOCATIONS",
    "EXTENDED_LOCATIONS",
    "PROVIDER_NAMESPACE",
    "RESOURCE_TYPE_RESOURCE_GROUPS",
    "RESOURCE_TYPE_MANAGEMENT_GROUPS",
    "RESOURCE_TYPE_DEPLOYMENTS",
    "RESOURCE_TYPE_SUBSCRIPTIONS",
    "RESOURCE_TYPE_TAGS",
    "RESOURCE_TYPE_POLICIES",
    "RESOURCE_TYPE_LOCATIONS",
    "RESOURCE_TYPE_EXTENDED_LOCATIONS",
    "RESOURCE_TYPE_TENANTS",
    "DEFAULT_TENANT_ID",
    "ITL_RESOURCE_TYPES",
    # --- Eager: Providers ---
    "ResourceProvider",
    "ResourceProviderRegistry",
    "resource_registry",
    "ResourceIdentity",
    "generate_resource_id",
    "parse_resource_id",
    "LocationsHandler",
    "RegionMeta",
    "ProviderServer",
    # --- Lazy: Identity Framework ---
    "IdentityProvider",
    "IdentityProviderFactory",
    "get_identity_factory",
    "register_identity_provider",
    "Tenant",
    "TenantSpec",
    "TenantStatus",
    "TenantResponse",
    "TenantWithOrganizations",
    "Organization",
    "OrganizationSpec",
    "OrganizationStatus",
    "OrganizationResponse",
    "OrganizationWithDomains",
    "TenantAdminUser",
    "TenantAdminRole",
    "CustomDomain",
    "DomainStatus",
    "DomainVerificationMethod",
    # --- Lazy: Services ---
    "BaseResourceService",
    # --- Lazy: Graph Database ---
    "MetadataService",
    "GraphDatabaseInterface",
    "InMemoryGraphDatabase",
    "SQLGraphDatabase",
    "SQLiteGraphDatabase",
    "PostgresGraphDatabase",
    "create_graph_database",
    "GraphNode",
    "GraphRelationship",
    "NodeType",
    "RelationshipType",
    "SubscriptionNode",
    "ResourceGroupNode",
    "ResourceNode",
    # --- Lazy: Storage ---
    "ResourceStore",
    "TupleResourceStore",
    "StorageBackend",
    # --- Lazy: Messaging ---
    "MessageBroker",
    "InMemoryBroker",
    "MessageBrokerManager",
]
