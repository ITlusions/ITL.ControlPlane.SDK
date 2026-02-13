"""
Unified Locations Handler - Default locations with dynamic registration support

Provides:
- Default Azure locations (baked-in)
- Dynamic location registration from database
- Fast O(1) validation and lookups
- Thread-safe registry
- Region-based filtering

Usage:
    # Initialize with defaults (automatic on first access)
    LocationsHandler.initialize()
    
    # Validate location
    LocationsHandler.validate_location("eastus")  # O(1)
    
    # Register custom location from database
    LocationsHandler.register_location("singapore", "Singapore", region="Asia Pacific")
    
    # Get all valid locations
    all_locs = LocationsHandler.get_valid_locations()
"""

from typing import List, Dict, FrozenSet, Optional
from enum import Enum
import threading


# ============================================================================
# Default Locations (Azure baseline)
# ============================================================================

class RegionMeta:
    """Region metadata for regional grouping."""
    UNITED_STATES = "United States"
    UNITED_KINGDOM = "United Kingdom"
    EUROPE = "Europe"
    NETHERLANDS = "Netherlands"
    ASIA_PACIFIC = "Asia Pacific"
    CDN_EDGE = "CDN Edge"
    CUSTOM = "Custom"


class Location(str, Enum):
    """Predefined location constants."""
    # United States
    EASTUS = "eastus"
    WESTUS = "westus"
    CENTRALUS = "centralus"
    
    # Europe
    NORTHEUROPE = "northeurope"
    WESTEUROPE = "westeurope"
    FRANCECENTRAL = "francecentral"
    GERMANYWESTCENTRAL = "germanywestcentral"
    SWEDENCENTRAL = "swedencentral"
    POLANDCENTRAL = "polandcentral"
    ITALYNORTH = "italynorth"
    SWITZERLANDNORTH = "switzerlandnorth"
    
    # United Kingdom
    UKSOUTH = "uksouth"
    UKWEST = "ukwest"
    
    # Asia Pacific
    EASTASIA = "eastasia"
    SOUTHEASTASIA = "southeastasia"
    
    # Netherlands
    AMSTERDAM = "amsterdam"
    ROTTERDAM = "rotterdam"
    ALMERE = "almere"
    
    # CDN Edge
    CDN_AMSTERDAM = "cdn-amsterdam"
    CDN_FRANKFURT = "cdn-frankfurt"
    CDN_LONDON = "cdn-london"
    CDN_PARIS = "cdn-paris"
    CDN_STOCKHOLM = "cdn-stockholm"
    CDN_ZURICH = "cdn-zurich"


# Default location metadata (static Azure locations)
_DEFAULT_LOCATIONS_DATA = {
    "eastus": {"display_name": "East US", "region": RegionMeta.UNITED_STATES, "shortname": "US-E"},
    "westus": {"display_name": "West US", "region": RegionMeta.UNITED_STATES, "shortname": "US-W"},
    "centralus": {"display_name": "Central US", "region": RegionMeta.UNITED_STATES, "shortname": "US-C"},
    "northeurope": {"display_name": "North Europe", "region": RegionMeta.EUROPE, "shortname": "EU-N"},
    "westeurope": {"display_name": "West Europe", "region": RegionMeta.EUROPE, "shortname": "EU-W"},
    "francecentral": {"display_name": "France Central", "region": RegionMeta.EUROPE, "shortname": "EU-FR"},
    "germanywestcentral": {"display_name": "Germany West Central", "region": RegionMeta.EUROPE, "shortname": "EU-DE"},
    "swedencentral": {"display_name": "Sweden Central", "region": RegionMeta.EUROPE, "shortname": "EU-SE"},
    "polandcentral": {"display_name": "Poland Central", "region": RegionMeta.EUROPE, "shortname": "EU-PL"},
    "italynorth": {"display_name": "Italy North", "region": RegionMeta.EUROPE, "shortname": "EU-IT"},
    "switzerlandnorth": {"display_name": "Switzerland North", "region": RegionMeta.EUROPE, "shortname": "EU-CH"},
    "uksouth": {"display_name": "UK South", "region": RegionMeta.UNITED_KINGDOM, "shortname": "UK-S"},
    "ukwest": {"display_name": "UK West", "region": RegionMeta.UNITED_KINGDOM, "shortname": "UK-W"},
    "eastasia": {"display_name": "East Asia", "region": RegionMeta.ASIA_PACIFIC, "shortname": "AP-E"},
    "southeastasia": {"display_name": "Southeast Asia", "region": RegionMeta.ASIA_PACIFIC, "shortname": "AP-SE"},
    "amsterdam": {"display_name": "Amsterdam", "region": RegionMeta.NETHERLANDS, "shortname": "NL-AM"},
    "rotterdam": {"display_name": "Rotterdam", "region": RegionMeta.NETHERLANDS, "shortname": "NL-RT"},
    "almere": {"display_name": "Almere", "region": RegionMeta.NETHERLANDS, "shortname": "NL-AL"},
    "cdn-amsterdam": {"display_name": "CDN Amsterdam", "region": RegionMeta.CDN_EDGE, "shortname": "CDN-AM"},
    "cdn-frankfurt": {"display_name": "CDN Frankfurt", "region": RegionMeta.CDN_EDGE, "shortname": "CDN-FR"},
    "cdn-london": {"display_name": "CDN London", "region": RegionMeta.CDN_EDGE, "shortname": "CDN-LO"},
    "cdn-paris": {"display_name": "CDN Paris", "region": RegionMeta.CDN_EDGE, "shortname": "CDN-PA"},
    "cdn-stockholm": {"display_name": "CDN Stockholm", "region": RegionMeta.CDN_EDGE, "shortname": "CDN-ST"},
    "cdn-zurich": {"display_name": "CDN Zurich", "region": RegionMeta.CDN_EDGE, "shortname": "CDN-ZU"},
}


# ============================================================================
# Unified Locations Handler
# ============================================================================

class LocationsHandler:
    """
    Unified location handler with default locations and dynamic registration.
    
    Features:
    - Default Azure locations (baked-in)
    - Dynamic registration from database
    - O(1) validation and lookups
    - Thread-safe
    - Region-based filtering
    - Full metadata support
    """
    
    # Thread-safe lock for registry
    _lock = threading.RLock()
    
    # Storage for locations
    _default_locations: Dict[str, Dict] = {}  # Defaults (immutable)
    _custom_locations: Dict[str, Dict] = {}   # Dynamically registered (mutable)
    _custom_regions: set = set()              # Custom region names
    
    # Caches (invalidated when locations added/removed)
    _valid_locations_cache: FrozenSet[str] = frozenset()
    _locations_by_region_cache: Dict[str, FrozenSet[str]] = {}
    _cache_valid = False
    
    # Error message cache
    _error_message_cache: Dict[str, str] = {}
    
    # Initialization flag
    _initialized = False
    
    @classmethod
    def initialize(cls) -> None:
        """
        Initialize handler with default locations.
        
        Safe to call multiple times (idempotent).
        Typically called once at application startup.
        """
        with cls._lock:
            if cls._initialized:
                return
            
            cls._default_locations = {name: data.copy() for name, data in _DEFAULT_LOCATIONS_DATA.items()}
            cls._custom_locations.clear()
            cls._custom_regions.clear()
            cls._error_message_cache.clear()
            cls._cache_valid = False
            
            cls._rebuild_cache()
            cls._initialized = True
    
    @classmethod
    def register_location(
        cls,
        name: str,
        display_name: str,
        region: str = "Custom",
        **metadata
    ) -> bool:
        """
        Register a custom location (typically from database).
        
        Thread-safe. Cannot override default locations.
        
        Args:
            name: Location identifier (e.g., 'singapore')
            display_name: Human-readable name (e.g., 'Singapore')
            region: Region name (e.g., 'Asia Pacific')
            **metadata: Additional metadata (shortname, latitude, longitude, etc.)
        
        Returns:
            True if registered, False if already exists or is a default
        
        Example:
            LocationsHandler.register_location(
                "singapore",
                "Singapore",
                region="Asia Pacific",
                shortname="SGP"
            )
        """
        cls.initialize()  # Ensure initialized
        
        name = name.lower()
        
        with cls._lock:
            # Don't override defaults
            if name in cls._default_locations:
                return False
            
            # Don't re-register existing custom location
            if name in cls._custom_locations:
                return False
            
            # Register the location
            cls._custom_locations[name] = {
                "name": name,
                "display_name": display_name,
                "region": region,
                **metadata
            }
            
            # Track custom regions
            if region and region != RegionMeta.CUSTOM:
                cls._custom_regions.add(region)
            
            # Invalidate cache
            cls._cache_valid = False
            cls._error_message_cache.clear()
            cls._rebuild_cache()
            
            return True
    
    @classmethod
    def unregister_location(cls, name: str) -> bool:
        """
        Unregister a custom location.
        
        Thread-safe. Cannot remove default locations.
        
        Args:
            name: Location name to unregister
        
        Returns:
            True if unregistered, False if not found or is a default
        """
        cls.initialize()  # Ensure initialized
        
        name = name.lower()
        
        with cls._lock:
            if name in cls._default_locations:
                return False  # Cannot remove default locations
            
            if name not in cls._custom_locations:
                return False
            
            del cls._custom_locations[name]
            cls._cache_valid = False
            cls._error_message_cache.clear()
            cls._rebuild_cache()
            
            return True
    
    @classmethod
    def _rebuild_cache(cls) -> None:
        """Rebuild all caches (must be called with lock held)."""
        # Combine all locations
        all_locations = {**cls._default_locations, **cls._custom_locations}
        
        # Cache valid locations
        cls._valid_locations_cache = frozenset(all_locations.keys())
        
        # Cache locations by region
        regions_to_locations: Dict[str, set] = {}
        for name, loc_dict in all_locations.items():
            region = loc_dict.get("region", RegionMeta.CUSTOM)
            if region not in regions_to_locations:
                regions_to_locations[region] = set()
            regions_to_locations[region].add(name)
        
        # Convert to frozensets
        cls._locations_by_region_cache = {
            region: frozenset(locs)
            for region, locs in regions_to_locations.items()
        }
        
        cls._cache_valid = True
    
    @classmethod
    def is_valid(cls, location: str) -> bool:
        """
        Check if location is valid. O(1) operation.
        
        Args:
            location: Location string to check
        
        Returns:
            True if valid, False otherwise
        """
        cls.initialize()  # Ensure initialized
        return location.lower() in cls._valid_locations_cache
    
    @classmethod
    def validate_location(cls, location: str) -> str:
        """
        Validate location and return normalized value. O(1) operation.
        
        Use in Pydantic validators:
            @validator('location')
            def validate_location(cls, v):
                return LocationsHandler.validate_location(v)
        
        Args:
            location: Location string to validate
        
        Returns:
            Normalized location string (lowercase)
        
        Raises:
            ValueError: If location is not valid
        """
        cls.initialize()  # Ensure initialized
        
        normalized = location.lower()
        if normalized in cls._valid_locations_cache:
            return normalized
        
        # Generate error message (only on validation failure)
        if normalized not in cls._error_message_cache:
            valid_locs = sorted(cls._valid_locations_cache)
            cls._error_message_cache[normalized] = (
                f"'{location}' is not a valid location. "
                f"Valid options: {', '.join(valid_locs)}"
            )
        raise ValueError(cls._error_message_cache[normalized])
    
    @classmethod
    def get_valid_locations(cls) -> List[str]:
        """
        Get all valid locations (defaults + custom). O(1) - cached.
        
        Returns:
            Sorted list of valid location strings
        """
        cls.initialize()  # Ensure initialized
        return sorted(cls._valid_locations_cache)
    
    @classmethod
    def get_valid_locations_set(cls) -> FrozenSet[str]:
        """
        Get frozenset of valid locations for O(1) membership testing.
        
        Returns:
            Immutable set safe to share
        """
        cls.initialize()  # Ensure initialized
        return cls._valid_locations_cache
    
    @classmethod
    def get_locations_by_region(cls, region: str) -> List[str]:
        """
        Get all locations in a region. O(1) - uses cached mapping.
        
        Args:
            region: Region name (e.g., 'Netherlands', 'Europe')
        
        Returns:
            Sorted list of location strings in that region
        """
        cls.initialize()  # Ensure initialized
        locations = cls._locations_by_region_cache.get(region, frozenset())
        return sorted(locations)
    
    @classmethod
    def get_available_regions(cls) -> List[str]:
        """
        Get all regions with registered locations. O(1) - cached.
        
        Returns:
            Sorted list of region strings
        """
        cls.initialize()  # Ensure initialized
        return sorted(cls._locations_by_region_cache.keys())
    
    @classmethod
    def get_region_for_location(cls, location: str) -> str:
        """
        Get region for a specific location. O(1) - dict lookup.
        
        Args:
            location: Location string (e.g., 'amsterdam')
        
        Returns:
            Region string (e.g., 'Netherlands')
        
        Raises:
            ValueError: If location not found
        """
        cls.initialize()  # Ensure initialized
        
        normalized = location.lower()
        
        # Check default locations first
        if normalized in cls._default_locations:
            return cls._default_locations[normalized].get("region", "Unknown")
        
        # Check custom locations
        if normalized in cls._custom_locations:
            return cls._custom_locations[normalized].get("region", RegionMeta.CUSTOM)
        
        raise ValueError(f"'{location}' is not a valid location")
    
    @classmethod
    def get_location_metadata(cls, location: str) -> Optional[Dict]:
        """
        Get full metadata for a location.
        
        Args:
            location: Location string
        
        Returns:
            Dictionary with metadata, or None if not found
        """
        cls.initialize()  # Ensure initialized
        
        normalized = location.lower()
        
        if normalized in cls._default_locations:
            return cls._default_locations[normalized].copy()
        
        if normalized in cls._custom_locations:
            return cls._custom_locations[normalized].copy()
        
        return None
    
    @classmethod
    def get_all_locations_with_metadata(cls) -> List[Dict]:
        """
        Get all locations with full metadata.
        
        Returns:
            List of location dicts (sorted by name)
        """
        cls.initialize()  # Ensure initialized
        
        all_locs = {**cls._default_locations, **cls._custom_locations}
        return sorted(all_locs.values(), key=lambda x: x.get("name", ""))
    
    @classmethod
    def get_default_locations_count(cls) -> int:
        """Get count of default locations."""
        cls.initialize()  # Ensure initialized
        return len(cls._default_locations)
    
    @classmethod
    def get_custom_locations_count(cls) -> int:
        """Get count of custom (dynamically registered) locations."""
        cls.initialize()  # Ensure initialized
        return len(cls._custom_locations)
    
    @classmethod
    def get_stats(cls) -> Dict:
        """
        Get statistics about registered locations.
        
        Returns:
            Dict with counts and metadata
        """
        cls.initialize()  # Ensure initialized
        
        return {
            "total": len(cls._valid_locations_cache),
            "default": len(cls._default_locations),
            "custom": len(cls._custom_locations),
            "regions": len(cls._locations_by_region_cache),
            "custom_regions": len(cls._custom_regions),
        }


# Module-level constants for convenience
VALID_LOCATIONS = frozenset(_DEFAULT_LOCATIONS_DATA.keys())  # Default locations only
AVAILABLE_REGIONS = frozenset({meta.get("region") for meta in _DEFAULT_LOCATIONS_DATA.values()})
LOCATION_TO_REGION = {name: meta.get("region", "Unknown") for name, meta in _DEFAULT_LOCATIONS_DATA.items()}

# Region metadata constant
RegionMeta = RegionMeta
Location = Location
