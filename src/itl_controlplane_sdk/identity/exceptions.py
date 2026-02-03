"""
Identity Provider specific exceptions.

These are re-exported from the main SDK exceptions module for convenience.
"""

from .. import exceptions

# Re-export common exceptions
ConfigurationError = exceptions.ConfigurationError
ValidationError = exceptions.ValidationError
AuthorizationError = exceptions.AuthorizationError
ProviderError = exceptions.ProviderError
CascadeDeletionError = exceptions.CascadeDeletionError
TenantError = exceptions.TenantError
TenantCreationError = exceptions.TenantCreationError
TenantNotFoundError = exceptions.TenantNotFoundError
TenantDeletionError = exceptions.TenantDeletionError
OrganizationError = exceptions.OrganizationError
OrganizationCreationError = exceptions.OrganizationCreationError
OrganizationNotFoundError = exceptions.OrganizationNotFoundError
UserError = exceptions.UserError
DomainError = exceptions.DomainError
ExternalServiceError = exceptions.ExternalServiceError
KeycloakError = exceptions.KeycloakError
GraphDBError = exceptions.GraphDBError
TransactionError = exceptions.TransactionError
ErrorCategory = exceptions.ErrorCategory
ControlPlaneError = exceptions.ControlPlaneError

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
