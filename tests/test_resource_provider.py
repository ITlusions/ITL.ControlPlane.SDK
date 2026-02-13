"""
Test resource provider functionality
"""
import pytest
from unittest.mock import AsyncMock

from itl_controlplane_sdk import (
    ResourceProvider,
    ResourceRequest,
    ResourceResponse, 
    ProvisioningState,
    ResourceNotFoundError
)


class TestResourceProvider(ResourceProvider):
    """Test implementation of ResourceProvider"""
    
    def __init__(self):
        super().__init__("TestProvider")
        self.supported_resource_types = ["testresources"]
        self._resources = {}
    
    async def create_or_update_resource(self, request: ResourceRequest) -> ResourceResponse:
        resource_id = f"/subscriptions/{request.subscription_id}/resourceGroups/{request.resource_group}/providers/{request.provider_namespace}/{request.resource_type}/{request.resource_name}"
        
        response = ResourceResponse(
            id=resource_id,
            name=request.resource_name,
            type=f"{request.provider_namespace}/{request.resource_type}",
            location=request.location,
            properties=request.body.get("properties", {}),
            provisioning_state=ProvisioningState.SUCCEEDED
        )
        
        self._resources[resource_id] = response
        return response
    
    async def get_resource(self, request: ResourceRequest) -> ResourceResponse:
        resource_id = f"/subscriptions/{request.subscription_id}/resourceGroups/{request.resource_group}/providers/{request.provider_namespace}/{request.resource_type}/{request.resource_name}"
        
        if resource_id not in self._resources:
            raise ResourceNotFoundError(resource_id)
            
        return self._resources[resource_id]
    
    async def delete_resource(self, request: ResourceRequest) -> ResourceResponse:
        resource_id = f"/subscriptions/{request.subscription_id}/resourceGroups/{request.resource_group}/providers/{request.provider_namespace}/{request.resource_type}/{request.resource_name}"
        
        if resource_id not in self._resources:
            raise ResourceNotFoundError(resource_id)
            
        resource = self._resources[resource_id]
        del self._resources[resource_id]
        
        # Return resource with DELETING state
        resource.provisioning_state = ProvisioningState.DELETING
        return resource
    
    async def list_resources(self, request: ResourceRequest) -> list:
        return list(self._resources.values())


@pytest.mark.asyncio
async def test_resource_provider_creation():
    """Test resource provider instantiation"""
    provider = TestResourceProvider()
    assert provider.provider_namespace == "TestProvider"
    assert "testresources" in provider.supported_resource_types


@pytest.mark.asyncio 
async def test_create_resource():
    """Test resource creation"""
    provider = TestResourceProvider()
    
    request = ResourceRequest(
        subscription_id="sub-123",
        resource_group="rg-test",
        provider_namespace="TestProvider",
        resource_type="testresources", 
        resource_name="test-resource",
        location="eastus",
        body={"properties": {"test": "value"}}
    )
    
    response = await provider.create_or_update_resource(request)
    
    assert response.name == "test-resource"
    assert response.location == "eastus"
    assert response.provisioning_state == ProvisioningState.SUCCEEDED
    assert response.properties["test"] == "value"


@pytest.mark.asyncio
async def test_get_resource():
    """Test resource retrieval"""
    provider = TestResourceProvider()
    
    # Create a resource first
    request = ResourceRequest(
        subscription_id="sub-123",
        resource_group="rg-test", 
        provider_namespace="TestProvider",
        resource_type="testresources",
        resource_name="test-resource", 
        location="eastus",
        body={"properties": {"test": "value"}}
    )
    
    await provider.create_or_update_resource(request)
    
    # Now get it
    response = await provider.get_resource(request)
    
    assert response.name == "test-resource"
    assert response.properties["test"] == "value"


@pytest.mark.asyncio
async def test_delete_resource():
    """Test resource deletion"""
    provider = TestResourceProvider()
    
    # Create a resource first  
    request = ResourceRequest(
        subscription_id="sub-123",
        resource_group="rg-test",
        provider_namespace="TestProvider", 
        resource_type="testresources",
        resource_name="test-resource",
        location="eastus",
        body={"properties": {"test": "value"}}
    )
    
    await provider.create_or_update_resource(request)
    
    # Now delete it
    response = await provider.delete_resource(request)
    
    assert response.name == "test-resource" 
    assert response.provisioning_state == ProvisioningState.DELETING
    
    # Verify it's gone
    from itl_controlplane_sdk import ResourceNotFoundError
    with pytest.raises(ResourceNotFoundError):
        await provider.get_resource(request)


@pytest.mark.asyncio
async def test_resource_not_found():
    """Test resource not found error"""
    provider = TestResourceProvider()
    
    request = ResourceRequest(
        subscription_id="sub-123", 
        resource_group="rg-test",
        provider_namespace="TestProvider",
        resource_type="testresources",
        resource_name="nonexistent-resource",
        location="eastus",
        body={}
    )
    
    from itl_controlplane_sdk.models import ResourceNotFoundError
    with pytest.raises(ResourceNotFoundError):
        await provider.get_resource(request)