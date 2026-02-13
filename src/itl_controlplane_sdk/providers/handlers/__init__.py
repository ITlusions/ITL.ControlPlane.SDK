"""
Resource handler patterns and mixins

Provides:
- ScopedResourceHandler: Base for scope-aware resource uniqueness
- UniquenessScope: Scope levels for resource uniqueness
- Advanced handlers: Timestamped, ProvisioningState, Validated
- ResourceGroupHandler: Specialized handler for resource groups
"""

from .scoped import ScopedResourceHandler, UniquenessScope
from .advanced import (
    ProvisioningState,
    TimestampedResourceHandler,
    ProvisioningStateHandler,
    ValidatedResourceHandler,
)
from .resource_group import ResourceGroupHandler

__all__ = [
    # Scope handling
    "ScopedResourceHandler",
    "UniquenessScope",
    # Advanced handlers
    "ProvisioningState",
    "TimestampedResourceHandler",
    "ProvisioningStateHandler",
    "ValidatedResourceHandler",
    # Specific handlers
    "ResourceGroupHandler",
]
