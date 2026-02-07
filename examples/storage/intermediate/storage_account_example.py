"""
Storage Account Handler with GLOBAL Scoping

Key difference from VMs (RG-scoped):
- Storage account names must be GLOBALLY unique (like DNS names)
- Names become endpoints: https://{name}.blob.core.itlcloud.net
- Scope context is empty {} for uniqueness checks (no RG boundary)

Demonstrates:
1. StorageAccountSchema with naming + type validation
2. StorageAccountHandler using Big 3 mixins + GLOBAL scoping
3. Comparison between GLOBAL vs RESOURCE_GROUP scoping
4. Real-world create/get/list/delete lifecycle
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
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
# SCHEMA: Storage Account Validation
# ============================================================================

class StorageAccountSchema(BaseModel):
    """
    Pydantic validation schema for Storage Accounts.
    
    Rules (matching cloud provider conventions):
    - Name: 3-24 chars, lowercase alphanumeric only (no hyphens!)
    - Account type: Standard_LRS, Standard_GRS, Premium_LRS, etc.
    - Access tier: Hot or Cool
    - Kind: StorageV2, BlobStorage, BlockBlobStorage
    """

    name: str = Field(..., description="Storage account name (3-24 chars, lowercase alphanumeric)")
    account_type: str = Field(default="Standard_LRS", description="Replication type")
    access_tier: str = Field(default="Hot", description="Access tier: Hot or Cool")
    kind: str = Field(default="StorageV2", description="Storage account kind")
    location: str = Field(..., description="Deployment region")
    enable_https_only: bool = Field(default=True, description="Require HTTPS")
    tags: Optional[Dict[str, str]] = Field(default_factory=dict)

    @validator('name')
    def validate_storage_name(cls, v):
        """Storage names: 3-24 chars, lowercase letters and numbers only."""
        if not v or len(v) < 3 or len(v) > 24:
            raise ValueError('Storage account name must be 3-24 characters')
        if not re.match(r'^[a-z0-9]+$', v):
            raise ValueError('Storage account name must contain only lowercase letters and numbers')
        return v

    @validator('account_type')
    def validate_account_type(cls, v):
        valid_types = {
            'Standard_LRS', 'Standard_GRS', 'Standard_RAGRS',
            'Standard_ZRS', 'Premium_LRS', 'Premium_ZRS',
        }
        if v not in valid_types:
            raise ValueError(f'Invalid account type. Must be one of: {", ".join(sorted(valid_types))}')
        return v

    @validator('access_tier')
    def validate_access_tier(cls, v):
        if v not in ('Hot', 'Cool'):
            raise ValueError('Access tier must be Hot or Cool')
        return v

    @validator('kind')
    def validate_kind(cls, v):
        valid_kinds = {'StorageV2', 'BlobStorage', 'BlockBlobStorage', 'FileStorage'}
        if v not in valid_kinds:
            raise ValueError(f'Invalid kind. Must be one of: {", ".join(sorted(valid_kinds))}')
        return v


# ============================================================================
# HANDLER: Storage Account Handler with Global Scoping
# ============================================================================

class StorageAccountHandler(
    ValidatedResourceHandler,
    ProvisioningStateHandler,
    TimestampedResourceHandler,
    ScopedResourceHandler,
):
    """
    Storage Account handler with GLOBAL scoping.
    
    Unlike VMs (SUBSCRIPTION + RESOURCE_GROUP scoped), storage accounts
    are GLOBALLY unique because their names become DNS endpoints.
    
    Scope comparison:
    ┌──────────────────┬─────────────────────────────────────────┐
    │ Resource         │ Scoping                                 │
    ├──────────────────┼─────────────────────────────────────────┤
    │ Virtual Machine  │ [SUBSCRIPTION, RESOURCE_GROUP]          │
    │                  │ → "vm-01" can exist in multiple RGs     │
    │ Resource Group   │ [SUBSCRIPTION]                          │
    │                  │ → "prod-rg" unique per subscription     │
    │ Storage Account  │ [GLOBAL]                                │
    │                  │ → "mydata2026" unique across ALL tenants│
    └──────────────────┴─────────────────────────────────────────┘
    
    Usage:
        handler = StorageAccountHandler(storage_dict)
        resource_id, config = handler.create_resource(
            "proddata2026",
            {
                "name": "proddata2026",
                "location": "westeurope",
                "account_type": "Standard_GRS",
                "access_tier": "Hot",
                "kind": "StorageV2",
            },
            "ITL.Storage/storageAccounts",
            {"user_id": "admin@company.com"}
        )
    """

    # GLOBAL scope: name must be unique across the entire system
    UNIQUENESS_SCOPE = [UniquenessScope.GLOBAL]
    RESOURCE_TYPE = "storageaccounts"
    SCHEMA_CLASS = StorageAccountSchema

    def __init__(self, storage_dict: Dict[str, Any]):
        super().__init__(storage_dict)

    def _generate_resource_id(self, name: str, resource_type: str, scope_context: Dict[str, str]) -> str:
        """
        Generate storage account resource ID.
        
        Storage accounts are subscription-level resources in the ID path,
        but globally unique in naming.
        """
        subscription_id = scope_context.get("subscription_id", "global")
        return f"/subscriptions/{subscription_id}/providers/ITL.Storage/storageAccounts/{name}"


# ============================================================================
# EXAMPLE 1: Global uniqueness enforcement
# ============================================================================

def example_1_global_uniqueness():
    """Demonstrate that storage account names are globally unique."""
    print("=" * 60)
    print("EXAMPLE 1: Global Uniqueness Enforcement")
    print("=" * 60)

    storage = {}
    handler = StorageAccountHandler(storage)

    # Create first storage account
    resource_id, config = handler.create_resource(
        "proddata2026",
        {
            "name": "proddata2026",
            "location": "westeurope",
            "account_type": "Standard_GRS",
            "access_tier": "Hot",
            "kind": "StorageV2",
        },
        "ITL.Storage/storageAccounts",
        {"user_id": "admin@company.com"},
    )

    print(f"\nCreated storage account:")
    print(f"   ID:                {resource_id}")
    print(f"   Name:              {config.get('name')}")
    print(f"   Provisioning:      {config.get('provisioning_state')}")
    print(f"   Created by:        {config.get('createdBy')}")
    print(f"   Created at:        {config.get('createdTime')}")

    # Try creating same name → should fail (GLOBAL uniqueness)
    try:
        handler.create_resource(
            "proddata2026",
            {
                "name": "proddata2026",
                "location": "eastus",
                "account_type": "Standard_LRS",
            },
            "ITL.Storage/storageAccounts",
            {"user_id": "other-user@company.com"},
        )
        print("\nShould not reach here!")
    except ValueError as e:
        print(f"\n Duplicate blocked (GLOBAL scope): {e}")
        print("   → Same name cannot be used anywhere, even in different subscriptions")

    # Different name works fine
    resource_id2, config2 = handler.create_resource(
        "devdata2026",
        {
            "name": "devdata2026",
            "location": "eastus",
            "account_type": "Standard_LRS",
            "access_tier": "Cool",
            "kind": "StorageV2",
        },
        "ITL.Storage/storageAccounts",
        {"user_id": "dev@company.com"},
    )
    print(f"\nCreated second account: {config2.get('name')} (different name → OK)")


# ============================================================================
# EXAMPLE 2: Schema validation
# ============================================================================

def example_2_schema_validation():
    """Show validation rules for storage account names and types."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Schema Validation")
    print("=" * 60)

    storage = {}
    handler = StorageAccountHandler(storage)

    # Invalid name: too short
    try:
        handler.create_resource(
            "ab",
            {"name": "ab", "location": "westeurope"},
            "ITL.Storage/storageAccounts",
            {"user_id": "admin@company.com"},
        )
    except Exception as e:
        print(f"\n Name too short: {e}")

    # Invalid name: contains hyphens (not allowed for storage)
    try:
        handler.create_resource(
            "my-storage",
            {"name": "my-storage", "location": "westeurope"},
            "ITL.Storage/storageAccounts",
            {"user_id": "admin@company.com"},
        )
    except Exception as e:
        print(f" Hyphens not allowed: {e}")

    # Invalid name: uppercase
    try:
        handler.create_resource(
            "MyStorage",
            {"name": "MyStorage", "location": "westeurope"},
            "ITL.Storage/storageAccounts",
            {"user_id": "admin@company.com"},
        )
    except Exception as e:
        print(f" Uppercase not allowed: {e}")

    # Invalid account type
    try:
        handler.create_resource(
            "goodname123",
            {"name": "goodname123", "location": "westeurope", "account_type": "FakeType"},
            "ITL.Storage/storageAccounts",
            {"user_id": "admin@company.com"},
        )
    except Exception as e:
        print(f" Invalid account type: {e}")

    # Valid creation
    resource_id, config = handler.create_resource(
        "validaccount42",
        {
            "name": "validaccount42",
            "location": "westeurope",
            "account_type": "Premium_LRS",
            "access_tier": "Hot",
            "kind": "BlockBlobStorage",
        },
        "ITL.Storage/storageAccounts",
        {"user_id": "admin@company.com"},
    )
    print(f"\nValid account created: {config.get('name')} ({config.get('account_type')})")


# ============================================================================
# EXAMPLE 3: Compare Global vs RG-scoped resources
# ============================================================================

def example_3_scope_comparison():
    """
    Side-by-side comparison: Storage (GLOBAL) vs VM (SUBSCRIPTION + RG).
    
    This demonstrates WHY scoping matters:
    - VMs: Same name allowed in different resource groups
    - Storage: Name must be unique everywhere
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Scope Comparison (Global vs RG-Scoped)")
    print("=" * 60)

    # --- Storage Account: GLOBAL scoping ---
    sa_storage = {}
    sa_handler = StorageAccountHandler(sa_storage)

    # Create in "subscription A"
    sa_handler.create_resource(
        "shareddata2026",
        {"name": "shareddata2026", "location": "westeurope", "kind": "StorageV2"},
        "ITL.Storage/storageAccounts",
        {"subscription_id": "sub-A", "user_id": "admin@a.com"},
    )
    print(f"\nStorage 'shareddata2026' created in sub-A")

    # Try same name in "subscription B" → BLOCKED (global)
    try:
        sa_handler.create_resource(
            "shareddata2026",
            {"name": "shareddata2026", "location": "eastus", "kind": "StorageV2"},
            "ITL.Storage/storageAccounts",
            {"subscription_id": "sub-B", "user_id": "admin@b.com"},
        )
    except ValueError:
        print(f"   Same name in sub-B → BLOCKED (globally unique)")

    # --- VM-like handler: SUBSCRIPTION + RG scoping ---
    print()

    class SimpleVMHandler(ScopedResourceHandler):
        UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION, UniquenessScope.RESOURCE_GROUP]
        RESOURCE_TYPE = "virtualmachines"

    vm_storage = {}
    vm_handler = SimpleVMHandler(vm_storage)

    # Create in rg-A
    vm_handler.create_resource(
        "web-server",
        {"size": "Standard_D2s_v3"},
        "ITL.Compute/virtualMachines",
        {"subscription_id": "sub-001", "resource_group": "rg-A", "user_id": "admin"},
    )
    print(f"VM 'web-server' created in rg-A")

    # Same name in rg-B → ALLOWED (different RG scope)
    vm_handler.create_resource(
        "web-server",
        {"size": "Standard_D2s_v3"},
        "ITL.Compute/virtualMachines",
        {"subscription_id": "sub-001", "resource_group": "rg-B", "user_id": "admin"},
    )
    print(f"   Same name in rg-B → ALLOWED (RG-scoped)")

    # Same name in same RG → BLOCKED (duplicate within scope)
    try:
        vm_handler.create_resource(
            "web-server",
            {"size": "Standard_D4s_v3"},
            "ITL.Compute/virtualMachines",
            {"subscription_id": "sub-001", "resource_group": "rg-A", "user_id": "admin"},
        )
    except ValueError:
        print(f"   Same name in rg-A again → BLOCKED (duplicate in scope)")

    print(f"\nSummary:")
    print(f"   Storage: GLOBAL   → name unique across entire system")
    print(f"   VM:      SUB + RG → name unique within subscription + resource group")


# ============================================================================
# EXAMPLE 4: Full CRUD lifecycle
# ============================================================================

def example_4_full_lifecycle():
    """Complete create → get → list → update → delete lifecycle."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Full CRUD Lifecycle")
    print("=" * 60)

    storage = {}
    handler = StorageAccountHandler(storage)
    scope = {"user_id": "admin@company.com"}

    # CREATE
    rid1, c1 = handler.create_resource(
        "appdata2026", {"name": "appdata2026", "location": "westeurope", "kind": "StorageV2"},
        "ITL.Storage/storageAccounts", scope,
    )
    rid2, c2 = handler.create_resource(
        "backups2026", {"name": "backups2026", "location": "northeurope", "access_tier": "Cool", "kind": "StorageV2"},
        "ITL.Storage/storageAccounts", scope,
    )
    print(f"\nCreated: appdata2026, backups2026")

    # GET
    result = handler.get_resource("appdata2026", scope)
    if result:
        _, data = result
        print(f"\nGet appdata2026:")
        print(f"   State:    {data.get('provisioning_state')}")
        print(f"   Created:  {data.get('createdTime')}")
        print(f"   By:       {data.get('createdBy')}")

    # LIST
    all_resources = handler.list_resources(scope)
    print(f"\nAll storage accounts: {len(all_resources)}")
    for rid, data in all_resources:
        print(f"   • {data.get('name', 'unknown')} ({data.get('location', '?')})")

    # DELETE
    deleted = handler.delete_resource("appdata2026", scope)
    if deleted:
        print(f"\n Deleted: appdata2026")

    remaining = handler.list_resources(scope)
    print(f"   Remaining: {len(remaining)}")

    print("\nAll Storage Account examples completed!")


if __name__ == "__main__":
    example_1_global_uniqueness()
    example_2_schema_validation()
    example_3_scope_comparison()
    example_4_full_lifecycle()
