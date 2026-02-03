"""
Providers module - Resource provider framework and utilities

This module contains:
- ResourceProvider: Abstract base class for all resource providers
- ScopedResourceHandler: Base class for scope-aware resource uniqueness
- ResourceGroupHandler: Handler for subscription-scoped resource groups
- ResourceProviderRegistry: Registry for managing multiple providers
- Resource ID utilities: ID generation and parsing
- LocationsHandler: Dynamic Azure location validation
"""

from .base import ResourceProvider
from .scoped_resources import ScopedResourceHandler, UniquenessScope
from .resource_group_handler import ResourceGroupHandler
from .resource_handlers import (
    ProvisioningState,
    TimestampedResourceHandler,
    ProvisioningStateHandler,
    ValidatedResourceHandler,
)
from .locations import (
    AzureLocation,
    AzureRegionMeta,
    LocationsHandler,
    VALID_LOCATIONS,
    AVAILABLE_REGIONS,
    LOCATION_TO_REGION,
)
from .itl_locations import (
    ITLRegionMeta,
    ITLLocationsHandler,
)
from .registry import ResourceProviderRegistry, resource_registry
from .resource_ids import ResourceIdentity, generate_resource_id, parse_resource_id

__all__ = [
    # Base classes
    "ResourceProvider",
    "ScopedResourceHandler",
    "UniquenessScope",
    # Advanced handlers (Big 3)
    "TimestampedResourceHandler",
    "ProvisioningStateHandler",
    "ValidatedResourceHandler",
    "ProvisioningState",
    # Specific handlers
    "ResourceGroupHandler",
    # Azure Locations
    "AzureLocation",
    "AzureRegionMeta",
    "LocationsHandler",
    "VALID_LOCATIONS",
    "AVAILABLE_REGIONS",
    "LOCATION_TO_REGION",
    # ITL Locations (Dynamic Registry)
    "ITLRegionMeta",
    "ITLLocationsHandler",
    # Registry
    "ResourceProviderRegistry",
    "resource_registry",
    # Resource ID utilities
    "ResourceIdentity",
    "generate_resource_id",
    "parse_resource_id",
]
