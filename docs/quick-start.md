# Quick Start: ITL ControlPlane SDK in 5 Minutes

Get up and running with the ITL ControlPlane SDK in just 5 minutes.

## 1. Installation (30 seconds)

```bash
# Core SDK only
pip install itl-controlplane-sdk

# With FastAPI support
pip install itl-controlplane-sdk[fastapi]

# With identity provider framework
pip install itl-controlplane-sdk[identity]

# Everything
pip install itl-controlplane-sdk[all]
```

## 2. Create Your First Provider (2 minutes)

```python
# my_provider.py
from itl_controlplane_sdk import (
    ResourceProvider,
    ResourceRequest,
    ResourceResponse,
    ProvisioningState,
    generate_resource_id
)

class MyProvider(ResourceProvider):
    def __init__(self):
        super().__init__("ITL.MyProvider")
        self.resources = {}
    
    async def create_or_update_resource(self, request: ResourceRequest) -> ResourceResponse:
        # Generate resource ID
        resource_id = generate_resource_id(
            subscription_id=request.subscription_id,
            resource_group=request.resource_group,
            provider_namespace=self.provider_namespace,
            resource_type=request.resource_type,
            resource_name=request.resource_name
        )
        
        # Store the resource
        self.resources[resource_id] = {
            "id": resource_id,
            "name": request.resource_name,
            "properties": request.properties
        }
        
        # Return response
        return ResourceResponse(
            id=resource_id,
            name=request.resource_name,
            type=f"{self.provider_namespace}/{request.resource_type}",
            provisioning_state=ProvisioningState.SUCCEEDED,
            properties=request.properties
        )
    
    async def get_resource(self, request: ResourceRequest) -> ResourceResponse:
        resource_id = generate_resource_id(
            subscription_id=request.subscription_id,
            resource_group=request.resource_group,
            provider_namespace=self.provider_namespace,
            resource_type=request.resource_type,
            resource_name=request.resource_name
        )
        
        if resource_id not in self.resources:
            raise Exception(f"Resource not found: {request.resource_name}")
        
        resource = self.resources[resource_id]
        return ResourceResponse(
            id=resource["id"],
            name=resource["name"],
            properties=resource["properties"]
        )
    
    async def delete_resource(self, request: ResourceRequest) -> ResourceResponse:
        resource_id = generate_resource_id(
            subscription_id=request.subscription_id,
            resource_group=request.resource_group,
            provider_namespace=self.provider_namespace,
            resource_type=request.resource_type,
            resource_name=request.resource_name
        )
        
        self.resources.pop(resource_id, None)
        
        return ResourceResponse(
            id=resource_id,
            name=request.resource_name,
            provisioning_state=ProvisioningState.DELETING
        )
```

## 3. Use Your Provider (2 minutes)

```python
# main.py
import asyncio
from itl_controlplane_sdk import ResourceRequest, ProvisioningState
from my_provider import MyProvider

async def main():
    # Create provider
    provider = MyProvider()
    
    # Create a resource
    create_request = ResourceRequest(
        subscription_id="sub-123",
        resource_group="rg-test",
        provider_namespace="ITL.MyProvider",
        resource_type="myresources",
        resource_name="my-first-resource",
        location="eastus",
        properties={"key": "value"}
    )
    
    create_response = await provider.create_or_update_resource(create_request)
    print(f"✓ Created: {create_response.id}")
    print(f"  Status: {create_response.provisioning_state}")
    
    # Get the resource
    get_response = await provider.get_resource(create_request)
    print(f"\n✓ Retrieved: {get_response.name}")
    print(f"  Properties: {get_response.properties}")
    
    # Delete the resource
    delete_response = await provider.delete_resource(create_request)
    print(f"\n✓ Deleted: {delete_response.name}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 4. Run It

```bash
python main.py
```

**Expected output:**
```
✓ Created: /subscriptions/sub-123/resourceGroups/rg-test/providers/ITL.MyProvider/myresources/my-first-resource
  Status: Succeeded

✓ Retrieved: my-first-resource
  Properties: {'key': 'value'}

✓ Deleted: my-first-resource
```

---

## Next Steps

- **Advanced Features**: See [10-ADVANCED_PATTERNS.md](guides/advanced-patterns.md)
- **Scope-Aware Resources**: See [03-CORE_CONCEPTS.md](architecture/core-concepts.md)
- **Handler Patterns**: See [06-HANDLER_MIXINS.md](features/handler-mixins.md)
- **FastAPI Integration**: See [08-API_ENDPOINTS.md](features/api-endpoints.md)
- **Complete Examples**: See [15-EXAMPLES](../examples/)

---

**That's it!** You've created your first ITL ControlPlane SDK provider. Now explore the guides to learn more advanced patterns and features.
