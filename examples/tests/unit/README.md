# Tests - Unit Level

Unit testing SDK components and handlers.

## Files
- **`test_itl_locations.py`** - Unit tests for ITL location utilities
  - Location validation
  - Region mapping
  - Code lookups
  - Format validation

**Run:** `pytest tests/unit/` or `pytest tests/unit/test_itl_locations.py`

## Unit Testing Concepts

Unit tests verify individual components:
- Validation functions
- Formatting utilities
- Data transformations
- Error handling

### Test Structure

```python
import pytest
from itl_control_plane_sdk import validate_location

class TestLocationValidation:
    def test_valid_location(self):
        """Valid locations should pass"""
        assert validate_location("westeurope") == True
    
    def test_invalid_location(self):
        """Invalid locations should fail"""
        assert validate_location("moonbase") == False
    
    def test_case_insensitive(self):
        """Location validation should be case-insensitive"""
        assert validate_location("WestEurope") == True
```

### Test Patterns

**Pattern 1: Positive Cases**
```python
def test_create_valid_resource(self):
    handler = ResourceHandler()
    result = handler.create_resource("valid-name", {...})
    assert result is not None
```

**Pattern 2: Negative Cases**
```python
def test_create_invalid_name(self):
    handler = ResourceHandler()
    with pytest.raises(ValueError):
        handler.create_resource("invalid-@name", {...})
```

**Pattern 3: Edge Cases**
```python
def test_create_min_length_name(self):
    handler = ResourceHandler()
    result = handler.create_resource("a", {...})  # Min = 1 char
    assert result is not None

def test_create_max_length_name(self):
    handler = ResourceHandler()
    result = handler.create_resource("x" * 80, {...})  # Max = 80
    assert result is not None
```

## Utility Testing Example

```python
import pytest
from itl_control_plane_sdk import format_resource_id

class TestResourceIDFormatting:
    def test_format_resource_id_complete(self):
        """Format complete resource ID"""
        rid = format_resource_id(
            subscription="sub-123",
            resource_group="app-rg",
            resource_type="virtualMachines",
            resource_name="web-vm"
        )
        
        expected = "/subscriptions/sub-123/resourceGroups/app-rg/providers/Microsoft.Compute/virtualMachines/web-vm"
        assert rid == expected
    
    def test_format_resource_id_with_parent(self):
        """Format resource ID with parent"""
        rid = format_resource_id(
            subscription="sub-123",
            resource_group="app-rg",
            parent_type="servers",
            parent_name="db-server",
            resource_type="databases",
            resource_name="appdb"
        )
        
        expected = "/subscriptions/sub-123/resourceGroups/app-rg/providers/Microsoft.Sql/servers/db-server/databases/appdb"
        assert rid == expected
```

## Prerequisites
- Install pytest: `pip install pytest`
- Understand SDK basics (see [core/beginner/](../../core/beginner/))

## Next Steps
→ **[Integration](../integration/)** - Test full workflows
