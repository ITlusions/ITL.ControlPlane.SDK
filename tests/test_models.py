"""
Test models and validation
"""
import pytest
from pydantic import ValidationError

from itl_controlplane_sdk import (
    ResourceRequest,
    ResourceResponse,
    ResourceListResponse,
    ProvisioningState,
    ResourceMetadata,
    ErrorResponse,
    ResourceGroup,
    ManagementGroup,
    Deployment,
    Subscription,
    Location,
    ExtendedLocation,
    Tag,
    Policy,
    ProviderConfiguration,
)


def test_resource_request_validation():
    """Test ResourceRequest model validation"""
    # Valid request
    request = ResourceRequest(
        subscription_id="sub-123",
        resource_group="rg-test",
        provider_namespace="ITL.Test",
        resource_type="testresources",
        resource_name="test-resource",
        location="eastus",
        body={"properties": {"test": "value"}}
    )
    assert request.resource_name == "test-resource"
    assert request.api_version == "2023-01-01"

    # Invalid resource name (too long)
    with pytest.raises(ValidationError):
        ResourceRequest(
            subscription_id="sub-123",
            resource_group="rg-test", 
            provider_namespace="ITL.Test",
            resource_type="testresources",
            resource_name="a" * 300,  # Too long
            location="eastus",
            body={}
        )

    # Invalid API version format
    with pytest.raises(ValidationError):
        ResourceRequest(
            subscription_id="sub-123",
            resource_group="rg-test",
            provider_namespace="ITL.Test", 
            resource_type="testresources",
            resource_name="test-resource",
            location="eastus",
            body={},
            api_version="invalid-format"
        )


def test_resource_response_model():
    """Test ResourceResponse model"""
    response = ResourceResponse(
        id="/subscriptions/sub-123/resourceGroups/rg-test/providers/ITL.Test/testresources/test-resource",
        name="test-resource",
        type="ITL.Test/testresources",
        location="eastus",
        properties={"test": "value"},
        tags={"env": "test"},
        provisioning_state=ProvisioningState.SUCCEEDED
    )
    
    assert response.name == "test-resource"
    assert response.provisioning_state == ProvisioningState.SUCCEEDED
    assert response.tags["env"] == "test"


def test_resource_list_response():
    """Test ResourceListResponse model"""
    resources = [
        ResourceResponse(
            id="/test/1",
            name="resource1", 
            type="Test/resources",
            location="eastus",
            properties={}
        ),
        ResourceResponse(
            id="/test/2",
            name="resource2",
            type="Test/resources", 
            location="westus",
            properties={}
        )
    ]
    
    list_response = ResourceListResponse(
        value=resources,
        next_link="https://api.example.com/next"
    )
    
    assert len(list_response.value) == 2
    assert list_response.next_link == "https://api.example.com/next"


def test_provisioning_states():
    """Test ProvisioningState enum"""
    assert ProvisioningState.SUCCEEDED.value == "Succeeded"
    assert ProvisioningState.FAILED.value == "Failed"
    assert ProvisioningState.CREATING.value == "Creating"


def test_error_response():
    """Test ErrorResponse model"""
    error = ErrorResponse(
        error={
            "code": "ResourceNotFound",
            "message": "The resource was not found",
            "details": []
        }
    )
    
    assert error.error["code"] == "ResourceNotFound"
    assert "not found" in error.error["message"]