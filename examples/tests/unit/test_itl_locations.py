"""
Example: Using LocationsHandler in Pydantic schemas

Shows how to validate resources using your custom locations
"""

from pydantic import BaseModel, validator, Field
from itl_controlplane_sdk.providers.locations import (
    LocationsHandler,
    RegionMeta,
    Location,
)


# Example 1: Basic schema with location validation
class DeploymentSchema(BaseModel):
    """Example schema using location validation"""
    
    name: str = Field(..., description="Deployment name")
    location: str = Field(..., description="location")
    environment: str = Field(..., description="Environment")
    
    @validator('location')
    def validate_location(cls, v):
        """Automatically validates against all 27 locations"""
        return LocationsHandler.validate_location(v)


# Example 2: Using locations
if __name__ == "__main__":
    print("locations Handler Examples\n")
    print("=" * 70)
    
    # Example 1: Check if location is valid
    print("\n1. Validate a Location")
    print("-" * 70)
    
    if LocationsHandler.is_valid("amsterdam"):
        print("'amsterdam' is a valid location")
    else:
        print("'amsterdam' is not valid")
    
    if LocationsHandler.is_valid("invalid-location"):
        print("'invalid-location' is valid")
    else:
        print("'invalid-location' is not valid")
    
    # Example 2: Get all valid locations
    print("\n2. Get All Valid Locations")
    print("-" * 70)
    locations = LocationsHandler.get_valid_locations()
    print(f"Total locations: {len(locations)}")
    print(f"Locations: {', '.join(locations)}")
    
    # Example 3: Get locations by region
    print("\n3. Get Locations by Region")
    print("-" * 70)
    
    regions = LocationsHandler.get_available_regions()
    print(f"Available regions: {', '.join(regions)}\n")
    
    for region_name in RegionMeta.__members__.values():
        locs = LocationsHandler.get_locations_by_region(region_name)
        print(f"  {region_name.value}: {', '.join(locs)}")
    
    # Example 4: Get region for a location
    print("\n4. Get Region for Location")
    print("-" * 70)
    
    test_locations = ["amsterdam", "eastus", "cdn-london"]
    for loc in test_locations:
        try:
            region = LocationsHandler.get_region_for_location(loc)
            print(f"  {loc:20} -> {region}")
        except ValueError as e:
            print(f"  {loc:20} -> ERROR: {e}")
    
    # Example 5: Using in Pydantic Schema
    print("\n5. Using in Pydantic Schema")
    print("-" * 70)
    
    # Valid deployment
    try:
        deployment = DeploymentSchema(
            name="app-v1",
            location="amsterdam",
            environment="production"
        )
        print(f"Created deployment:")
        print(f"    Name: {deployment.name}")
        print(f"    Location: {deployment.location}")
        print(f"    Environment: {deployment.environment}")
    except ValueError as e:
        print(f"Error: {e}")
    
    # Invalid location
    print("\n  Trying with invalid location...")
    try:
        deployment = DeploymentSchema(
            name="app-v1",
            location="invalid-datacenter",
            environment="production"
        )
    except ValueError as e:
        error_msg = str(e)
        print(f"Validation error (truncated):")
        print(f"   {error_msg[:100]}...")
        # Show valid options
        valid = LocationsHandler.get_valid_locations()
        print(f"\n  Valid locations: {', '.join(valid[:5])}... ({len(valid)} total)")
    
    # Example 6: Fast O(1) lookup
    print("\n6. Fast Location Lookup (O(1))")
    print("-" * 70)
    
    valid_locs = LocationsHandler.get_valid_locations_set()
    print(f"Valid locations set: {type(valid_locs).__name__}")
    
    test_locs = ["amsterdam", "singapore", "berlin"]
    for loc in test_locs:
        is_valid = loc in valid_locs
        status = "FOUND" if is_valid else "NOT FOUND"
        print(f"  {loc:15} -> {status}")
    
    # Example 7: Primary Datacenters (Netherlands)
    print("\n7. Primary Datacenters (Netherlands)")
    print("-" * 70)
    
    nl_locations = LocationsHandler.get_locations_by_region(RegionMeta.NETHERLANDS)
    print(f"Netherlands datacenters: {', '.join(nl_locations)}")
    print("These are your primary production locations!")
    
    # Example 8: CDN Edge Zones
    print("\n8. CDN Edge Zones (Global Distribution)")
    print("-" * 70)
    
    cdn_locations = LocationsHandler.get_locations_by_region(RegionMeta.CDN_EDGE)
    print(f"CDN Edge zones: {', '.join(cdn_locations)}")
    print("Use these for global content distribution!")
    
    print("\n" + "=" * 70)
    print(f"Summary: {len(locations)} locations across {len(regions)} regions")

