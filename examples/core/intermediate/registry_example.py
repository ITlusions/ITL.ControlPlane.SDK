"""
ResourceProviderRegistry Example - Multi-Provider Management

Demonstrates:
1. Creating a ResourceProviderRegistry
2. Registering multiple resource providers
3. CRUD operations through the registry
4. Provider discovery and lookup
5. Request validation before operations

The registry is the central hub for managing all resource providers
in your control plane application.
"""

import asyncio
from typing import Dict, List, Any, Optional

from itl_controlplane_sdk.providers.registry import ResourceProviderRegistry
from itl_controlplane_sdk.providers.base import ResourceProvider
from itl_controlplane_sdk.core import (
    ResourceRequest,
    ResourceResponse,
    ResourceListResponse,
    ProvisioningState,
)


# ============================================================================
# STEP 1: Define custom resource providers
# ============================================================================

class ComputeProvider(ResourceProvider):
    """Example compute provider for Virtual Machines."""

    def __init__(self):
        super().__init__("ITL.Compute")
        self._resources: Dict[str, ResourceResponse] = {}

    async def create_or_update_resource(self, request: ResourceRequest) -> ResourceResponse:
        """Create or update a VM resource."""
        resource_id = self.generate_resource_id(
            request.subscription_id,
            request.resource_group,
            request.resource_type,
            request.resource_name,
        )
        response = ResourceResponse(
            id=resource_id,
            name=request.resource_name,
            type=f"{self.provider_namespace}/{request.resource_type}",
            location=request.location,
            properties={
                **request.body,
                "vmSize": request.body.get("vmSize", "Standard_D2s_v3"),
                "osType": request.body.get("osType", "Linux"),
            },
            provisioning_state=ProvisioningState.SUCCEEDED,
        )
        self._resources[resource_id] = response
        return response

    async def get_resource(self, request: ResourceRequest) -> ResourceResponse:
        """Get a specific VM."""
        resource_id = self.generate_resource_id(
            request.subscription_id,
            request.resource_group,
            request.resource_type,
            request.resource_name,
        )
        if resource_id not in self._resources:
            raise KeyError(f"VM not found: {request.resource_name}")
        return self._resources[resource_id]

    async def delete_resource(self, request: ResourceRequest) -> ResourceResponse:
        """Delete a VM."""
        resource_id = self.generate_resource_id(
            request.subscription_id,
            request.resource_group,
            request.resource_type,
            request.resource_name,
        )
        if resource_id in self._resources:
            deleted = self._resources.pop(resource_id)
            deleted.provisioning_state = ProvisioningState.SUCCEEDED
            return deleted
        raise KeyError(f"VM not found: {request.resource_name}")

    async def list_resources(self, request: ResourceRequest) -> ResourceListResponse:
        """List all VMs in a resource group."""
        prefix = f"/subscriptions/{request.subscription_id}/resourceGroups/{request.resource_group}"
        matching = [r for rid, r in self._resources.items() if rid.startswith(prefix)]
        return ResourceListResponse(value=matching)

    def validate_request(self, request: ResourceRequest) -> List[str]:
        errors = super().validate_request(request)
        if request.body and request.body.get("vmSize"):
            valid_sizes = {"Standard_B1s", "Standard_D2s_v3", "Standard_D4s_v3", "Standard_E2s_v3"}
            if request.body["vmSize"] not in valid_sizes:
                errors.append(f"Invalid vmSize. Must be one of: {valid_sizes}")
        return errors


class StorageProvider(ResourceProvider):
    """Example storage provider for Storage Accounts."""

    def __init__(self):
        super().__init__("ITL.Storage")
        self._resources: Dict[str, ResourceResponse] = {}

    async def create_or_update_resource(self, request: ResourceRequest) -> ResourceResponse:
        """Create or update a storage account."""
        resource_id = self.generate_resource_id(
            request.subscription_id,
            request.resource_group,
            request.resource_type,
            request.resource_name,
        )
        response = ResourceResponse(
            id=resource_id,
            name=request.resource_name,
            type=f"{self.provider_namespace}/{request.resource_type}",
            location=request.location,
            properties={
                **request.body,
                "accountType": request.body.get("accountType", "Standard_LRS"),
                "primaryEndpoint": f"https://{request.resource_name}.blob.core.itlcloud.net",
            },
            provisioning_state=ProvisioningState.SUCCEEDED,
        )
        self._resources[resource_id] = response
        return response

    async def get_resource(self, request: ResourceRequest) -> ResourceResponse:
        """Get a storage account."""
        resource_id = self.generate_resource_id(
            request.subscription_id,
            request.resource_group,
            request.resource_type,
            request.resource_name,
        )
        if resource_id not in self._resources:
            raise KeyError(f"Storage account not found: {request.resource_name}")
        return self._resources[resource_id]

    async def delete_resource(self, request: ResourceRequest) -> ResourceResponse:
        """Delete a storage account."""
        resource_id = self.generate_resource_id(
            request.subscription_id,
            request.resource_group,
            request.resource_type,
            request.resource_name,
        )
        if resource_id in self._resources:
            return self._resources.pop(resource_id)
        raise KeyError(f"Storage account not found: {request.resource_name}")

    async def list_resources(self, request: ResourceRequest) -> ResourceListResponse:
        """List all storage accounts in a resource group."""
        prefix = f"/subscriptions/{request.subscription_id}/resourceGroups/{request.resource_group}"
        matching = [r for rid, r in self._resources.items() if rid.startswith(prefix)]
        return ResourceListResponse(value=matching)


# ============================================================================
# STEP 2: Registry setup and usage
# ============================================================================

async def main():
    """Demonstrate full registry workflow."""
    print("=" * 60)
    print("ResourceProviderRegistry Example")
    print("=" * 60)

    # --- Create registry and register providers ---
    registry = ResourceProviderRegistry()

    compute = ComputeProvider()
    storage = StorageProvider()

    registry.register_provider("ITL.Compute", "virtualMachines", compute)
    registry.register_provider("ITL.Storage", "storageAccounts", storage)

    # --- Discover registered providers ---
    print("\nRegistered Providers:")
    for provider_path in registry.list_providers():
        print(f"  • {provider_path}")

    print(f"\nProvider Namespaces:")
    for ns in registry.list_provider_namespaces():
        print(f"  • {ns}")

    # --- Lookup a specific provider ---
    found = registry.get_provider("ITL.Compute", "virtualMachines")
    print(f"\nLookup ITL.Compute/virtualMachines: {found.get_provider_info()}")

    missing = registry.get_provider("ITL.Network", "virtualNetworks")
    print(f"Lookup ITL.Network/virtualNetworks: {missing}")

    # --- Create resources through registry ---
    print("\n" + "-" * 60)
    print("Creating resources through registry...")
    print("-" * 60)

    # Create a VM
    vm_request = ResourceRequest(
        subscription_id="sub-001",
        resource_group="prod-rg",
        provider_namespace="ITL.Compute",
        resource_type="virtualMachines",
        resource_name="web-server-01",
        location="westeurope",
        body={"vmSize": "Standard_D2s_v3", "osType": "Linux"},
    )
    vm = await registry.create_or_update_resource("ITL.Compute", "virtualMachines", vm_request)
    print(f"\nCreated VM: {vm.name}")
    print(f"   ID:       {vm.id}")
    print(f"   Location: {vm.location}")
    print(f"   Size:     {vm.properties.get('vmSize')}")

    # Create a storage account
    sa_request = ResourceRequest(
        subscription_id="sub-001",
        resource_group="prod-rg",
        provider_namespace="ITL.Storage",
        resource_type="storageAccounts",
        resource_name="proddata2026",
        location="westeurope",
        body={"accountType": "Standard_GRS"},
    )
    sa = await registry.create_or_update_resource("ITL.Storage", "storageAccounts", sa_request)
    print(f"\nCreated Storage: {sa.name}")
    print(f"   ID:       {sa.id}")
    print(f"   Endpoint: {sa.properties.get('primaryEndpoint')}")

    # --- Get resources through registry ---
    print("\n" + "-" * 60)
    print("Getting resources through registry...")
    print("-" * 60)

    vm_get = await registry.get_resource("ITL.Compute", "virtualMachines", vm_request)
    print(f"\nGet VM: {vm_get.name} → {vm_get.provisioning_state.value}")

    # --- List resources through registry ---
    print("\n" + "-" * 60)
    print("Listing resources through registry...")
    print("-" * 60)

    list_request = ResourceRequest(
        subscription_id="sub-001",
        resource_group="prod-rg",
        provider_namespace="ITL.Storage",
        resource_type="storageAccounts",
        resource_name="any",
        location="westeurope",
        body={},
    )
    sa_list = await registry.list_resources("ITL.Storage", "storageAccounts", list_request)
    print(f"\nStorage Accounts in prod-rg: {len(sa_list.value)}")
    for item in sa_list.value:
        print(f"   • {item.name} ({item.location})")

    # --- Delete through registry ---
    print("\n" + "-" * 60)
    print("Deleting resources through registry...")
    print("-" * 60)

    deleted = await registry.delete_resource("ITL.Compute", "virtualMachines", vm_request)
    print(f"\n Deleted VM: {deleted.name}")

    # Verify it's gone
    try:
        await registry.get_resource("ITL.Compute", "virtualMachines", vm_request)
    except KeyError:
        print("   Confirmed: VM no longer exists")

    # --- Error handling: unknown provider ---
    print("\n" + "-" * 60)
    print("Error handling...")
    print("-" * 60)

    try:
        await registry.get_resource("ITL.Unknown", "widgets", vm_request)
    except ValueError as e:
        print(f"\n Expected error: {e}")

    # --- Validation through registry ---
    bad_request = ResourceRequest(
        subscription_id="sub-001",
        resource_group="prod-rg",
        provider_namespace="ITL.Compute",
        resource_type="virtualMachines",
        resource_name="bad-vm",
        location="westeurope",
        body={"vmSize": "InvalidSize_XYZ"},
    )
    try:
        await registry.create_or_update_resource("ITL.Compute", "virtualMachines", bad_request)
    except ValueError as e:
        print(f" Validation error: {e}")

    print("\nAll Registry examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
