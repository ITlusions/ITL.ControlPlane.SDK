"""
Identity Provider Framework for ITL Control Plane SDK.

Provides abstract interfaces and factory pattern for pluggable identity providers.

Supports:
- Keycloak (default)
- Azure AD
- Okta
- Custom implementations

Includes tenant and organization models for multi-tenant identity management.

Example:
    from itl_controlplane_sdk.identity import (
        get_factory,
        register_provider,
        Tenant,
        Organization,
    )
    from keycloak_identity_provider import KeycloakIdentityProvider

    # Register available providers
    register_provider("keycloak", KeycloakIdentityProvider)

    # Create provider instance
    factory = get_factory()
    config = {"url": "http://localhost:8080", "realm": "master"}
    provider = factory.create("keycloak", config)

    # Use provider
    realm = await provider.create_realm(spec)
"""

from .identity_provider_base import IdentityProvider
from .identity_provider_factory import (
    IdentityProviderFactory,
    get_factory,
    register_provider,
    create_provider,
    get_or_create_provider,
)
from .tenant import (
    Tenant,
    TenantSpec,
    TenantStatus,
    TenantResponse,
    TenantWithOrganizations,
)
from .organization import (
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

__all__ = [
    # Identity Provider Framework
    "IdentityProvider",
    "IdentityProviderFactory",
    "get_factory",
    "register_provider",
    "create_provider",
    "get_or_create_provider",
    # Tenant Models
    "Tenant",
    "TenantSpec",
    "TenantStatus",
    "TenantResponse",
    "TenantWithOrganizations",
    # Organization Models
    "Organization",
    "OrganizationSpec",
    "OrganizationStatus",
    "OrganizationResponse",
    "OrganizationWithDomains",
    # Organization Components
    "TenantAdminUser",
    "TenantAdminRole",
    "CustomDomain",
    "DomainStatus",
    "DomainVerificationMethod",
]
