"""
QuickStart Example: ITL ControlPlane SDK

This is a simple example showing how to quickly get started with the SDK.
"""
import asyncio
import logging

# Import SDK components
from itl_controlplane_sdk import ResourceProviderRegistry, ResourceProvider
from itl_controlplane_sdk import ResourceRequest, ProvisioningState

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def quickstart():
    """Quick example of using the SDK"""
    
    # 1. Create a simple test provider
    class TestProvider(ResourceProvider):
        def __init__(self):
            super().__init__("TestProvider")
        
        async def create_or_update_resource(self, request):
            logger.info(f"Creating resource: {request.resource_name}")
            return {"status": "created", "resource_id": f"test-{request.resource_name}"}
        
        async def get_resource(self, request):
            logger.info(f"Getting resource: {request.resource_name}")
            return {"resource_id": request.resource_name, "status": "active"}
        
        async def delete_resource(self, request):
            logger.info(f"Deleting resource: {request.resource_name}")
            return {"status": "deleted"}
        
        async def list_resources(self, request):
            logger.info(f"Listing resources in group: {request.resource_group}")
            return []
    
    # 2. Create registry and register the provider
    registry = ResourceProviderRegistry()
    test_provider = TestProvider()
    registry.register_provider("ITL.Test", "TestResource", test_provider)
    
    # 3. Create a simple resource request
    request = ResourceRequest(
        subscription_id="my-subscription",
        resource_group="my-resource-group",
        resource_name="my-test-resource",
        resource_type="TestResource",
        location="westus2",
        provider_namespace="ITL.Test",
        body={"test_setting": "test_value", "tags": {"environment": "development"}}
    )
    
    # 4. Get the provider and test basic operations
    provider = registry.get_provider("ITL.Test", "TestResource")
    if provider:
        logger.info("Provider found! Testing operations...")
        
        # Test create operation
        create_result = await provider.create_or_update_resource(request)
        logger.info(f"Create result: {create_result}")
        
        # Test get operation  
        get_request = ResourceRequest(
            subscription_id="my-subscription",
            resource_group="my-resource-group", 
            resource_name="my-test-resource",
            resource_type="TestResource",
            location="westus2",
            provider_namespace="ITL.Test",
            body={}
        )
        get_result = await provider.get_resource(get_request)
        logger.info(f"Get result: {get_result}")
        
        # Test list operation
        list_request = ResourceRequest(
            subscription_id="my-subscription",
            resource_group="my-resource-group",
            resource_name="",  # Empty for list operations
            resource_type="TestResource", 
            location="westus2",
            provider_namespace="ITL.Test",
            body={}
        )
        list_result = await provider.list_resources(list_request)
        logger.info(f"List result: {list_result}")
        
        # Test delete operation
        delete_result = await provider.delete_resource(request)
        logger.info(f"Delete result: {delete_result}")
    else:
        logger.error("Provider not found!")
    
    logger.info("QuickStart example completed!")


if __name__ == "__main__":
    # Run the quickstart example
    asyncio.run(quickstart())