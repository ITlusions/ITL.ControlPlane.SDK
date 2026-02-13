"""
Providers module - Resource provider framework and utilities

Provides:
- ResourceProvider: Abstract base class for all resource providers
- ProviderServer: Base class for standalone provider servers
- ScopedResourceHandler: Base class for scope-aware resource uniqueness
- ResourceGroupHandler: Handler for subscription-scoped resource groups
- Advanced handlers: Timestamped, ProvisioningState, Validated
- ResourceProviderRegistry: Registry for managing multiple providers
- Resource ID utilities: ID generation and parsing
- LocationsHandler: Azure location validation
- LocationsHandler: Dynamic location registry
"""

# Core abstractions
from .base import ResourceProvider, ProviderServer

# Resource handlers
from .handlers import (
    ScopedResourceHandler,
    UniquenessScope,
    ProvisioningState,
    TimestampedResourceHandler,
    ProvisioningStateHandler,
    ValidatedResourceHandler,
    ResourceGroupHandler,
)

# Location management
from .locations import (
    LocationsHandler,
    Location,
    RegionMeta,
    VALID_LOCATIONS,
    AVAILABLE_REGIONS,
    LOCATION_TO_REGION,
)

# Utilities
from .utilities import (
    ResourceProviderRegistry,
    resource_registry,
    ResourceIdentity,
    generate_resource_id,
    parse_resource_id,
)

__all__ = [
    # Core abstractions
    "ResourceProvider",
    "ProviderServer",
    # Scope handling
    "ScopedResourceHandler",
    "UniquenessScope",
    # Advanced handlers (Big 3)
    "TimestampedResourceHandler",
    "ProvisioningStateHandler",
    "ValidatedResourceHandler",
    "ProvisioningState",
    # Specific handlers
    "ResourceGroupHandler",
    # Location management
    "LocationsHandler",
    "Location",
    "RegionMeta",
    "VALID_LOCATIONS",
    "AVAILABLE_REGIONS",
    "LOCATION_TO_REGION",
    # Utilities
    "ResourceProviderRegistry",
    "resource_registry",
    "ResourceIdentity",
    "generate_resource_id",
    "parse_resource_id",
]

