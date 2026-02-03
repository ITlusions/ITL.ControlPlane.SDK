"""
ITL ControlPlane SDK - Core Framework

This package provides the core framework for building resource providers
and managing cloud resources through a unified interface.

Modules:
    core: Core models, exceptions, infrastructure definitions
    identity: Identity provider framework (Keycloak, Azure AD, etc.)
    fastapi: HTTP routing and middleware
"""

__version__ = "1.0.0"

# Core SDK components (from modular structure)
from itl_controlplane_sdk.core import (
    ResourceRequest,
    ResourceResponse, 
    ResourceListResponse,
    ResourceMetadata,
    ProvisioningState,
    ResourceProviderError,
    ResourceNotFoundError,
    ResourceConflictError,
    ValidationError,
    # Infrastructure models (shared across providers)
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
    ITL_RESOURCE_TYPES,
)

# Identity framework
from itl_controlplane_sdk.identity import (
    IdentityProvider,
    IdentityProviderFactory,
    get_factory as get_identity_factory,
    register_provider as register_identity_provider,
    # Tenant models
    Tenant,
    TenantSpec,
    TenantStatus,
    TenantResponse,
    TenantWithOrganizations,
    # Organization models
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

from .providers import (
    ResourceProvider, 
    ResourceProviderRegistry, 
    resource_registry, 
    ResourceIdentity, 
    generate_resource_id, 
    parse_resource_id,
    ITLLocationsHandler,
    ITLRegionMeta,
)

# Services (application-layer patterns)
from .services import BaseResourceService

# Auto-initialize ITL Locations Handler with default locations
ITLLocationsHandler.initialize(DEFAULT_LOCATIONS)

# Convenience exports
__all__ = [
    # Core Models
    'ResourceRequest',
    'ResourceResponse',
    'ResourceListResponse', 
    'ResourceMetadata',
    'ProvisioningState',
    # Base Classes
    'ResourceProvider',
    'ResourceProviderRegistry',
    'resource_registry',
    # Resource ID utilities
    'ResourceIdentity',
    'generate_resource_id', 
    'parse_resource_id',
    # Locations
    'ITLLocationsHandler',
    'ITLRegionMeta',
    # Services
    'BaseResourceService',
    # Exceptions
    'ResourceProviderError',
    'ResourceNotFoundError',
    'ResourceConflictError',
    'ValidationError',
    # Infrastructure Models
    'ResourceGroup',
    'ManagementGroup',
    'Deployment',
    'Subscription',
    'Location',
    'ExtendedLocation',
    'Tag',
    'Policy',
    'ProviderConfiguration',
    # Constants
    'DEFAULT_LOCATIONS',
    'EXTENDED_LOCATIONS',
    'PROVIDER_NAMESPACE',
    'RESOURCE_TYPE_RESOURCE_GROUPS',
    'RESOURCE_TYPE_MANAGEMENT_GROUPS',
    'RESOURCE_TYPE_DEPLOYMENTS',
    'RESOURCE_TYPE_SUBSCRIPTIONS',
    'RESOURCE_TYPE_TAGS',
    'RESOURCE_TYPE_POLICIES',
    'RESOURCE_TYPE_LOCATIONS',
    'RESOURCE_TYPE_EXTENDED_LOCATIONS',
    'ITL_RESOURCE_TYPES',
    # Identity Framework
    'IdentityProvider',
    'IdentityProviderFactory',
    'get_identity_factory',
    'register_identity_provider',
    # Tenant Models
    'Tenant',
    'TenantSpec',
    'TenantStatus',
    'TenantResponse',
    'TenantWithOrganizations',
    # Organization Models
    'Organization',
    'OrganizationSpec',
    'OrganizationStatus',
    'OrganizationResponse',
    'OrganizationWithDomains',
    'TenantAdminUser',
    'TenantAdminRole',
    'CustomDomain',
    'DomainStatus',
    'DomainVerificationMethod',
]
