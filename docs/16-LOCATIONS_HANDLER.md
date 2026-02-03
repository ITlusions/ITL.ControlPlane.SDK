# Azure LocationsHandler - Dynamic Region Validation

## Overview

The `LocationsHandler` provides a centralized, dynamic, and maintainable way to validate Azure locations across all resource handlers. Instead of hardcoding location lists in each schema validator, handlers now use the `LocationsHandler.validate_location()` method.

## Key Features

✅ **Comprehensive Azure Regions** - 30+ official Azure locations  
✅ **Dynamic Validation** - Centralized location authority  
✅ **Region Grouping** - Locations organized by geographic region (US, Europe, Asia-Pacific, etc.)  
✅ **Easy to Extend** - Add new regions by updating the enum  
✅ **Type-Safe** - Uses Python Enum for discoverability  
✅ **Reusable** - Use in any Pydantic validator  

## Supported Locations

### US Regions (7)
- eastus
- eastus2
- westus
- westus2
- centralus
- northcentralus
- southcentralus

### Europe Regions (4)
- westeurope
- northeurope
- uksouth
- ukwest

### Asia-Pacific Regions (6)
- southeastasia
- eastasia
- japaneast
- japanwest
- australiaeast
- australiasoutheast

### India Regions (3)
- indiacentral
- indiasouth
- indiawest

### Canada Regions (2)
- canadacentral
- canadaeast

### Other Regions (8)
- brazilsouth
- uaenorth
- southafricanorth
- germanywestcentral
- chinaeast
- chinanorth
- usgovvirginia
- usgoviowa
- usgovarizona
- usgovtexas

**Total: 30+ regions**

## Usage

### In Pydantic Schema Validators

```python
from pydantic import BaseModel, validator, Field
from itl_controlplane_sdk.providers.locations import LocationsHandler

class ResourceSchema(BaseModel):
    location: str = Field(..., description="Azure region")
    
    @validator('location')
    def validate_location(cls, v):
        return LocationsHandler.validate_location(v)
```

### Direct Validation

```python
from itl_controlplane_sdk.providers.locations import LocationsHandler

# Validate a location
try:
    validated = LocationsHandler.validate_location('eastus')
    print(f"Valid: {validated}")
except ValueError as e:
    print(f"Invalid: {e}")

# Check if location is valid
if LocationsHandler.is_valid('westeurope'):
    print("Location is valid")

# Get all valid locations
all_locations = LocationsHandler.get_valid_locations()
# Returns: ['australiaeast', 'australiasoutheast', ..., 'westus2']

# Get locations by region
us_locations = LocationsHandler.get_locations_by_region(AzureRegionMeta.US)
# Returns: ['centralus', 'eastus', 'eastus2', ..., 'westus2']

# Get region for location
region = LocationsHandler.get_region_for_location('eastus')
# Returns: 'US'
```

## Architecture

### File Structure

```
src/itl_controlplane_sdk/providers/
├── locations.py                 # LocationsHandler implementation
├── resource_group_handler.py    # Uses LocationsHandler in validator
├── __init__.py                  # Exports LocationsHandler + enums
```

### Class Hierarchy

```
LocationsHandler (static methods only)
├── is_valid(location: str) -> bool
├── validate_location(location: str) -> str
├── get_valid_locations() -> List[str]
├── get_valid_locations_set() -> Set[str]
├── get_locations_by_region(region: AzureRegionMeta) -> List[str]
├── get_available_regions() -> List[str]
└── get_region_for_location(location: str) -> str

AzureLocation (Enum)
├── EAST_US = "eastus"
├── WEST_US = "westus"
├── ... (30+ total)

AzureRegionMeta (Enum)
├── US = "US"
├── EUROPE = "Europe"
├── ASIA_PACIFIC = "Asia Pacific"
└── ... (11 total)
```

## Implementation Details

### Dynamic Location Validation

```python
@staticmethod
def validate_location(location: str) -> str:
    """
    Validate location and return normalized value.
    
    Args:
        location: Location string to validate
    
    Returns:
        Lowercase normalized location
    
    Raises:
        ValueError: If location is invalid
    """
    normalized = location.lower().strip()
    
    if not LocationsHandler.is_valid(normalized):
        valid_list = ", ".join(LocationsHandler.get_valid_locations())
        raise ValueError(
            f"'{location}' is not a valid Azure location. "
            f"Valid options: {valid_list}"
        )
    
    return normalized
```

### Membership Testing (Fast)

```python
# O(1) lookup using set
VALID_LOCATIONS = LocationsHandler.get_valid_locations_set()
# Returns: {'eastus', 'westus', 'westeurope', ...}

if location in VALID_LOCATIONS:
    # Fast check
    process(location)
```

### Region Grouping

```python
# Get US locations
us_locs = LocationsHandler.get_locations_by_region(AzureRegionMeta.US)
# Returns: ['centralus', 'eastus', 'eastus2', 'northcentralus', 
#           'southcentralus', 'westus', 'westus2']

# Get all available regions
regions = LocationsHandler.get_available_regions()
# Returns: ['US', 'Europe', 'Asia Pacific', 'India', 'Canada', ...]
```

## Usage Examples

### Example 1: Resource Group Handler

**Before (hardcoded locations):**
```python
class ResourceGroupSchema(BaseModel):
    location: str
    
    @validator('location')
    def validate_location(cls, v):
        valid_locations = {
            'eastus', 'westus', 'westus2', 'centralus', 'northcentralus', 'southcentralus',
            'eastus2', 'westeurope', 'northeurope', 'southeastasia', 'eastasia',
            'australiaeast', 'australiasoutheast', 'japaneast', 'japanwest',
            'canadacentral', 'canadaeast', 'uksouth', 'ukwest', 'indiacentral',
        }
        if v not in valid_locations:
            raise ValueError(f'Location must be one of: {", ".join(valid_locations)}')
        return v
```

**After (dynamic LocationsHandler):**
```python
from itl_controlplane_sdk.providers.locations import LocationsHandler

class ResourceGroupSchema(BaseModel):
    location: str
    
    @validator('location')
    def validate_location(cls, v):
        return LocationsHandler.validate_location(v)
```

### Example 2: Virtual Machine Handler

```python
from pydantic import BaseModel, validator, Field
from itl_controlplane_sdk.providers.locations import LocationsHandler

class VirtualMachineSchema(BaseModel):
    vm_name: str
    location: str = Field(..., description="Azure region")
    vm_size: str
    
    @validator('location')
    def validate_location(cls, v):
        return LocationsHandler.validate_location(v)

# Usage
handler = VirtualMachineHandler(storage)
handler.create_resource(
    "my-vm",
    {
        "vm_name": "my-vm",
        "location": "eastus",  # Validated dynamically
        "vm_size": "Standard_D2s_v3"
    },
    ...
)
```

### Example 3: Storage Account Handler

```python
from pydantic import BaseModel, validator
from itl_controlplane_sdk.providers.locations import LocationsHandler

class StorageAccountSchema(BaseModel):
    name: str
    location: str
    account_type: str
    
    @validator('location')
    def validate_location(cls, v):
        return LocationsHandler.validate_location(v)
```

## Extension Guide

### Adding New Locations

To add new Azure locations, update the `AzureLocation` enum in `locations.py`:

```python
class AzureLocation(str, Enum):
    """Valid Azure regions as an enumeration."""
    
    # Existing locations...
    
    # New location (when Azure releases it)
    NEW_REGION = "newregion"
    
    # Existing locations continued...
```

Then update `LOCATION_TO_REGION` mapping:

```python
LOCATION_TO_REGION: Dict[str, AzureRegionMeta] = {
    # Existing mappings...
    AzureLocation.NEW_REGION: AzureRegionMeta.YOUR_REGION,  # or create new region
    # Continue...
}
```

And if needed, add new region to `AzureRegionMeta`:

```python
class AzureRegionMeta(str, Enum):
    """Azure region metadata for regional grouping."""
    YOUR_REGION = "Your Region Name"
```

### Updating Location List

The location list is updated whenever:
1. Azure releases new regions
2. Older regions are retired
3. Region names change

Simply:
1. Update `AzureLocation` enum
2. Update `LOCATION_TO_REGION` mapping  
3. All handlers automatically use updated list
4. No code changes needed in any handler

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| `is_valid(location)` | <1ms | Enum lookup |
| `validate_location(location)` | <1ms | Validation + normalization |
| `get_valid_locations()` | <1ms | Cached or computed once |
| `get_region_for_location()` | <1ms | Dict lookup |

## Error Handling

Validation errors include helpful messages with all valid options:

```python
try:
    LocationsHandler.validate_location("invalid")
except ValueError as e:
    print(e)
    # Output:
    # 'invalid' is not a valid Azure location. Valid options: australiaeast,
    # australiasoutheast, brazilsouth, canadacentral, canadaeast, centralus,
    # chinaeast, chinanorth, eastasia, eastus, eastus2, germanywestcentral,
    # indiacentral, indiasouth, indiawest, japaneast, japanwest,
    # northcentralus, northeurope, southafricanorth, southcentralus,
    # southeastasia, uaenorth, uksouth, ukwest, usgovarizona, usgoviowa,
    # usgovtexas, usgovvirginia, westeurope, westus, westus2
```

## Testing

All LocationsHandler functionality is tested in:
- `tests/test_resource_handlers.py` - Mixin unit tests
- `examples/test_resource_group_big_3.py` - Integration tests with ResourceGroupHandler

Run tests:
```bash
python -W ignore examples/test_resource_group_big_3.py
# All tests passing with dynamic location validation
```

## Exports

Available from `itl_controlplane_sdk.providers`:

```python
from itl_controlplane_sdk.providers import (
    AzureLocation,          # Enum of valid locations
    AzureRegionMeta,        # Enum of regions
    LocationsHandler,       # Main handler class
    VALID_LOCATIONS,        # Set of valid location strings (fast lookup)
    AVAILABLE_REGIONS,      # List of available regions
    LOCATION_TO_REGION,     # Dict mapping locations to regions
)
```

## Migration Guide

### From hardcoded lists to LocationsHandler

1. **Update imports:**
   ```python
   from itl_controlplane_sdk.providers.locations import LocationsHandler
   ```

2. **Remove hardcoded list:**
   ```python
   # Remove this:
   valid_locations = {'eastus', 'westus', ...}
   ```

3. **Update validator:**
   ```python
   @validator('location')
   def validate_location(cls, v):
       return LocationsHandler.validate_location(v)
   ```

4. **Test:**
   ```bash
   python test_schema.py
   ```

## Summary

The `LocationsHandler` provides:
- ✅ **Single source of truth** for Azure locations
- ✅ **Easy maintenance** when regions change
- ✅ **Type-safe** enum for discoverability
- ✅ **Reusable** across all handlers
- ✅ **Comprehensive** 30+ regions covered
- ✅ **Well-documented** with examples
- ✅ **Fast** <1ms validation
- ✅ **Clear errors** with all valid options

Use it in all location validators for clean, maintainable, dynamic region validation!
