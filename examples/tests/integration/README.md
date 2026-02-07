# Tests - Integration Level

Integration testing SDK workflows and end-to-end scenarios.

## Files
- **`test_resource_group_big_3.py`** - Integration tests for resource lifecycle
  - Resource creation workflows
  - Multi-handler interactions
  - Provisioning state transitions
  - Timestamp validation
  - Full resource group deployment

**Run:** `pytest tests/integration/` or `pytest tests/integration/test_resource_group_big_3.py`

## Integration Testing Concepts

Integration tests verify:
- Multiple components working together
- API workflows (create → read → update → delete)
- Handler interactions
- End-to-end scenarios

### Test Structure

```python
import pytest
from itl_control_plane_sdk import ResourceProvider

class TestResourceGroupWorkflow:
    @pytest.fixture
    def provider(self):
        """Create a provider for testing"""
        return ResourceProvider("test-provider")
    
    def test_create_and_read(self, provider):
        """Workflow: Create RG, read it back"""
        # Create
        rg = provider.create_resource(
            "test-rg",
            {"location": "westeurope"}
        )
        assert rg.id is not None
        
        # Read
        rg_read = provider.get_resource(rg.id)
        assert rg_read.properties.name == "test-rg"
```

## Big 3 Integration Test Pattern

### Pattern: Validation + Provisioning + Timestamps

```python
def test_create_vm_validates_input(self, vm_handler):
    """VM creation validates input"""
    with pytest.raises(ValueError):
        vm_handler.create_resource(
            "invalid-@-name",  # Invalid character
            {...}
        )

def test_vm_provisioning_state(self, vm_handler):
    """VM goes through provisioning states"""
    vm = vm_handler.create_resource(
        "web-vm",
        {"size": "Standard_D2s_v3"}
    )
    
    assert vm.provisioning_state == "Provisioning"
    
    # Simulate completion
    vm.provisioning_state = "Succeeded"
    assert vm.provisioning_state == "Succeeded"

def test_vm_timestamps(self, vm_handler):
    """VM has creation/modification timestamps"""
    vm = vm_handler.create_resource(
        "web-vm",
        {"size": "Standard_D2s_v3"}
    )
    
    assert vm.created_at is not None
    assert vm.modified_at is not None
    assert vm.modified_at >= vm.created_at
```

## Multi-Handler Integration

```python
def test_create_complete_app_stack(self):
    """Integration: Create RG, VM, NIC, Storage"""
    
    # Create resource group
    rg = self.rg_handler.create_resource(
        "app-rg",
        {"location": "westeurope"}
    )
    
    # Create storage (global)
    storage = self.storage_handler.create_resource(
        "appstorage2025",
        {"account_type": "Standard_GRS"},
        {...},
        {}  # Global scope
    )
    
    # Create NIC (RG-scoped)
    nic = self.nic_handler.create_resource(
        "app-nic",
        {"vm_id": "...", "subnet_id": "..."},
        {...},
        {"subscription_id": "...", "resource_group": rg.id}
    )
    
    # Create VM (RG-scoped)
    vm = self.vm_handler.create_resource(
        "app-vm",
        {"size": "Standard_D2s_v3"},
        {...},
        {"subscription_id": "...", "resource_group": rg.id}
    )
    
    # Verify all created
    assert rg.id is not None
    assert storage.id is not None
    assert nic.id is not None
    assert vm.id is not None
```

## Error Scenario Testing

```python
def test_global_uniqueness_conflict(self):
    """Verify global uniqueness is enforced"""
    # First storage account succeeds
    storage1 = self.storage_handler.create_resource(
        "data2025",
        {"account_type": "Standard_GRS"},
        {...},
        {}
    )
    assert storage1.id is not None
    
    # Second with same name fails
    with pytest.raises(ValueError, match="already exists globally"):
        storage2 = self.storage_handler.create_resource(
            "data2025",  # Duplicate!
            {"account_type": "Standard_GRS"},
            {...},
            {}
        )

def test_rg_scoped_uniqueness(self):
    """Verify RG-scoped uniqueness is enforced"""
    # Same VM name OK in different RGs
    vm1 = self.vm_handler.create_resource(
        "web-vm",
        {"size": "Standard_D2s_v3"},
        {...},
        {"subscription_id": "sub", "resource_group": "rg-1"}
    )
    
    vm2 = self.vm_handler.create_resource(
        "web-vm",  # Same name, different RG
        {"size": "Standard_D2s_v3"},
        {...},
        {"subscription_id": "sub", "resource_group": "rg-2"}
    )
    
    assert vm1.id != vm2.id
    
    # Same VM name fails in same RG
    with pytest.raises(ValueError, match="already exists in"):
        vm3 = self.vm_handler.create_resource(
            "web-vm",  # Duplicate in rg-1
            {"size": "Standard_D2s_v3"},
            {...},
            {"subscription_id": "sub", "resource_group": "rg-1"}
        )
```

## Workflow Testing

```python
@pytest.mark.asyncio
async def test_deployment_workflow(self):
    """Complete deployment workflow"""
    
    # Step 1: Create infrastructure
    rg = await self.rg_handler.create_async(
        "deploy-rg",
        {"location": "westeurope"}
    )
    
    # Step 2: Create security policies
    policy = await self.policy_handler.create_async(
        "encrypt-disks",
        {"effect": "Deny"}
    )
    
    # Step 3: Create compute
    vm = await self.vm_handler.create_async(
        "app-vm",
        {"size": "Standard_D2s_v3"},
        {...},
        {"subscription_id": "...", "resource_group": rg.id}
    )
    
    # Step 4: Verify all states
    assert rg.provisioning_state == "Succeeded"
    assert policy.provisioning_state == "Succeeded"
    assert vm.provisioning_state in ["Provisioning", "Succeeded"]
    
    # Step 5: Export IDs for next stage
    return {
        "rg_id": rg.id,
        "vm_id": vm.id,
        "policy_id": policy.id
    }
```

## Prerequisites
- Install pytest: `pip install pytest pytest-asyncio`
- Understand SDK basics (see [core/beginner/](../../core/beginner/))
- Understand all resource types (compute, storage, network, management)

## Running Tests

```bash
# Run all integration tests
pytest tests/integration/

# Run specific test
pytest tests/integration/test_resource_group_big_3.py::TestResourceGroupWorkflow::test_create_and_read

# Run with verbose output
pytest tests/integration/ -v

# Run with coverage
pytest tests/integration/ --cov=itl_control_plane_sdk

# Run in parallel (faster)
pytest tests/integration/ -n auto
```

## Test Coverage

Recommended coverage:
- Unit tests: 80%+ of SDK code
- Integration tests: 60%+ of workflows
- E2E tests: Critical paths only

## Next Steps
→ **[Deployment](../../deployment/intermediate/)** - Deploy your code
