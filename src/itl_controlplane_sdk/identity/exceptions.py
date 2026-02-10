"""
Identity Provider specific exceptions.

Defines the exception hierarchy for the identity module.
These exceptions can be used standalone without depending on
external exception modules.
"""

from ..core.exceptions import (
    ResourceProviderError,
    ValidationError,
)


# ---------------------------------------------------------------------------
# Identity-specific exception hierarchy
# ---------------------------------------------------------------------------

class IdentityError(ResourceProviderError):
    """Base exception for all identity operations."""

    def __init__(self, message: str, context: dict = None):
        super().__init__(message, error_code="IdentityError", status_code=500)
        self.context = context or {}


class ConfigurationError(IdentityError):
    """Identity provider configuration is invalid or incomplete."""

    def __init__(self, message: str, context: dict = None):
        super().__init__(message, context=context)
        self.error_code = "ConfigurationError"
        self.status_code = 400


class ProviderError(IdentityError):
    """An identity provider operation failed."""

    def __init__(self, message: str, context: dict = None):
        super().__init__(message, context=context)
        self.error_code = "ProviderError"


class AuthorizationError(IdentityError):
    """Authorization check failed."""

    def __init__(self, message: str, context: dict = None):
        super().__init__(message, context=context)
        self.error_code = "AuthorizationError"
        self.status_code = 403


class TenantError(ProviderError):
    """Base exception for tenant operations."""


class TenantCreationError(TenantError):
    """Tenant creation failed."""


class TenantNotFoundError(TenantError):
    """Tenant not found."""

    def __init__(self, message: str, context: dict = None):
        super().__init__(message, context=context)
        self.status_code = 404


class TenantDeletionError(TenantError):
    """Tenant deletion failed."""


class OrganizationError(ProviderError):
    """Base exception for organization operations."""


class OrganizationCreationError(OrganizationError):
    """Organization creation failed."""


class OrganizationNotFoundError(OrganizationError):
    """Organization not found."""

    def __init__(self, message: str, context: dict = None):
        super().__init__(message, context=context)
        self.status_code = 404


class UserError(ProviderError):
    """Base exception for user operations."""


class DomainError(ProviderError):
    """Base exception for domain operations."""


class CascadeDeletionError(ProviderError):
    """Cascade deletion encountered an error."""


class ExternalServiceError(ProviderError):
    """External service (Keycloak, Azure AD, etc.) returned an error."""


class KeycloakError(ExternalServiceError):
    """Keycloak-specific error."""


class GraphDBError(ExternalServiceError):
    """Graph database operation failed."""


class TransactionError(ProviderError):
    """Transaction failed (multi-step operation)."""

__all__ = [
    "ConfigurationError",
    "ValidationError",
    "AuthorizationError",
    "ProviderError",
    "CascadeDeletionError",
    "TenantError",
    "TenantCreationError",
    "TenantNotFoundError",
    "TenantDeletionError",
    "OrganizationError",
    "OrganizationCreationError",
    "OrganizationNotFoundError",
    "UserError",
    "DomainError",
    "ExternalServiceError",
    "KeycloakError",
    "GraphDBError",
    "TransactionError",
    "ErrorCategory",
    "ControlPlaneError",
]
