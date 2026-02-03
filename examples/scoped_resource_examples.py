"""
Example: Implementing Additional Resource Types with ScopedResourceHandler

This file demonstrates how to implement various Azure-like resource types
using the ScopedResourceHandler base class.
"""

from itl_controlplane_sdk.providers import ScopedResourceHandler, UniquenessScope
from typing import Dict, Any, Tuple


# ==================== EXAMPLE 1: Virtual Machines ====================
# Unique within Resource Group (subscription + resource group scope)

class VirtualMachineHandler(ScopedResourceHandler):
    """
    Handler for Virtual Machines with RG-scoped uniqueness.
    
    Same VM name allowed in different RGs within same subscription,
    but not in the same RG.
    """
    
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION, UniquenessScope.RESOURCE_GROUP]
    RESOURCE_TYPE = "virtualmachines"
    
    def create_from_spec(
        self,
        name: str,
        vm_spec: Dict[str, Any],
        subscription_id: str,
        resource_group: str
    ) -> Tuple[str, Dict[str, Any]]:
        """Create a VM with automatic duplicate detection within RG"""
        vm_config = {
            "size": vm_spec.get("size", "Standard_B2s"),
            "image": vm_spec.get("image"),
            "os_type": vm_spec.get("os_type", "Linux"),
            "enable_accelerated_networking": vm_spec.get("enable_accelerated_networking", False),
            "provisioning_state": "Succeeded"
        }
        
        return self.create_resource(
            name,
            vm_config,
            "ITL.Compute/virtualmachines",
            {
                "subscription_id": subscription_id,
                "resource_group": resource_group
            }
        )
    
    def list_by_rg(
        self,
        subscription_id: str,
        resource_group: str
    ) -> list:
        """List all VMs in a resource group"""
        resources = self.list_resources({
            "subscription_id": subscription_id,
            "resource_group": resource_group
        })
        return [{"name": name, "id": rid, "config": config} 
                for name, rid, config in resources]


# ==================== EXAMPLE 2: Storage Accounts ====================
# Globally unique (no scope)

class StorageAccountHandler(ScopedResourceHandler):
    """
    Handler for Storage Accounts with global uniqueness.
    
    Storage account names must be globally unique across the entire system.
    """
    
    UNIQUENESS_SCOPE = [UniquenessScope.GLOBAL]
    RESOURCE_TYPE = "storageaccounts"
    
    def create_from_config(
        self,
        name: str,
        storage_config: Dict[str, Any],
        subscription_id: str
    ) -> Tuple[str, Dict[str, Any]]:
        """Create a storage account with global uniqueness enforcement"""
        sa_config = {
            "account_type": storage_config.get("account_type", "Standard"),
            "replication": storage_config.get("replication", "LRS"),
            "access_tier": storage_config.get("access_tier", "Hot"),
            "provisioning_state": "Succeeded"
        }
        
        return self.create_resource(
            name,
            sa_config,
            "ITL.Storage/storageaccounts",
            {"subscription_id": subscription_id}  # Scope context not used for global
        )


# ==================== EXAMPLE 3: Policies ====================
# Management Group-scoped uniqueness

class PolicyHandler(ScopedResourceHandler):
    """
    Handler for Policies with Management Group scope.
    
    Same policy name allowed in different management groups,
    but not in the same management group.
    """
    
    UNIQUENESS_SCOPE = [UniquenessScope.MANAGEMENT_GROUP]
    RESOURCE_TYPE = "policies"
    
    def create_from_definition(
        self,
        name: str,
        policy_def: Dict[str, Any],
        management_group_id: str
    ) -> Tuple[str, Dict[str, Any]]:
        """Create a policy within a management group"""
        policy_config = {
            "type": policy_def.get("type", "BuiltIn"),
            "mode": policy_def.get("mode", "Indexed"),
            "rules": policy_def.get("rules", []),
            "parameters": policy_def.get("parameters", {}),
            "provisioning_state": "Succeeded"
        }
        
        return self.create_resource(
            name,
            policy_config,
            "ITL.Governance/policies",
            {"management_group_id": management_group_id}
        )
    
    def list_by_management_group(self, management_group_id: str) -> list:
        """List all policies in a management group"""
        resources = self.list_resources({
            "management_group_id": management_group_id
        })
        return [{"name": name, "id": rid, "definition": config} 
                for name, rid, config in resources]


# ==================== EXAMPLE 4: Network Interfaces ====================
# Resource Group-scoped

class NetworkInterfaceHandler(ScopedResourceHandler):
    """
    Handler for Network Interfaces with RG-scoped uniqueness.
    """
    
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION, UniquenessScope.RESOURCE_GROUP]
    RESOURCE_TYPE = "networkinterfaces"
    
    def create_from_config(
        self,
        name: str,
        nic_config: Dict[str, Any],
        subscription_id: str,
        resource_group: str
    ) -> Tuple[str, Dict[str, Any]]:
        """Create a network interface"""
        nic_data = {
            "ip_configurations": nic_config.get("ip_configurations", []),
            "dns_settings": nic_config.get("dns_settings", {}),
            "network_security_group": nic_config.get("network_security_group"),
            "provisioning_state": "Succeeded"
        }
        
        return self.create_resource(
            name,
            nic_data,
            "ITL.Network/networkinterfaces",
            {
                "subscription_id": subscription_id,
                "resource_group": resource_group
            }
        )


# ==================== EXAMPLE 5: Management Groups ====================
# Subscription-scoped (unique within a subscription context)

class ManagementGroupHandler(ScopedResourceHandler):
    """
    Handler for Management Groups with unique names per subscription/hierarchy.
    """
    
    UNIQUENESS_SCOPE = [UniquenessScope.GLOBAL]  # MGs are globally unique
    RESOURCE_TYPE = "managementgroups"
    
    def create_hierarchy(
        self,
        name: str,
        parent_id: str = None,
        display_name: str = None
    ) -> Tuple[str, Dict[str, Any]]:
        """Create a management group in the hierarchy"""
        mg_config = {
            "display_name": display_name or name,
            "parent_id": parent_id,
            "children": [],
            "provisioning_state": "Succeeded"
        }
        
        return self.create_resource(
            name,
            mg_config,
            "ITL.Management/managementgroups",
            {}  # Global scope - no context needed
        )


# ==================== REAL-WORLD USAGE EXAMPLE ====================

class ComputeProvider:
    """Example provider using multiple handlers"""
    
    def __init__(self):
        # Initialize storage dictionaries
        self.virtual_machines = {}
        self.network_interfaces = {}
        self.storage_accounts = {}
        
        # Initialize handlers
        self.vm_handler = VirtualMachineHandler(self.virtual_machines)
        self.nic_handler = NetworkInterfaceHandler(self.network_interfaces)
        self.sa_handler = StorageAccountHandler(self.storage_accounts)
    
    async def provision_vm_stack(
        self,
        vm_name: str,
        subscription_id: str,
        resource_group: str
    ):
        """
        Provision a complete VM with NIC and storage account.
        Demonstrates error handling for duplicate detection.
        """
        try:
            # Create storage account (globally unique)
            sa_id, sa_data = self.sa_handler.create_from_config(
                f"sa{vm_name.lower()}",
                {"replication": "LRS"},
                subscription_id
            )
            print(f"✓ Storage Account: {sa_id}")
            
        except ValueError as e:
            print(f"✗ Storage Account Error: {e}")
            return None
        
        try:
            # Create network interface (RG-scoped)
            nic_id, nic_data = self.nic_handler.create_from_config(
                f"{vm_name}-nic",
                {"ip_configurations": []},
                subscription_id,
                resource_group
            )
            print(f"✓ Network Interface: {nic_id}")
            
        except ValueError as e:
            print(f"✗ Network Interface Error: {e}")
            return None
        
        try:
            # Create virtual machine (RG-scoped)
            vm_id, vm_data = self.vm_handler.create_from_spec(
                vm_name,
                {
                    "size": "Standard_B2s",
                    "image": "UbuntuServer:20.04-LTS",
                    "os_type": "Linux"
                },
                subscription_id,
                resource_group
            )
            print(f"✓ Virtual Machine: {vm_id}")
            
        except ValueError as e:
            print(f"✗ Virtual Machine Error: {e}")
            return None
        
        return {
            "vm_id": vm_id,
            "nic_id": nic_id,
            "sa_id": sa_id
        }


# ==================== USAGE EXAMPLES ====================

async def main():
    """Demonstrate usage of the handlers"""
    
    provider = ComputeProvider()
    
    # Example 1: Create VM stack (will succeed)
    print("=== Creating VM Stack ===")
    result1 = await provider.provision_vm_stack(
        "web-server-01",
        "prod-sub",
        "app-rg"
    )
    
    # Example 2: Try to create duplicate NIC in same RG (will fail)
    print("\n=== Attempting Duplicate NIC in Same RG ===")
    try:
        nic_id, nic_data = provider.nic_handler.create_from_config(
            "web-server-01-nic",
            {},
            "prod-sub",
            "app-rg"
        )
        print("✗ Duplicate was allowed (shouldn't happen)")
    except ValueError as e:
        print(f"✓ Duplicate blocked: {e}")
    
    # Example 3: Create NIC with same name in different RG (will succeed)
    print("\n=== Creating NIC with Same Name in Different RG ===")
    try:
        nic_id, nic_data = provider.nic_handler.create_from_config(
            "web-server-01-nic",
            {},
            "prod-sub",
            "network-rg"
        )
        print(f"✓ Created in different RG: {nic_id}")
    except ValueError as e:
        print(f"✗ Failed: {e}")
    
    # Example 4: List VMs in resource group
    print("\n=== Listing VMs in app-rg ===")
    vms = provider.vm_handler.list_by_rg("prod-sub", "app-rg")
    for vm in vms:
        print(f"  - {vm['name']}: {vm['id']}")
    
    # Example 5: Global uniqueness check
    print("\n=== Storage Account Global Uniqueness ===")
    try:
        sa_id1, _ = provider.sa_handler.create_from_config(
            "globalunique123",
            {},
            "sub-1"
        )
        print(f"✓ Created: {sa_id1}")
        
        # Try to create with same name from different subscription
        sa_id2, _ = provider.sa_handler.create_from_config(
            "globalunique123",
            {},
            "sub-2"
        )
        print("✗ Duplicate allowed globally (shouldn't happen)")
    except ValueError as e:
        print(f"✓ Global duplicate blocked: {e}")


# ==================== HANDLER CONFIGURATION REFERENCE ====================

"""
Choose UNIQUENESS_SCOPE based on resource type:

GLOBAL RESOURCES (Globally unique):
- Storage Accounts: name must be globally unique DNS-name
- Management Groups: globally unique in tenant
- Log Analytics Workspaces: globally unique
- Application Insights: globally unique
- Handler: UNIQUENESS_SCOPE = [UniquenessScope.GLOBAL]
- Key: "resource-name"

SUBSCRIPTION-SCOPED (Unique within subscription):
- Resource Groups: unique within subscription
- Subscriptions: global but modeled as sub-scoped
- Handler: UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION]
- Key: "sub:sub-id/resource-name"

RESOURCE GROUP-SCOPED (Unique within RG):
- Virtual Machines: unique within RG
- Network Interfaces: unique within RG
- Disks: unique within RG
- Public IP Addresses: unique within RG
- Network Security Groups: unique within RG
- Handler: UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION, UniquenessScope.RESOURCE_GROUP]
- Key: "sub:sub-id/rg:rg-name/resource-name"

MANAGEMENT GROUP-SCOPED (Unique within MG):
- Policies: can have same name in different MGs
- Policy Assignments: unique within MG
- Blueprints: unique within MG
- Handler: UNIQUENESS_SCOPE = [UniquenessScope.MANAGEMENT_GROUP]
- Key: "mg:mg-id/resource-name"

PARENT RESOURCE-SCOPED (Unique within parent):
- Subnets: unique within Virtual Network
- IP Configurations: unique within NIC
- Scale Set VMs: unique within Scale Set
- Handler: UNIQUENESS_SCOPE = [UniquenessScope.PARENT_RESOURCE]
- Key: "parent:parent-id/resource-name"
"""


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
