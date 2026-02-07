# Test Examples

Testing patterns and validation examples. These examples show how to test resource handlers, validate locations, and ensure data integrity.

## Files in This Folder

### `test_resource_group_big_3.py`
**Complete testing patterns for the "Big 3" handler features.**

A comprehensive test suite demonstrating:
- Creation and validation of resources
- Pydantic schema validation with custom validators
- Provisioning state lifecycle management
- Automatic timestamp tracking (createdTime, modifiedTime, createdBy, modifiedBy)
- Subscription-scoped uniqueness enforcement
- Convenience methods (create_from_properties, get_by_name, list_by_subscription)

**Time to complete:** ~20 minutes  
**Prerequisites:** Understanding of `intermediate/big_3_examples.py`  
**5 Test Cases:**
1. **Creation & Validation** - Test valid/invalid resources
2. **Timestamps on Creation** - Verify audit trail
3. **State Transitions** - Test lifecycle management
4. **Subscription Scoping** - Test uniqueness boundaries
5. **Convenience Methods** - Test helper functions

**Run it:**
```bash
python test_resource_group_big_3.py
```

**Expected output:**
```
======================================================================
TEST 1: Resource Group Creation with Validation
======================================================================

[->] Creating resource group 'prod-rg' in eastus...
[OK] Created: /subscriptions/sub-prod-001/resourceGroups/prod-rg
    State: Succeeded
    Location: eastus
    Created by: admin@company.com
    Created at: 2025-11-15T10:30:00Z
    Tags: {'env': 'production', 'team': 'platform'}
[OK] All Big 3 features present!

[->] Attempting to create RG with invalid location...
[OK] Validation caught: Location must be one of...

[->] Attempting to create duplicate RG in same subscription...
[OK] Correctly blocked duplicate: Resource already exists

======================================================================
TEST SUMMARY
======================================================================

OK PASS: Creation & Validation
OK PASS: Timestamps on Creation
OK PASS: State Management
OK PASS: Subscription Scoping
OK PASS: Convenience Methods

Total: 5/5 tests passed

[SUCCESS] ResourceGroupHandler with Big 3 is fully functional!
```

**Key test patterns:**

```python
# Test 1: Validation
handler = ResourceGroupHandler(storage)
try:
    handler.create_resource("bad-rg", {"location": "invalid-region"}, ...)
except ValueError as e:
    assert "not a valid Azure location" in str(e)

# Test 2: Timestamps
resource_id, config = handler.create_resource(...)
assert config['createdTime'] is not None
assert config['createdBy'] == "admin@company.com"

# Test 3: State Management
assert config['provisioning_state'] == 'Succeeded'
deleted = handler.delete_resource(...)
assert deleted is True

# Test 4: Subscription Scoping
# Create in sub-001
handler.create_resource("shared-rg", {...}, {...}, {"subscription_id": "sub-001"})
# Create in sub-002 with same name - allowed
handler.create_resource("shared-rg", {...}, {...}, {"subscription_id": "sub-002"})
# Create duplicate in sub-001 - blocked
handler.create_resource("shared-rg", {...}, {...}, {"subscription_id": "sub-001"})
```

### `test_itl_locations.py`
**Location validation using ITL's 27 datacenters.**

Demonstrates:
- ITL location validation (27 locations across multiple regions)
- Regional organization (Netherlands primary, Europe, CDN Edge)
- Location lookup by region
- Fast O(1) location validation
- Pydantic schema integration
- Location metadata queries

**Time to complete:** ~10 minutes  
**Prerequisites:** None (standalone)  
**Concepts:**
- `ITLLocationsHandler` - Central location validator
- `ITLRegionMeta` - Region classification
- Regional datacenter organization
- CDN edge zone support
- Location metadata

**Run it:**
```bash
python test_itl_locations.py
```

**Expected output:**
```
ITL Locations Handler Examples

======================================================================

1. Validate a Location
----------------------------------------------------------------------
'amsterdam' is a valid location
'invalid-location' is not valid

2. Get All Valid Locations
----------------------------------------------------------------------
Total locations: 27
Locations: amsterdam, rotterdam, rotterdam-backup, ...

3. Get Locations by Region
----------------------------------------------------------------------
Available regions: NETHERLANDS, EUROPE, CDN_EDGE, ...

  NETHERLANDS: amsterdam, rotterdam, rotterdam-backup
  EUROPE: london, frankfurt, brussels, ...
  CDN_EDGE: cdn-london, cdn-paris, cdn-amsterdam, ...

4. Get Region for Location
----------------------------------------------------------------------
  amsterdam           -> NETHERLANDS
  eastus              -> EUROPE
  cdn-london          -> CDN_EDGE

5. Using in Pydantic Schema
----------------------------------------------------------------------
Created deployment:
    Name: app-v1
    Location: amsterdam
    Environment: production

  Trying with invalid location...
Validation error: Location must be one of...

Valid locations: amsterdam, rotterdam, london, frankfurt, ...

6. Fast Location Lookup (O(1))
----------------------------------------------------------------------
Valid locations set: set
  amsterdam       -> FOUND
  singapore       -> NOT FOUND
  berlin          -> FOUND

7. Primary Datacenters (Netherlands)
----------------------------------------------------------------------
Netherlands datacenters: amsterdam, rotterdam, rotterdam-backup
These are your primary production locations!

8. CDN Edge Zones (Global Distribution)
----------------------------------------------------------------------
CDN Edge zones: cdn-london, cdn-paris, cdn-amsterdam, ...
Use these for global content distribution!

======================================================================
Summary: 27 locations across 6 regions
```

**Key patterns:**

```python
# Validate a location
if ITLLocationsHandler.is_valid("amsterdam"):
    print("Valid location")

# Get all locations
locations = ITLLocationsHandler.get_valid_locations()

# Get locations by region
nl_locs = ITLLocationsHandler.get_locations_by_region(ITLRegionMeta.NETHERLANDS)
cdn_locs = ITLLocationsHandler.get_locations_by_region(ITLRegionMeta.CDN_EDGE)

# Fast lookup (O(1))
valid_set = ITLLocationsHandler.get_valid_locations_set()
is_valid = "amsterdam" in valid_set

# In Pydantic schema
class DeploymentSchema(BaseModel):
    location: str
    
    @validator('location')
    def validate_location(cls, v):
        return ITLLocationsHandler.validate_location(v)
```

## ITL Location Reference

### Netherlands (Primary Production)
- `amsterdam` - Primary datacenter
- `rotterdam` - Secondary datacenter
- `rotterdam-backup` - Tertiary datacenter

### Europe (Regional)
- `london` - UK region
- `frankfurt` - Germany region
- `brussels` - Belgium region
- `paris` - France region
- `stockholm` - Sweden region
- `zurich` - Switzerland region

### CDN Edge Zones (Global Distribution)
- `cdn-london` - UK edge
- `cdn-paris` - France edge
- `cdn-amsterdam` - Benelux edge
- `cdn-frankfurt` - Central Europe edge
- `cdn-singapore` - Asia-Pacific edge
- `cdn-sydney` - Oceania edge

### On-Premise / Local
- Custom regional datacenters
- Private deployments

## Testing Best Practices

### Pattern 1: Assertion Patterns

```python
# Creation assertions
assert resource_id is not None
assert config['provisioning_state'] == 'Succeeded'

# Validation assertions
try:
    handler.create_resource("invalid", {...}, ...)
    assert False, "Should have raised ValueError"
except ValueError as e:
    assert "specific message" in str(e)

# State assertion
assert config['createdBy'] == "expected_user"
assert config['createdTime'] is not None
```

### Pattern 2: Scope Testing

```python
# Test subscription scoping
storage = {}
handler = ResourceGroupHandler(storage)

# Create in sub-001
id1 = handler.create_resource("name", {...}, {...}, {"subscription_id": "sub-001"})

# Same name in sub-002 - should succeed
id2 = handler.create_resource("name", {...}, {...}, {"subscription_id": "sub-002"})

# Duplicate in sub-001 - should fail
try:
    handler.create_resource("name", {...}, {...}, {"subscription_id": "sub-001"})
    assert False, "Should have raised ValueError"
except ValueError:
    pass  # Expected
```

### Pattern 3: Validation Testing

```python
# Test with valid data
try:
    result = handler.create_resource(
        "valid-name",
        {"location": "amsterdam"},  # Valid location
        ...
    )
    assert result is not None
except:
    assert False, "Valid data should not raise"

# Test with invalid data
try:
    result = handler.create_resource(
        "x",  # Too short
        {"location": "invalid"},  # Invalid location
        ...
    )
    assert False, "Invalid data should raise ValueError"
except ValueError as e:
    assert "must be" in str(e) or "not valid" in str(e)
```

## Common Test Scenarios

### Scenario 1: Validate Resource Creation
```python
# Create with valid data
resource_id, config = handler.create_resource(...)

# Assert all Big 3 features
assert config['provisioning_state'] == 'Succeeded'
assert config['createdBy'] == "admin@company.com"
assert config['createdTime'] is not None
```

### Scenario 2: Test Duplicate Detection
```python
# Create first
handler.create_resource("my-resource", {...}, {...}, scope1)

# Try to create duplicate
try:
    handler.create_resource("my-resource", {...}, {...}, scope1)
    assert False, "Should block duplicate"
except ValueError:
    pass  # Expected
```

### Scenario 3: Test Location Validation
```python
# Valid location
handler.create_resource("rg", {"location": "amsterdam"}, ...)  # OK

# Invalid location
try:
    handler.create_resource("rg", {"location": "invalid"}, ...)
    assert False, "Should reject invalid location"
except ValueError:
    pass  # Expected
```

### Scenario 4: Test Timestamp Tracking
```python
resource_id, config = handler.create_resource(
    "resource",
    {...},
    {...},
    {"user_id": "alice@company.com"}
)

# Verify audit trail
assert config['createdBy'] == "alice@company.com"
assert config['createdTime'] is not None
assert config['createdTime'].endswith('Z')  # ISO 8601
```

## Running Tests

### Run all tests in folder
```bash
cd examples/tests
python test_resource_group_big_3.py
python test_itl_locations.py
```

### Run specific test class
```bash
python -m pytest test_resource_group_big_3.py::TestResourceGroupHandler -v
```

### Run with coverage
```bash
python -m pytest --cov=itl_controlplane_sdk examples/tests/ -v
```

## Next Steps

- **Review Test Output**: Understand what each test is checking
- **Run Examples**: Execute the test files to see assertions in action
- **Write Your Own**: Create tests for your custom handlers
- **Study Patterns**: Look at how tests structure validation and state checks

## Learning Path

1. `quickstart.py` - Basic SDK
2. `big_3_examples.py` - Features to test
3. **You are here** - How to test those features
4. Review `test_resource_group_big_3.py` line by line
5. Review `test_itl_locations.py` line by line
6. Apply patterns to your own code

## Troubleshooting

### Import errors
Make sure pytest can find the SDK:
```bash
pip install -e ../..  # Install SDK in editable mode
```

### Location validation failures
Check that locations match case-insensitively:
```python
# These are all valid:
"amsterdam"  # lowercase OK
"Amsterdam"  # uppercase OK
"AMSTERDAM"  # all caps OK
```

### Timestamp format issues
Timestamps are always in ISO 8601 format with Z suffix:
```python
# Valid: "2025-11-15T10:30:00Z"
# Invalid: "2025-11-15T10:30:00"  (missing Z)
# Invalid: "11/15/2025 10:30 AM"  (wrong format)
```
