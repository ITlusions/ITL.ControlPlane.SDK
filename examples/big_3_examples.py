"""
Example implementations using the Big 3 base classes.

Demonstrates how to use:
1. TimestampedResourceHandler - Auto timestamps
2. ProvisioningStateHandler - Lifecycle management
3. ValidatedResourceHandler - Schema validation
"""

from pydantic import BaseModel, validator, Field
from typing import Optional
import re

from itl_controlplane_sdk.providers import (
    ValidatedResourceHandler,
    ProvisioningStateHandler,
    TimestampedResourceHandler,
    ScopedResourceHandler,
    UniquenessScope,
    ProvisioningState,
)


# ============================================================================
# EXAMPLE 1: Virtual Machine Handler with Full Validation
# ============================================================================

class VirtualMachineSchema(BaseModel):
    """Pydantic schema for VM validation."""
    
    vm_name: str = Field(..., description="Name of the VM (3-63 chars)")
    size: str = Field(..., description="VM size like Standard_D2s_v3")
    os_type: str = Field(..., description="Windows or Linux")
    admin_username: Optional[str] = None
    image_publisher: Optional[str] = None
    image_offer: Optional[str] = None
    image_sku: Optional[str] = None
    
    @validator('vm_name')
    def validate_vm_name(cls, v):
        """VM names: 3-63 chars, alphanumeric + hyphen, no leading/trailing hyphen."""
        if not v or len(v) < 3 or len(v) > 63:
            raise ValueError('VM name must be 3-63 characters')
        if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$', v):
            raise ValueError('VM name must contain only alphanumeric and hyphens')
        return v
    
    @validator('size')
    def validate_size(cls, v):
        """Only allow known Azure sizes."""
        valid_sizes = {
            'Standard_B1s', 'Standard_B1ms', 'Standard_B2s', 'Standard_B2ms',
            'Standard_D2s_v3', 'Standard_D4s_v3', 'Standard_D8s_v3',
            'Standard_E2s_v3', 'Standard_E4s_v3', 'Standard_E8s_v3',
        }
        if v not in valid_sizes:
            raise ValueError(f'Invalid VM size. Must be one of: {", ".join(valid_sizes)}')
        return v
    
    @validator('os_type')
    def validate_os(cls, v):
        """Only Windows or Linux."""
        if v not in ('Windows', 'Linux'):
            raise ValueError('OS type must be Windows or Linux')
        return v


class VirtualMachineHandler(ValidatedResourceHandler, ProvisioningStateHandler, TimestampedResourceHandler, ScopedResourceHandler):
    """
    Handler for Virtual Machines with:
    - Subscription + Resource Group scoping
    - Pydantic schema validation
    - Provisioning state management
    - Automatic timestamps
    
    Example:
        handler = VirtualMachineHandler(storage_dict)
        
        # Create with automatic validation
        resource_id, config = handler.create_resource(
            "web-vm-01",
            {
                "vm_name": "web-vm-01",
                "size": "Standard_D2s_v3",
                "os_type": "Linux",
                "admin_username": "azureuser"
            },
            "Microsoft.Compute/virtualMachines",
            {
                "subscription_id": "sub-123",
                "resource_group": "prod-rg",
                "user_id": "operator@company.com"
            }
        )
        
        # Invalid VM name raises ValueError
        handler.create_resource(
            "x",  # Too short!
            {"vm_name": "x", "size": "Standard_D2s_v3", "os_type": "Linux"},
            ...
        )
        # → ValueError: VM name must be 3-63 characters
    """
    
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION, UniquenessScope.RESOURCE_GROUP]
    RESOURCE_TYPE = "virtualmachines"
    SCHEMA_CLASS = VirtualMachineSchema
    
    def _generate_resource_id(self, name: str, resource_type: str, scope_context: dict) -> str:
        """Generate Azure-standard VM resource ID."""
        sub_id = scope_context.get("subscription_id", "")
        rg_name = scope_context.get("resource_group", "")
        return f"/subscriptions/{sub_id}/resourceGroups/{rg_name}/providers/Microsoft.Compute/virtualMachines/{name}"


# ============================================================================
# EXAMPLE 2: Storage Account Handler (Global Scope)
# ============================================================================

class StorageAccountSchema(BaseModel):
    """Storage account validation."""
    
    account_name: str = Field(..., description="Name of storage account")
    account_type: str = Field(..., description="Standard_LRS, Standard_GRS, etc")
    access_tier: Optional[str] = Field("Hot", description="Hot or Cool")
    
    @validator('account_name')
    def validate_name(cls, v):
        """Storage accounts: 3-24 chars, lowercase alphanumeric only."""
        if not v or len(v) < 3 or len(v) > 24:
            raise ValueError('Storage account name must be 3-24 characters')
        if not re.match(r'^[a-z0-9]+$', v):
            raise ValueError('Storage account name must be lowercase alphanumeric only')
        return v
    
    @validator('account_type')
    def validate_type(cls, v):
        """Validate storage type."""
        valid = {'Standard_LRS', 'Standard_GRS', 'Standard_RAGRS', 'Premium_LRS'}
        if v not in valid:
            raise ValueError(f'Invalid type: {v}')
        return v


class StorageAccountHandler(ValidatedResourceHandler, ProvisioningStateHandler, TimestampedResourceHandler, ScopedResourceHandler):
    """
    Handler for Storage Accounts with:
    - GLOBAL scoping (names must be unique across Azure)
    - Pydantic schema validation
    - Provisioning state management
    
    Usage:
        handler = StorageAccountHandler(storage_dict)
        
        resource_id, config = handler.create_resource(
            "proddata2025",
            {
                "account_name": "proddata2025",
                "account_type": "Standard_GRS",
                "access_tier": "Cool"
            },
            "Microsoft.Storage/storageAccounts",
            {"user_id": "admin@company.com"}
        )
        
        # Raises error - globally unique
        handler.create_resource(
            "proddata2025",  # Already exists globally!
            ...
        )
    """
    
    UNIQUENESS_SCOPE = [UniquenessScope.GLOBAL]
    RESOURCE_TYPE = "storageaccounts"
    SCHEMA_CLASS = StorageAccountSchema
    
    def _generate_resource_id(self, name: str, resource_type: str, scope_context: dict) -> str:
        """Generate Storage Account resource ID."""
        sub_id = scope_context.get("subscription_id", "")
        rg_name = scope_context.get("resource_group", "")
        return f"/subscriptions/{sub_id}/resourceGroups/{rg_name}/providers/Microsoft.Storage/storageAccounts/{name}"


# ============================================================================
# EXAMPLE 3: Network Interface Handler
# ============================================================================

class NetworkInterfaceSchema(BaseModel):
    """NIC validation."""
    
    nic_name: str = Field(..., description="NIC name")
    vm_id: str = Field(..., description="VM resource ID")
    subnet_id: str = Field(..., description="Subnet resource ID")
    private_ip: Optional[str] = None
    
    @validator('nic_name')
    def validate_name(cls, v):
        """NIC naming convention."""
        if not v or len(v) < 3 or len(v) > 80:
            raise ValueError('NIC name must be 3-80 characters')
        return v


class NetworkInterfaceHandler(ValidatedResourceHandler, ProvisioningStateHandler, TimestampedResourceHandler, ScopedResourceHandler):
    """
    Handler for Network Interfaces with:
    - Subscription + Resource Group scoping
    - Pydantic schema validation
    - Linked to VMs and Subnets
    """
    
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION, UniquenessScope.RESOURCE_GROUP]
    RESOURCE_TYPE = "networkinterfaces"
    SCHEMA_CLASS = NetworkInterfaceSchema


# ============================================================================
# EXAMPLE 4: Database Handler (RG Scoped)
# ============================================================================

class DatabaseSchema(BaseModel):
    """Database validation."""
    
    db_name: str = Field(..., description="Database name")
    edition: str = Field(..., description="Basic, Standard, Premium")
    max_size_gb: int = Field(5, ge=1, le=1024, description="Max size in GB")
    
    @validator('db_name')
    def validate_name(cls, v):
        if not v or len(v) < 1 or len(v) > 128:
            raise ValueError('Database name must be 1-128 characters')
        return v
    
    @validator('edition')
    def validate_edition(cls, v):
        if v not in ('Basic', 'Standard', 'Premium'):
            raise ValueError('Edition must be Basic, Standard, or Premium')
        return v


class DatabaseHandler(ValidatedResourceHandler, ProvisioningStateHandler, TimestampedResourceHandler, ScopedResourceHandler):
    """Handler for SQL Databases with RG scoping."""
    
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION, UniquenessScope.RESOURCE_GROUP]
    RESOURCE_TYPE = "sqldatabases"
    SCHEMA_CLASS = DatabaseSchema


# ============================================================================
# Usage Examples
# ============================================================================

def example_vm_creation():
    """Example: Create and manage a virtual machine."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Virtual Machine with Validation")
    print("="*70)
    
    storage = {}
    handler = VirtualMachineHandler(storage)
    
    # Valid creation
    try:
        resource_id, config = handler.create_resource(
            "web-server-01",
            {
                "vm_name": "web-server-01",
                "size": "Standard_D2s_v3",
                "os_type": "Linux",
                "admin_username": "azureuser"
            },
            "Microsoft.Compute/virtualMachines",
            {
                "subscription_id": "prod-sub",
                "resource_group": "production",
                "user_id": "admin@company.com"
            }
        )
        print(f"[OK] Created: {resource_id}")
        print(f"    State: {config['provisioning_state']}")
        print(f"    Created: {config['createdTime']}")
        print(f"    Created By: {config['createdBy']}")
    except Exception as e:
        print(f"[ERROR] Error: {e}")
    
    # Invalid size
    try:
        print("\n[*] Attempting invalid size...")
        handler.create_resource(
            "invalid-vm",
            {
                "vm_name": "invalid-vm",
                "size": "InvalidSize",  # Not a real Azure size
                "os_type": "Linux"
            },
            "Microsoft.Compute/virtualMachines",
            {"subscription_id": "prod-sub", "resource_group": "production"}
        )
    except ValueError as e:
        print(f"[OK] Validation caught error: {e}")
    
    # Invalid OS
    try:
        print("\n[*] Attempting invalid OS type...")
        handler.create_resource(
            "invalid-vm2",
            {
                "vm_name": "invalid-vm2",
                "size": "Standard_D2s_v3",
                "os_type": "AIX"  # Not Windows or Linux
            },
            "Microsoft.Compute/virtualMachines",
            {"subscription_id": "prod-sub", "resource_group": "production"}
        )
    except ValueError as e:
        print(f"[OK] Validation caught error: {e}")


def example_storage_global_scope():
    """Example: Storage account with global uniqueness."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Storage Account (Global Scope)")
    print("="*70)
    
    storage = {}
    handler = StorageAccountHandler(storage)
    
    # Create first storage account
    try:
        resource_id, config = handler.create_resource(
            "mydata2025",
            {
                "account_name": "mydata2025",
                "account_type": "Standard_GRS",
                "access_tier": "Hot"
            },
            "Microsoft.Storage/storageAccounts",
            {
                "subscription_id": "prod-sub",
                "resource_group": "storage-rg",
                "user_id": "admin@company.com"
            }
        )
        print(f"[OK] Created: {resource_id}")
        print(f"    State: {config['provisioning_state']}")
    except Exception as e:
        print(f"[ERROR] Error: {e}")
    
    # Try to create duplicate (should fail - GLOBAL scope)
    try:
        print("\n[*] Attempting duplicate (global scope)...")
        handler.create_resource(
            "mydata2025",  # Same name
            {"account_name": "mydata2025", "account_type": "Standard_LRS"},
            "Microsoft.Storage/storageAccounts",
            {"subscription_id": "other-sub", "resource_group": "other-rg"}
        )
    except ValueError as e:
        print(f"[OK] Correctly blocked: {e}")


def example_provisioning_states():
    """Example: Provisioning state transitions."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Provisioning State Management")
    print("="*70)
    
    storage = {}
    handler = VirtualMachineHandler(storage)
    
    # Create VM (should auto-transition to Succeeded)
    resource_id, config = handler.create_resource(
        "app-server",
        {
            "vm_name": "app-server",
            "size": "Standard_D2s_v3",
            "os_type": "Linux"
        },
        "Microsoft.Compute/virtualMachines",
        {
            "subscription_id": "prod-sub",
            "resource_group": "production",
            "user_id": "admin@company.com"
        }
    )
    
    print(f"[OK] Created: {resource_id}")
    print(f"    Final State: {config['provisioning_state']}")
    
    # Check state history
    history = handler.get_state_history(resource_id)
    print(f"\n[*] State Transitions:")
    for transition in history:
        print(f"    {transition['state']:12} @ {transition['timestamp']}")
    
    # Delete (transitions through Deleting → Deleted)
    print(f"\n[*] Deleting resource...")
    deleted = handler.delete_resource(
        "app-server",
        {"subscription_id": "prod-sub", "resource_group": "production"}
    )
    
    if deleted:
        print(f"[OK] Deleted successfully")
    
    # Check final state history
    history = handler.get_state_history(resource_id)
    print(f"\n[*] Final State History:")
    for transition in history:
        print(f"    {transition['state']:12} @ {transition['timestamp']}")


if __name__ == "__main__":
    example_vm_creation()
    example_storage_global_scope()
    example_provisioning_states()
    
    print("\n" + "="*70)
    print("[SUCCESS] All examples completed!")
    print("="*70)
