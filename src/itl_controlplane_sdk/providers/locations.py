"""
Azure Locations Handler - Static Azure location validation

Provides Azure location constants and validation utilities.
This is a static handler for Azure-specific locations.

For dynamic, extensible location handling (supporting both defaults + custom locations),
use ITLLocationsHandler from itl_locations.py
"""
from typing import List, Dict, FrozenSet, Optional
from enum import Enum


class AzureRegionMeta:
    """Azure region metadata for regional grouping."""
    
    UNITED_STATES = "United States"
    UNITED_KINGDOM = "United Kingdom"
    EUROPE = "Europe"
    ASIA_PACIFIC = "Asia Pacific"
    CDN_EDGE = "CDN Edge"


class AzureLocation(str, Enum):
    """Valid Azure locations."""
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


# Static location metadata
_AZURE_LOCATIONS_DATA = {
    "eastus": {"display_name": "East US", "region": AzureRegionMeta.UNITED_STATES, "shortname": "US-E"},
    "westus": {"display_name": "West US", "region": AzureRegionMeta.UNITED_STATES, "shortname": "US-W"},
    "centralus": {"display_name": "Central US", "region": AzureRegionMeta.UNITED_STATES, "shortname": "US-C"},
    "northeurope": {"display_name": "North Europe", "region": AzureRegionMeta.EUROPE, "shortname": "EU-N"},
    "westeurope": {"display_name": "West Europe", "region": AzureRegionMeta.EUROPE, "shortname": "EU-W"},
    "francecentral": {"display_name": "France Central", "region": AzureRegionMeta.EUROPE, "shortname": "EU-FR"},
    "germanywestcentral": {"display_name": "Germany West Central", "region": AzureRegionMeta.EUROPE, "shortname": "EU-DE"},
    "swedencentral": {"display_name": "Sweden Central", "region": AzureRegionMeta.EUROPE, "shortname": "EU-SE"},
    "polandcentral": {"display_name": "Poland Central", "region": AzureRegionMeta.EUROPE, "shortname": "EU-PL"},
    "italynorth": {"display_name": "Italy North", "region": AzureRegionMeta.EUROPE, "shortname": "EU-IT"},
    "switzerlandnorth": {"display_name": "Switzerland North", "region": AzureRegionMeta.EUROPE, "shortname": "EU-CH"},
    "uksouth": {"display_name": "UK South", "region": AzureRegionMeta.UNITED_KINGDOM, "shortname": "UK-S"},
    "ukwest": {"display_name": "UK West", "region": AzureRegionMeta.UNITED_KINGDOM, "shortname": "UK-W"},
    "eastasia": {"display_name": "East Asia", "region": AzureRegionMeta.ASIA_PACIFIC, "shortname": "AP-E"},
    "southeastasia": {"display_name": "Southeast Asia", "region": AzureRegionMeta.ASIA_PACIFIC, "shortname": "AP-SE"},
    "amsterdam": {"display_name": "Amsterdam", "region": "Netherlands", "shortname": "NL-AM"},
    "rotterdam": {"display_name": "Rotterdam", "region": "Netherlands", "shortname": "NL-RT"},
    "almere": {"display_name": "Almere", "region": "Netherlands", "shortname": "NL-AL"},
    "cdn-amsterdam": {"display_name": "CDN Amsterdam", "region": AzureRegionMeta.CDN_EDGE, "shortname": "CDN-AM"},
    "cdn-frankfurt": {"display_name": "CDN Frankfurt", "region": AzureRegionMeta.CDN_EDGE, "shortname": "CDN-FR"},
    "cdn-london": {"display_name": "CDN London", "region": AzureRegionMeta.CDN_EDGE, "shortname": "CDN-LO"},
    "cdn-paris": {"display_name": "CDN Paris", "region": AzureRegionMeta.CDN_EDGE, "shortname": "CDN-PA"},
    "cdn-stockholm": {"display_name": "CDN Stockholm", "region": AzureRegionMeta.CDN_EDGE, "shortname": "CDN-ST"},
    "cdn-zurich": {"display_name": "CDN Zurich", "region": AzureRegionMeta.CDN_EDGE, "shortname": "CDN-ZU"},
}

# Pre-computed sets for O(1) validation
VALID_LOCATIONS = frozenset(_AZURE_LOCATIONS_DATA.keys())

# Build region to locations mapping
_REGION_TO_LOCATIONS: Dict[str, FrozenSet[str]] = {}
for name, metadata in _AZURE_LOCATIONS_DATA.items():
    region = metadata.get("region", "Unknown")
    if region not in _REGION_TO_LOCATIONS:
        _REGION_TO_LOCATIONS[region] = set()
    _REGION_TO_LOCATIONS[region].add(name)

LOCATION_TO_REGION = {name: metadata.get("region", "Unknown") for name, metadata in _AZURE_LOCATIONS_DATA.items()}
AVAILABLE_REGIONS = frozenset(_REGION_TO_LOCATIONS.keys())


class LocationsHandler:
    """Static Azure locations handler."""
    
    @classmethod
    def is_valid(cls, location: str) -> bool:
        """Check if location is valid. O(1) operation."""
        return location.lower() in VALID_LOCATIONS
    
    @classmethod
    def validate_location(cls, location: str) -> str:
        """Validate and normalize location."""
        normalized = location.lower()
        if normalized not in VALID_LOCATIONS:
            raise ValueError(f"Invalid location: {location}. Must be one of {sorted(VALID_LOCATIONS)}")
        return normalized
    
    @classmethod
    def get_valid_locations(cls) -> List[str]:
        """Get all valid Azure locations."""
        return sorted(VALID_LOCATIONS)
    
    @classmethod
    def get_available_regions(cls) -> List[str]:
        """Get all available regions."""
        return sorted(AVAILABLE_REGIONS)
    
    @classmethod
    def get_locations_by_region(cls, region: str) -> List[str]:
        """Get locations for a specific region."""
        if region not in _REGION_TO_LOCATIONS:
            return []
        return sorted(_REGION_TO_LOCATIONS[region])
    
    @classmethod
    def get_region_for_location(cls, location: str) -> Optional[str]:
        """Get region for a specific location."""
        return LOCATION_TO_REGION.get(location.lower())
