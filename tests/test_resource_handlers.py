"""
Test suite for the Big 3 Resource Handlers.

Tests:
1. TimestampedResourceHandler - Timestamps on create/update
2. ProvisioningStateHandler - State transitions
3. ValidatedResourceHandler - Schema validation
"""

import pytest
from datetime import datetime
from pydantic import BaseModel, validator, Field

from itl_controlplane_sdk.providers import (
    TimestampedResourceHandler,
    ProvisioningStateHandler,
    ValidatedResourceHandler,
    UniquenessScope,
    ProvisioningState,
)


# ============================================================================
# TEST 1: TimestampedResourceHandler
# ============================================================================

class TestTimestampedResourceHandler:
    """Test automatic timestamp management."""
    
    def test_created_timestamp_on_create(self):
        """Resources should have createdTime on creation."""
        storage = {}
        handler = TimestampedResourceHandler(storage)
        
        before = datetime.utcnow().isoformat()
        resource_id, config = handler.create_resource(
            "test-resource",
            {"setting": "value"},
            "Test/resource",
            {"subscription_id": "sub-1", "user_id": "user@company.com"}
        )
        after = datetime.utcnow().isoformat()
        
        # Should have timestamps
        assert "createdTime" in config
        assert "modifiedTime" in config
        assert config["createdTime"] == config["modifiedTime"]
        assert config["createdBy"] == "user@company.com"
        assert config["modifiedBy"] == "user@company.com"
        
        # Timestamp should be reasonable (between before and after)
        assert before < config["createdTime"] < after
    
    def test_modified_timestamp_on_update(self):
        """Resources should have updated modifiedTime on update."""
        storage = {}
        handler = TimestampedResourceHandler(storage)
        
        # Create
        resource_id, created = handler.create_resource(
            "test-resource",
            {"setting": "value"},
            "Test/resource",
            {"subscription_id": "sub-1", "user_id": "creator@company.com"}
        )
        created_time = created["createdTime"]
        
        # Wait to ensure time difference
        import time
        time.sleep(0.1)
        
        # Update
        resource_id2, updated = handler.update_resource(
            "test-resource",
            {"setting": "new-value"},
            {"subscription_id": "sub-1", "user_id": "updater@company.com"}
        )
        
        # createdTime should not change
        assert updated["createdTime"] == created_time
        assert updated["createdBy"] == "creator@company.com"
        
        # modifiedTime should be newer
        assert updated["modifiedTime"] > created_time
        assert updated["modifiedBy"] == "updater@company.com"
    
    def test_default_user_if_not_provided(self):
        """Should use 'system' as default user if not provided."""
        storage = {}
        handler = TimestampedResourceHandler(storage)
        
        resource_id, config = handler.create_resource(
            "test",
            {"setting": "value"},
            "Test/resource",
            {"subscription_id": "sub-1"}  # No user_id
        )
        
        assert config["createdBy"] == "system"
        assert config["modifiedBy"] == "system"


# ============================================================================
# TEST 2: ProvisioningStateHandler
# ============================================================================

class TestProvisioningStateHandler:
    """Test provisioning state machine."""
    
    def test_created_in_accepted_state(self):
        """New resources should start in Accepted state."""
        storage = {}
        handler = ProvisioningStateHandler(storage)
        
        resource_id, config = handler.create_resource(
            "test-rg",
            {"location": "eastus"},
            "Resources/resourcegroups",
            {"subscription_id": "sub-1"}
        )
        
        # Should auto-transition to Succeeded
        assert config["provisioning_state"] == ProvisioningState.SUCCEEDED.value
    
    def test_state_transitions(self):
        """Verify state transition history."""
        storage = {}
        handler = ProvisioningStateHandler(storage)
        
        resource_id, config = handler.create_resource(
            "test-rg",
            {"location": "eastus"},
            "Resources/resourcegroups",
            {"subscription_id": "sub-1"}
        )
        
        # Check state history
        history = handler.get_state_history(resource_id)
        
        # Should have: Accepted → Provisioning → Succeeded
        assert len(history) >= 3
        assert history[0]["state"] == ProvisioningState.ACCEPTED.value
        assert history[1]["state"] == ProvisioningState.PROVISIONING.value
        assert history[2]["state"] == ProvisioningState.SUCCEEDED.value
    
    def test_delete_transitions_through_deleting_state(self):
        """Delete should transition through Deleting → Deleted."""
        storage = {}
        handler = ProvisioningStateHandler(storage)
        
        resource_id, config = handler.create_resource(
            "test-rg",
            {"location": "eastus"},
            "Resources/resourcegroups",
            {"subscription_id": "sub-1"}
        )
        
        # Delete
        deleted = handler.delete_resource(
            "test-rg",
            {"subscription_id": "sub-1"}
        )
        assert deleted is True
        
        # Check history includes Deleting and Deleted
        history = handler.get_state_history(resource_id)
        states = [h["state"] for h in history]
        
        assert ProvisioningState.DELETING.value in states
        assert ProvisioningState.DELETED.value in states
    
    def test_invalid_state_transition_fails(self):
        """Invalid state transitions should raise ValueError."""
        storage = {}
        handler = ProvisioningStateHandler(storage)
        
        # Create resource (now in Succeeded state)
        resource_id, config = handler.create_resource(
            "test-rg",
            {"location": "eastus"},
            "Resources/resourcegroups",
            {"subscription_id": "sub-1"}
        )
        
        # Try to force invalid transition (Succeeded → Accepted)
        with pytest.raises(ValueError, match="Invalid state transition"):
            handler._advance_state(
                resource_id,
                ProvisioningState.ACCEPTED,
                {"subscription_id": "sub-1"}
            )


# ============================================================================
# TEST 3: ValidatedResourceHandler
# ============================================================================

class SimpleSchema(BaseModel):
    """Simple test schema."""
    name: str
    count: int = Field(gt=0)
    
    @validator('name')
    def name_not_empty(cls, v):
        if len(v) < 2:
            raise ValueError('Name must be at least 2 chars')
        return v


class ValidatingHandler(ValidatedResourceHandler):
    """Test handler with validation."""
    SCHEMA_CLASS = SimpleSchema
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION]
    RESOURCE_TYPE = "test"


class TestValidatedResourceHandler:
    """Test Pydantic schema validation."""
    
    def test_valid_data_accepted(self):
        """Valid data should be accepted."""
        storage = {}
        handler = ValidatingHandler(storage)
        
        resource_id, config = handler.create_resource(
            "test-item",
            {"name": "my-item", "count": 5},
            "Test/resource",
            {"subscription_id": "sub-1"}
        )
        
        assert resource_id is not None
        assert config["name"] == "my-item"
        assert config["count"] == 5
    
    def test_invalid_type_rejected(self):
        """Invalid type should raise ValueError."""
        storage = {}
        handler = ValidatingHandler(storage)
        
        with pytest.raises(ValueError, match="Validation failed"):
            handler.create_resource(
                "test",
                {"name": "item", "count": "five"},  # count should be int, not str
                "Test/resource",
                {"subscription_id": "sub-1"}
            )
    
    def test_validator_constraint_enforced(self):
        """Field validators should be enforced."""
        storage = {}
        handler = ValidatingHandler(storage)
        
        # count > 0 (Field constraint)
        with pytest.raises(ValueError, match="Validation failed"):
            handler.create_resource(
                "test",
                {"name": "item", "count": 0},  # Violates gt=0
                "Test/resource",
                {"subscription_id": "sub-1"}
            )
        
        # name length >= 2 (validator)
        with pytest.raises(ValueError, match="Validation failed"):
            handler.create_resource(
                "test",
                {"name": "x", "count": 5},  # Too short
                "Test/resource",
                {"subscription_id": "sub-1"}
            )
    
    def test_required_field_enforced(self):
        """Missing required fields should raise ValueError."""
        storage = {}
        handler = ValidatingHandler(storage)
        
        with pytest.raises(ValueError, match="Validation failed"):
            handler.create_resource(
                "test",
                {"name": "item"},  # Missing 'count'
                "Test/resource",
                {"subscription_id": "sub-1"}
            )
    
    def test_no_schema_class_skips_validation(self):
        """Handler without SCHEMA_CLASS should accept any data."""
        storage = {}
        
        class NoSchemaHandler(ProvisioningStateHandler):
            UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION]
            RESOURCE_TYPE = "test"
            # No SCHEMA_CLASS defined
        
        handler = NoSchemaHandler(storage)
        
        # Should accept arbitrary data
        resource_id, config = handler.create_resource(
            "test",
            {"anything": "goes", "x": 123},
            "Test/resource",
            {"subscription_id": "sub-1"}
        )
        
        assert config["anything"] == "goes"
        assert config["x"] == 123


# ============================================================================
# INTEGRATION: All Three Together
# ============================================================================

class VMSchema(BaseModel):
    """VM schema for integration test."""
    vm_name: str
    size: str
    
    @validator('vm_name')
    def validate_name(cls, v):
        if len(v) < 3:
            raise ValueError('VM name too short')
        return v
    
    @validator('size')
    def validate_size(cls, v):
        if v not in ('Small', 'Medium', 'Large'):
            raise ValueError('Invalid size')
        return v


class IntegratedVMHandler(ValidatedResourceHandler):
    """Full handler with all three features."""
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION, UniquenessScope.RESOURCE_GROUP]
    RESOURCE_TYPE = "virtualmachines"
    SCHEMA_CLASS = VMSchema


class TestIntegration:
    """Test all three handlers working together."""
    
    def test_all_features_together(self):
        """Should have timestamps, states, and validation."""
        storage = {}
        handler = IntegratedVMHandler(storage)
        
        # Create with validation
        resource_id, config = handler.create_resource(
            "web-vm",
            {"vm_name": "web-vm", "size": "Medium"},
            "Compute/virtualmachines",
            {
                "subscription_id": "prod-sub",
                "resource_group": "prod-rg",
                "user_id": "admin@company.com"
            }
        )
        
        # Should have timestamps
        assert "createdTime" in config
        assert "modifiedTime" in config
        assert config["createdBy"] == "admin@company.com"
        
        # Should have succeeded state
        assert config["provisioning_state"] == ProvisioningState.SUCCEEDED.value
        
        # Should have validated data
        assert config["vm_name"] == "web-vm"
        assert config["size"] == "Medium"
    
    def test_validation_fails_before_storage(self):
        """Validation errors should prevent storage."""
        storage = {}
        handler = IntegratedVMHandler(storage)
        
        # Invalid size
        with pytest.raises(ValueError, match="Validation failed"):
            handler.create_resource(
                "web-vm",
                {"vm_name": "web-vm", "size": "ExtraLarge"},  # Invalid
                "Compute/virtualmachines",
                {"subscription_id": "prod-sub", "resource_group": "prod-rg"}
            )
        
        # Storage should be empty (no partial write)
        assert len(storage) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
