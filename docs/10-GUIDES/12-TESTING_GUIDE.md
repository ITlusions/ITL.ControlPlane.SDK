# Testing Guide: Unit, Integration, and E2E Tests

Complete testing strategy for SDK-based resource providers.

---

## Testing Architecture

```
Your Provider
├── Unit Tests (models, handlers, validation)
├── Integration Tests (SDK + storage layer)
└── E2E Tests (full provider + API Gateway)
```

---

## Unit Testing: Handler and Logic Tests

### Test Handler Scoping

```python
# tests/test_handler_scoping.py
import pytest
from itl_controlplane_sdk.providers import ScopedResourceHandler, UniquenessScope

class TestVMHandler(ScopedResourceHandler):
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION, UniquenessScope.RESOURCE_GROUP]
    RESOURCE_TYPE = "virtualmachines"

@pytest.fixture
def handler():
    return TestVMHandler({})

def test_creates_resource_with_correct_scope(handler):
    """Resource ID includes subscription and RG"""
    resource_id, data = handler.create_resource(
        "vm-001",
        {"size": "Standard_D2s_v3"},
        "ITL.Compute/virtualmachines",
        {
            "subscription_id": "sub-123",
            "resource_group": "rg-prod"
        }
    )
    
    assert "sub-123" in resource_id
    assert "rg-prod" in resource_id

def test_detects_duplicate_resources(handler):
    """Creating same resource twice raises ValueError"""
    context = {
        "subscription_id": "sub-123",
        "resource_group": "rg-prod"
    }
    
    # First creation succeeds
    handler.create_resource("vm-001", {}, "ITL.Compute/virtualmachines", context)
    
    # Second creation fails
    with pytest.raises(ValueError, match="already exists"):
        handler.create_resource("vm-001", {}, "ITL.Compute/virtualmachines", context)

def test_allows_same_name_different_scopes(handler):
    """Same name OK if in different RGs"""
    context1 = {"subscription_id": "sub-123", "resource_group": "rg-prod"}
    context2 = {"subscription_id": "sub-123", "resource_group": "rg-test"}
    
    # Both succeed
    id1, _ = handler.create_resource("vm-001", {}, "ITL.Compute/virtualmachines", context1)
    id2, _ = handler.create_resource("vm-001", {}, "ITL.Compute/virtualmachines", context2)
    
    assert id1 != id2
```

### Test Validation Handlers

```python
# tests/test_validation.py
import pytest
from pydantic import BaseModel, ValidationError
from itl_controlplane_sdk.providers import ValidatedResourceHandler

class VMProperties(BaseModel):
    size: str
    image: str

class TestValidationHandler(ValidatedResourceHandler):
    SCHEMA = VMProperties

def test_accepts_valid_properties():
    """Valid properties pass validation"""
    handler = TestValidationHandler({})
    
    valid_data = {"size": "Standard_D2s_v3", "image": "Ubuntu20.04"}
    resource_id, data = handler.create_resource("vm-001", valid_data)
    
    assert data["size"] == "Standard_D2s_v3"

def test_rejects_invalid_properties():
    """Invalid properties raise ValidationError"""
    handler = TestValidationHandler({})
    
    invalid_data = {"size": "Standard_D2s_v3"}  # Missing 'image'
    
    with pytest.raises(ValidationError):
        handler.create_resource("vm-001", invalid_data)
```

### Test State Transitions

```python
# tests/test_state_transitions.py
import pytest
from itl_controlplane_sdk import ProvisioningState
from itl_controlplane_sdk.providers import ProvisioningStateHandler

@pytest.fixture
def handler():
    return ProvisioningStateHandler({})

def test_starts_in_accepted_state(handler):
    """New resources start in Accepted state"""
    id, data = handler.create_resource("resource-001", {})
    assert data["provisioning_state"] == ProvisioningState.ACCEPTED

def test_transitions_accepted_to_provisioning(handler):
    """Can transition from Accepted to Provisioning"""
    id, data = handler.create_resource("resource-001", {})
    
    handler.transition_state(id, ProvisioningState.PROVISIONING)
    updated = handler.get_resource(id)
    
    assert updated["provisioning_state"] == ProvisioningState.PROVISIONING

def test_invalid_transition_raises_error(handler):
    """Invalid transitions raise error"""
    id, data = handler.create_resource("resource-001", {})
    
    # Can't go Accepted → Failed directly
    with pytest.raises(ValueError, match="Invalid transition"):
        handler.transition_state(id, ProvisioningState.FAILED)
```

---

## Integration Testing: Provider + Storage

### Test Complete Provider

```python
# tests/test_provider_integration.py
import pytest
from unittest.mock import AsyncMock, patch
from my_provider import MyProvider
from itl_controlplane_sdk import ResourceRequest, ProvisioningState

@pytest.fixture
async def provider():
    return MyProvider()

@pytest.mark.asyncio
async def test_create_resource_flow(provider):
    """Full create flow: Accepted → Provisioning → Succeeded"""
    
    request = ResourceRequest(
        resource_type="myresources",
        resource_name="resource-001",
        subscription_id="sub-123",
        resource_group="rg-prod",
        location="westus2",
        properties={"key": "value"},
        tags={"env": "prod"}
    )
    
    # Create
    response = await provider.create_or_update_resource(request)
    
    assert response.name == "resource-001"
    assert response.provisioning_state == ProvisioningState.ACCEPTED
    
    # Simulate async work
    await provider._complete_provisioning(response.id)
    
    # Get resource
    get_response = await provider.get_resource(request)
    
    assert get_response.provisioning_state == ProvisioningState.SUCCEEDED

@pytest.mark.asyncio
async def test_delete_resource(provider):
    """Delete removes resource"""
    
    # First create
    request = ResourceRequest(
        resource_type="myresources",
        resource_name="resource-001",
        subscription_id="sub-123",
        resource_group="rg-prod"
    )
    
    await provider.create_or_update_resource(request)
    
    # Then delete
    delete_response = await provider.delete_resource(request)
    
    # Should be gone
    with pytest.raises(Exception, match="not found"):
        await provider.get_resource(request)

@pytest.mark.asyncio
async def test_list_resources(provider):
    """List returns all resources in RG"""
    
    # Create multiple
    for i in range(3):
        request = ResourceRequest(
            resource_type="myresources",
            resource_name=f"resource-{i:03d}",
            subscription_id="sub-123",
            resource_group="rg-prod"
        )
        await provider.create_or_update_resource(request)
    
    # List
    list_request = ResourceRequest(
        subscription_id="sub-123",
        resource_group="rg-prod"
    )
    
    resources = await provider.list_resources(list_request)
    
    assert len(resources) == 3

@pytest.mark.asyncio
async def test_duplicate_resource_rejected(provider):
    """Creating same resource twice fails"""
    
    request = ResourceRequest(
        resource_type="myresources",
        resource_name="resource-001",
        subscription_id="sub-123",
        resource_group="rg-prod"
    )
    
    # First succeeds
    await provider.create_or_update_resource(request)
    
    # Second fails
    with pytest.raises(ValueError, match="already exists"):
        await provider.create_or_update_resource(request)

@pytest.mark.asyncio
async def test_validation_errors(provider):
    """Invalid properties rejected"""
    
    request = ResourceRequest(
        resource_type="myresources",
        resource_name="invalid@name",  # Invalid character
        subscription_id="sub-123",
        resource_group="rg-prod"
    )
    
    response = await provider.create_or_update_resource(request)
    
    assert response.provisioning_state == ProvisioningState.FAILED
    assert "invalid" in response.properties.get("error", "").lower()
```

---

## E2E Testing: Full API Flow

### Test via API Gateway

```python
# tests/test_e2e_api.py
import pytest
import httpx
from my_provider import MyProvider

@pytest.fixture(scope="session")
async def api_client():
    # Start provider + API Gateway
    provider = MyProvider()
    server = start_test_server(provider)
    
    client = httpx.AsyncClient()
    yield client
    
    await client.aclose()
    server.shutdown()

@pytest.mark.asyncio
async def test_create_via_api_gateway(api_client):
    """Create resource through API Gateway"""
    
    response = await api_client.put(
        "http://localhost:9050/subscriptions/sub-123/resourceGroups/rg-prod/providers/ITL.MyProvider/myresources/resource-001",
        json={
            "location": "westus2",
            "properties": {"key": "value"},
            "tags": {"env": "prod"}
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "resource-001"
    assert data["provisioning_state"] == "Accepted"

@pytest.mark.asyncio
async def test_get_via_api_gateway(api_client):
    """Get resource through API Gateway"""
    
    # Create first
    await api_client.put(
        "http://localhost:9050/subscriptions/sub-123/resourceGroups/rg-prod/providers/ITL.MyProvider/myresources/resource-001",
        json={"location": "westus2"}
    )
    
    # Get
    response = await api_client.get(
        "http://localhost:9050/subscriptions/sub-123/resourceGroups/rg-prod/providers/ITL.MyProvider/myresources/resource-001"
    )
    
    assert response.status_code == 200
    assert response.json()["name"] == "resource-001"

@pytest.mark.asyncio
async def test_list_via_api_gateway(api_client):
    """List resources through API Gateway"""
    
    # Create multiple
    for i in range(3):
        await api_client.put(
            f"http://localhost:9050/subscriptions/sub-123/resourceGroups/rg-prod/providers/ITL.MyProvider/myresources/resource-{i:03d}",
            json={"location": "westus2"}
        )
    
    # List
    response = await api_client.get(
        "http://localhost:9050/subscriptions/sub-123/resourceGroups/rg-prod/providers/ITL.MyProvider/myresources"
    )
    
    assert response.status_code == 200
    assert len(response.json()["value"]) >= 3

@pytest.mark.asyncio
async def test_error_handling(api_client):
    """Error responses formatted correctly"""
    
    # Invalid resource name
    response = await api_client.put(
        "http://localhost:9050/subscriptions/sub-123/resourceGroups/rg-prod/providers/ITL.MyProvider/myresources/invalid@name",
        json={"location": "westus2"}
    )
    
    assert response.status_code == 400
    error = response.json()
    assert "error" in error
    assert "Invalid" in error["error"]["message"]
```

---

## Running Tests

### Run All Tests

```bash
# Run all tests with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_handler_scoping.py

# Run specific test
pytest tests/test_handler_scoping.py::test_creates_resource_with_correct_scope

# Run with verbose output
pytest tests/ -v

# Run and show print statements
pytest tests/ -s
```

### Pytest Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "e2e: End-to-end tests",
    "slow: Slow tests",
]
```

### Run by Category

```bash
# Run only unit tests
pytest tests/ -m unit

# Run unit + integration (skip E2E)
pytest tests/ -m "unit or integration"

# Run everything except slow
pytest tests/ -m "not slow"
```

---

## Test Coverage Goals

| Category | Target |
|----------|--------|
| Unit tests | >90% |
| Integration tests | >80% |
| Critical paths | 100% |
| Error handling | 100% |

---

## Fixtures for Testing

```python
# tests/conftest.py

@pytest.fixture
def test_storage():
    """Fresh storage dict for each test"""
    return {}

@pytest.fixture
def test_provider(test_storage):
    """Provider with test storage"""
    provider = MyProvider(storage=test_storage)
    return provider

@pytest.fixture
async def test_request():
    """Standard test resource request"""
    return ResourceRequest(
        resource_type="myresources",
        resource_name="test-001",
        subscription_id="sub-123",
        resource_group="rg-test",
        location="westus2",
        properties={},
        tags={}
    )
```

---

## Best Practices

✅ **Test at all levels** - Unit, integration, and E2E  
✅ **Use fixtures** - Reusable test setup  
✅ **Test error paths** - Not just happy path  
✅ **Test validation** - Invalid inputs must fail gracefully  
✅ **Mock external** - Don't hit real APIs in tests  
✅ **Async tests** - Use @pytest.mark.asyncio  
✅ **Measure coverage** - Track test coverage over time  

---

## Related Documentation

- [06-HANDLER_MIXINS.md](../06-HANDLER_MIXINS.md) - What handlers do
- [10-ADVANCED_PATTERNS.md](../10-GUIDES/10-ADVANCED_PATTERNS.md) - Complex patterns
- [SDK API Reference](../03-API_REFERENCE.md) - All available methods

---

See [15-EXAMPLES](../15-EXAMPLES/) for complete working test suites.
