"""
Location and region management

Unified handler supporting:
- Default Azure locations (baked-in)
- Dynamic registration from database
- Fast O(1) validation and lookups
- Thread-safe registry
"""

from .locations import (
    # Handler
    LocationsHandler,
    # Enums and constants
    Location,
    RegionMeta,
    # Module-level constants (default locations only)
    VALID_LOCATIONS,
    AVAILABLE_REGIONS,
    LOCATION_TO_REGION,
)

__all__ = [
    # Handler
    "LocationsHandler",
    # Enums and constants
    "Location",
    "RegionMeta",
    # Module-level constants
    "VALID_LOCATIONS",
    "AVAILABLE_REGIONS",
    "LOCATION_TO_REGION",
]
