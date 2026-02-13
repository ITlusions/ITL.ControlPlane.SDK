# locations Schema - Custom Location Validation

## Status: ✅ CREATED AND READY

You now have a custom locations schema based on your `DEFAULT_LOCATIONS` in models.py.

---

## What Was Created

### File: `itl_locations.py` (330 lines)

**Location:** `src/itl_controlplane_sdk/providers/itl_locations.py`

**Components:**

1. **Location Enum** - 24 valid locations
   ```python
   class Location(str, Enum):
       # Netherlands (Primary Datacenters)
       AMSTERDAM = "amsterdam"
       ROTTERDAM = "rotterdam"
       ALMERE = "almere"
       
       # United States
       EAST_US = "eastus"
       WEST_US = "westus"
       CENTRAL_US = "centralus"
       
       # Europe Cities
       GERMANY_WESTCENTRAL = "germanywestcentral"
       FRANCE_CENTRAL = "francecentral"
       SWITZERLAND_NORTH = "switzerlandnorth"
       SWEDEN_CENTRAL = "swedencentral"
       ITALY_NORTH = "italynorth"
       POLAND_CENTRAL = "polandcentral"
       
       # CDN Edge Zones
       CDN_AMSTERDAM = "cdn-amsterdam"
       CDN_FRANKFURT = "cdn-frankfurt"
       CDN_LONDON = "cdn-london"
       CDN_PARIS = "cdn-paris"
       CDN_STOCKHOLM = "cdn-stockholm"
       CDN_ZURICH = "cdn-zurich"
       
       # Others
       ... (and more)
   ```

2. **RegionMeta Enum** - 6 region groups
   ```python
   class RegionMeta(str, Enum):
       UNITED_STATES = "United States"
       UNITED_KINGDOM = "United Kingdom"
       EUROPE = "Europe"
       NETHERLANDS = "Netherlands"        # Your primary datacenters
       ASIA_PACIFIC = "Asia Pacific"
       CDN_EDGE = "CDN Edge"             # Global distribution
   ```

3. **LocationsHandler Class** - 7 utility methods
   - `validate_location(v)` - Validate with clear error messages
   - `is_valid(location)` - Quick check
   - `get_valid_locations()` - List all 24 locations
   - `get_valid_locations_set()` - Set for O(1) lookup
   - `get_locations_by_region(region)` - Filter by region
   - `get_available_regions()` - List all 6 regions
   - `get_region_for_location(location)` - Get region for location

---

## Your Locations (24 Total)

### Netherlands (3 - Primary Datacenters)
- almere
- amsterdam
- rotterdam

### Europe (8 - Major Cities)
- francecentral
- germanywestcentral
- italynorth
- northeurope
- polandcentral
- swedencentral
- switzerlandnorth
- westeurope

### United States (3)
- centralus
- eastus
- westus

### United Kingdom (2)
- uksouth
- ukwest

### Asia Pacific (2)
- eastasia
- southeastasia

### CDN Edge Zones (6 - Global Distribution)
- cdn-amsterdam
- cdn-frankfurt
- cdn-london
- cdn-paris
- cdn-stockholm
- cdn-zurich

---

## How to Use

### 1. Basic Validation in Pydantic Schema

```python
from pydantic import BaseModel, validator, Field
from itl_controlplane_sdk.providers import LocationsHandler

class DeploymentRequest(BaseModel):
    name: str
    location: str
    environment: str
    
    @validator('location')
    def validate_location(cls, v):
        return LocationsHandler.validate_location(v)

# Usage
deployment = DeploymentRequest(
    name="app-v1",
    location="amsterdam",
    environment="production"
)
# ✓ Valid - amsterdam is a valid location

deployment = DeploymentRequest(
    name="app-v1",
    location="singapore",
    environment="production"
)
# ✗ Error: 'singapore' is not a valid location
# Valid options: almere, amsterdam, cdn-amsterdam, ... (24 total)
```

### 2. Check if Location is Valid

```python
from itl_controlplane_sdk.providers import LocationsHandler

if LocationsHandler.is_valid("amsterdam"):
    print("Valid location")
else:
    print("Invalid location")
```

### 3. Get All Valid Locations

```python
locations = LocationsHandler.get_valid_locations()
# Returns: ['almere', 'amsterdam', 'cdn-amsterdam', ..., 'westus']
# (24 locations, sorted alphabetically)
```

### 4. Get Locations by Region

```python
from itl_controlplane_sdk.providers import RegionMeta

# Get Netherlands locations (primary datacenters)
nl_locations = LocationsHandler.get_locations_by_region(RegionMeta.NETHERLANDS)
# Returns: ['almere', 'amsterdam', 'rotterdam']

# Get CDN edge zones (global distribution)
cdn_locations = LocationsHandler.get_locations_by_region(RegionMeta.CDN_EDGE)
# Returns: ['cdn-amsterdam', 'cdn-frankfurt', 'cdn-london', ...]

# Get all Europe locations
eu_locations = LocationsHandler.get_locations_by_region(RegionMeta.EUROPE)
# Returns: ['francecentral', 'germanywestcentral', ...]
```

### 5. Get Region for a Location

```python
region = LocationsHandler.get_region_for_location("amsterdam")
# Returns: "Netherlands"

region = LocationsHandler.get_region_for_location("cdn-london")
# Returns: "CDN Edge"
```

### 6. Fast O(1) Lookup

```python
# For performance-critical code
valid_locations = LocationsHandler.get_valid_locations_set()

if user_location in valid_locations:  # O(1) lookup
    process_deployment(user_location)
```

### 7. List All Available Regions

```python
regions = LocationsHandler.get_available_regions()
# Returns: ['Asia Pacific', 'CDN Edge', 'Europe', 'Netherlands', 'United Kingdom', 'United States']
```

---

## Complete Example

```python
from pydantic import BaseModel, validator, Field
from itl_controlplane_sdk.providers import (
    LocationsHandler,
    RegionMeta,
)

class DatacenterDeployment(BaseModel):
    """Deployment request to ITL datacenters"""
    
    name: str = Field(..., description="Deployment name")
    location: str = Field(..., description="location")
    replicas: int = Field(default=1, description="Number of replicas")
    is_primary: bool = Field(default=False, description="Is primary deployment")
    
    @validator('location')
    def validate_location(cls, v):
        """Validate against all 24 locations"""
        return LocationsHandler.validate_location(v)

# Create deployment in Amsterdam (primary datacenter)
deployment = DatacenterDeployment(
    name="production-app",
    location="amsterdam",
    replicas=3,
    is_primary=True
)

print(f"Deploying to: {deployment.location}")
print(f"Region: {LocationsHandler.get_region_for_location(deployment.location)}")
# Output:
# Deploying to: amsterdam
# Region: Netherlands

# Get all Netherlands replicas
nl_locations = LocationsHandler.get_locations_by_region(RegionMeta.NETHERLANDS)
print(f"Available primary datacenters: {', '.join(nl_locations)}")
# Output:
# Available primary datacenters: almere, amsterdam, rotterdam
```

---

## Comparison: Azure vs ITL

| Feature | Azure | ITL |
|---------|-------|-----|
| **File** | `locations.py` | `itl_locations.py` |
| **Enum** | `AzureLocation` | `Location` |
| **Region Enum** | `AzureRegionMeta` | `RegionMeta` |
| **Handler** | `LocationsHandler` | `LocationsHandler` |
| **Locations** | 30+ global regions | 24 locations (your infrastructure) |
| **Primary Use** | Cloud-agnostic validation | Your specific datacenters |
| **Key Regions** | US, Europe, Asia, Gov, China | Netherlands (primary), Europe, US, Asia, CDN |

---

## Extending locations

To add new locations (e.g., a new datacenter):

### Step 1: Add to Location enum
```python
class Location(str, Enum):
    # ... existing locations ...
    SINGAPORE = "singapore"
```

### Step 2: Add to LOCATION_TO_REGION mapping
```python
LOCATION_TO_REGION: Dict[str, RegionMeta] = {
    # ... existing mappings ...
    Location.SINGAPORE: RegionMeta.ASIA_PACIFIC,
}
```

### Step 3: Done!
All handlers automatically support the new location:
- `validate_location("singapore")` ✓
- `get_valid_locations()` includes "singapore"
- `get_locations_by_region(RegionMeta.ASIA_PACIFIC)` includes "singapore"
- Pydantic schemas automatically validate against it

---

## Error Messages

When validation fails, users see all valid options:

```python
LocationsHandler.validate_location("berlin")

# Error:
# ValueError: 'berlin' is not a valid location. 
# Valid options: almere, amsterdam, cdn-amsterdam, cdn-frankfurt, cdn-london, 
# cdn-paris, cdn-stockholm, cdn-zurich, centralus, eastasia, eastus, 
# francecentral, germanywestcentral, italynorth, northeurope, polandcentral, 
# rotterdam, southeastasia, swedencentral, switzerlandnorth, uksouth, ukwest, 
# westeurope, westus
```

---

## Integration with Your Schemas

Update your resource schemas to use locations:

```python
from pydantic import BaseModel, validator
from itl_controlplane_sdk.providers import LocationsHandler

# For Resource Groups
class ResourceGroupSchema(BaseModel):
    location: str
    
    @validator('location')
    def validate_location(cls, v):
        return LocationsHandler.validate_location(v)

# For Virtual Machines
class VirtualMachineSchema(BaseModel):
    location: str
    
    @validator('location')
    def validate_location(cls, v):
        return LocationsHandler.validate_location(v)

# For Storage Accounts
class StorageAccountSchema(BaseModel):
    location: str
    
    @validator('location')
    def validate_location(cls, v):
        return LocationsHandler.validate_location(v)
```

---

## Files Created/Modified

| File | Status | Changes |
|------|--------|---------|
| `src/itl_controlplane_sdk/providers/itl_locations.py` | ✅ NEW | Created 330-line module with Location enum, RegionMeta, and LocationsHandler |
| `src/itl_controlplane_sdk/providers/__init__.py` | ✅ UPDATED | Added imports for locations exports |
| `examples/test_itl_locations.py` | ✅ NEW | Example usage with 8 different scenarios |

---

## Summary

You now have a custom locations schema that:
- ✅ Validates against your 24 actual locations (from models.py)
- ✅ Groups locations by region (Netherlands, Europe, US, Asia, CDN)
- ✅ Uses the same pattern as Azure locations (easy to understand)
- ✅ Type-safe with enums
- ✅ Fast O(1) lookups
- ✅ Clear error messages
- ✅ Easy to extend for new datacenters
- ✅ Ready to use in all resource schemas

**Ready to use:** `from itl_controlplane_sdk.providers import LocationsHandler`

