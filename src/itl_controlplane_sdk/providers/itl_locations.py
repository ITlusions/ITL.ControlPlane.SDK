"""
ITL Locations Handler - Dynamic location registry for Control Plane

Manages two types of locations:
1. DEFAULT_LOCATIONS - Static locations from core.models (API baseline)
2. CUSTOM_LOCATIONS - Dynamically registered locations (added at runtime)

Provides:
- Dynamic validation against defaults + custom locations
- Runtime registration of new locations
- Fast O(1) lookups
- Region-based filtering
- Easy extension for Control Plane

Optimized for:
- Fast O(1) validation (set lookup)
- Minimal string operations
- Pre-computed region mappings
- Cached query results
- Thread-safe registry
"""
from typing import List, Dict, FrozenSet, Optional
import threading


class ITLRegionMeta:
    """ITL region metadata for regional grouping."""
    
    UNITED_STATES = "United States"
    UNITED_KINGDOM = "United Kingdom"
    EUROPE = "Europe"
    NETHERLANDS = "Netherlands"
    ASIA_PACIFIC = "Asia Pacific"
    CDN_EDGE = "CDN Edge"
    CUSTOM = "Custom"  # For dynamically added regions




class ITLLocationsHandler:
    """
    Dynamic location registry for ITL Control Plane.
    
    Thread-safe handler that:
    1. Loads default locations from core.models.DEFAULT_LOCATIONS
    2. Allows dynamic registration of new locations
    3. Validates against combined defaults + custom locations
    4. Maintains O(1) lookup performance
    
    Usage:
        # Initialize with default locations (typically at app startup)
        from itl_controlplane_sdk.core import DEFAULT_LOCATIONS
        ITLLocationsHandler.initialize(DEFAULT_LOCATIONS)
        
        # Validate location (defaults + custom)
        @validator('location')
        def validate_location(cls, v):
            return ITLLocationsHandler.validate_location(v)
        
        # Register new location at runtime (Control Plane extensibility)
        ITLLocationsHandler.register_location("singapore", "Singapore", "Asia Pacific")
        
        # Get all valid locations
        valid = ITLLocationsHandler.get_valid_locations()
    """
    
    # Thread-safe lock
    _lock = threading.RLock()
    
    # Storage for locations and regions
    _default_locations: Dict[str, Dict] = {}  # {name: {display_name, region, ...}}
    _custom_locations: Dict[str, Dict] = {}   # {name: {display_name, region, ...}}
    _custom_regions: set = set()              # Custom region names
    
    # Caches (invalidated when new locations added)
    _valid_locations_cache: FrozenSet[str] = frozenset()
    _locations_by_region_cache: Dict[str, FrozenSet[str]] = {}
    _cache_valid = False
    
    # Error message cache
    _error_message_cache: Dict[str, str] = {}
    
    @classmethod
    def initialize(cls, default_locations: List[Dict[str, str]]) -> None:
        """
        Initialize handler with default locations from core.models.DEFAULT_LOCATIONS.
        
        Should be called once at application startup.
        
        Args:
            default_locations: List of location dicts from DEFAULT_LOCATIONS
                              Each dict should have: name, display_name, region, etc.
        
        Example:
            from itl_controlplane_sdk.core import DEFAULT_LOCATIONS
            ITLLocationsHandler.initialize(DEFAULT_LOCATIONS)
        """
        with cls._lock:
            cls._default_locations.clear()
            cls._custom_locations.clear()
            cls._error_message_cache.clear()
            cls._cache_valid = False
            
            for loc_dict in default_locations:
                name = loc_dict.get("name", "").lower()
                if name:
                    cls._default_locations[name] = loc_dict.copy()
            
            cls._rebuild_cache()
    
    @classmethod
    def register_location(
        cls,
        name: str,
        display_name: str,
        region: str = "Custom",
        **metadata
    ) -> bool:
        """
        Register a new custom location at runtime.
        
        Args:
            name: Location identifier (e.g., 'singapore')
            display_name: Human-readable name (e.g., 'Singapore')
            region: Region name (e.g., 'Asia Pacific', 'Custom')
            **metadata: Additional metadata (shortname, latitude, longitude, etc.)
        
        Returns:
            True if registered, False if already exists
        
        Example:
            # Register new location via Control Plane
            ITLLocationsHandler.register_location(
                "singapore",
                "Singapore",
                region="Asia Pacific",
                shortname="SGP"
            )
        """
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
            if region and region != "Custom":
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
        
        Args:
            name: Location name to unregister
        
        Returns:
            True if unregistered, False if not found or is a default
        """
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
            region = loc_dict.get("region", "Custom")
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
        Check if location is valid (default or custom). O(1) operation.
        
        Args:
            location: Location string to validate
        
        Returns:
            True if valid, False otherwise
        """
        return location.lower() in cls._valid_locations_cache
    
    @classmethod
    def validate_location(cls, location: str) -> str:
        """
        Validate location and return normalized value. O(1) operation.
        
        Use in Pydantic validators:
            @validator('location')
            def validate_location(cls, v):
                return ITLLocationsHandler.validate_location(v)
        
        Args:
            location: Location string to validate
        
        Returns:
            Normalized location string
        
        Raises:
            ValueError: If location is not valid
        """
        normalized = location.lower()
        if normalized in cls._valid_locations_cache:
            return normalized
        
        # Generate error message (only on validation failure)
        if normalized not in cls._error_message_cache:
            valid_locs = sorted(cls._valid_locations_cache)
            cls._error_message_cache[normalized] = (
                f"'{location}' is not a valid ITL location. "
                f"Valid options: {', '.join(valid_locs)}"
            )
        raise ValueError(cls._error_message_cache[normalized])
    
    @classmethod
    def get_valid_locations(cls) -> List[str]:
        """
        Get list of all valid locations (defaults + custom). O(1) - returns cached list.
        
        Returns:
            Sorted list of valid location strings
        """
        return sorted(cls._valid_locations_cache)
    
    @classmethod
    def get_valid_locations_set(cls) -> FrozenSet[str]:
        """
        Get frozenset of all valid locations for O(1) membership testing.
        
        Returns:
            Frozenset of valid location strings (immutable, safe to share)
        """
        return cls._valid_locations_cache
    
    @classmethod
    def get_locations_by_region(cls, region: str) -> List[str]:
        """
        Get all locations in a specific region. O(1) - uses pre-computed mapping.
        
        Args:
            region: Region name (e.g., 'Netherlands', 'Europe', 'Custom', or custom region)
        
        Returns:
            Sorted list of location strings in that region
        
        Example:
            nl_locations = ITLLocationsHandler.get_locations_by_region("Netherlands")
            # Returns: ['almere', 'amsterdam', 'rotterdam']
        """
        locations = cls._locations_by_region_cache.get(region, frozenset())
        return sorted(locations)
    
    @classmethod
    def get_available_regions(cls) -> List[str]:
        """
        Get list of all available regions (defaults + custom). O(1) - returns cached list.
        
        Returns:
            Sorted list of region strings
        """
        return sorted(cls._locations_by_region_cache.keys())
    
    @classmethod
    def get_region_for_location(cls, location: str) -> str:
        """
        Get the region for a specific location. O(1) - dict lookup.
        
        Args:
            location: Location string (e.g., 'amsterdam')
        
        Returns:
            Region string (e.g., 'Netherlands')
        
        Raises:
            ValueError: If location is not valid
        """
        normalized = location.lower()
        
        # Check default locations first
        if normalized in cls._default_locations:
            return cls._default_locations[normalized].get("region", "Unknown")
        
        # Check custom locations
        if normalized in cls._custom_locations:
            return cls._custom_locations[normalized].get("region", "Custom")
        
        raise ValueError(f"'{location}' is not a valid ITL location")
    
    @classmethod
    def get_location_metadata(cls, location: str) -> Optional[Dict]:
        """
        Get full metadata for a location.
        
        Args:
            location: Location string
        
        Returns:
            Dictionary with location metadata, or None if not found
        
        Example:
            meta = ITLLocationsHandler.get_location_metadata("amsterdam")
            # Returns: {"name": "amsterdam", "display_name": "Amsterdam", "region": "Netherlands", ...}
        """
        normalized = location.lower()
        
        if normalized in cls._default_locations:
            return cls._default_locations[normalized].copy()
        
        if normalized in cls._custom_locations:
            return cls._custom_locations[normalized].copy()
        
        return None
    
    @classmethod
    def get_all_locations_with_metadata(cls) -> List[Dict]:
        """
        Get all locations with their full metadata.
        
        Returns:
            List of location dicts (sorted by name)
        """
        all_locs = {**cls._default_locations, **cls._custom_locations}
        return sorted(all_locs.values(), key=lambda x: x.get("name", ""))
    
    @classmethod
    def get_default_locations_count(cls) -> int:
        """Get count of default locations."""
        return len(cls._default_locations)
    
    @classmethod
    def get_custom_locations_count(cls) -> int:
        """Get count of custom (dynamically registered) locations."""
        return len(cls._custom_locations)
    
    @classmethod
    def get_stats(cls) -> Dict:
        """
        Get statistics about registered locations.
        
        Returns:
            Dict with counts and metadata
        """
        return {
            "total": len(cls._valid_locations_cache),
            "default": len(cls._default_locations),
            "custom": len(cls._custom_locations),
            "regions": len(cls._locations_by_region_cache),
            "custom_regions": len(cls._custom_regions),
        }
