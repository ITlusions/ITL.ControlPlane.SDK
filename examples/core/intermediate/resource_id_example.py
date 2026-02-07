"""
Resource ID Generation and Parsing Example

Demonstrates the dual-ID system used in the ITL ControlPlane SDK:
1. Path-based IDs (ARM-style): /subscriptions/{sub}/resourceGroups/{rg}/providers/{ns}/{type}/{name}
2. GUIDs: Globally unique identifiers for cross-system references
3. ResourceIdentity: Combines both for maximum flexibility

Use cases:
- Generating resource IDs for new resources
- Parsing existing IDs to extract components
- Working with GUID-enhanced IDs for guaranteed uniqueness
"""

from itl_controlplane_sdk.providers.resource_ids import (
    ResourceIdentity,
    generate_resource_id,
    parse_resource_id,
)


# ============================================================================
# EXAMPLE 1: Generate standard ARM-style resource IDs
# ============================================================================

def example_1_basic_resource_ids():
    """Generate standard path-based resource IDs."""
    print("=" * 60)
    print("EXAMPLE 1: Basic Resource ID Generation")
    print("=" * 60)

    # VM in a resource group
    vm_id = generate_resource_id(
        subscription_id="sub-001",
        resource_group="prod-rg",
        provider_namespace="ITL.Compute",
        resource_type="virtualMachines",
        resource_name="web-server-01",
    )
    print(f"\nVM ID:\n  {vm_id}")

    # Storage account (no resource group → subscription-level)
    storage_id = generate_resource_id(
        subscription_id="sub-001",
        resource_group=None,
        provider_namespace="ITL.Storage",
        resource_type="storageAccounts",
        resource_name="proddata2026",
    )
    print(f"\nStorage ID (subscription-level):\n  {storage_id}")

    # Resource group itself
    rg_id = generate_resource_id(
        subscription_id="sub-001",
        resource_group="prod-rg",
        provider_namespace="ITL.Core",
        resource_type="resourcegroups",
        resource_name="prod-rg",
    )
    print(f"\nResource Group ID:\n  {rg_id}")

    # Network resource
    vnet_id = generate_resource_id(
        subscription_id="sub-001",
        resource_group="network-rg",
        provider_namespace="ITL.Network",
        resource_type="virtualNetworks",
        resource_name="prod-vnet",
    )
    print(f"\nVNet ID:\n  {vnet_id}")


# ============================================================================
# EXAMPLE 2: Generate GUID-enhanced IDs for guaranteed uniqueness
# ============================================================================

def example_2_guid_resource_ids():
    """Generate IDs with GUID suffix for cross-system uniqueness."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: GUID-Enhanced Resource IDs")
    print("=" * 60)

    # Standard ID (no GUID)
    standard_id = generate_resource_id(
        subscription_id="sub-001",
        resource_group="prod-rg",
        provider_namespace="ITL.Compute",
        resource_type="virtualMachines",
        resource_name="vm-01",
        include_guid=False,
    )
    print(f"\nStandard (no GUID):\n  {standard_id}")

    # Enhanced ID (with GUID for cross-system tracking)
    enhanced_id = generate_resource_id(
        subscription_id="sub-001",
        resource_group="prod-rg",
        provider_namespace="ITL.Compute",
        resource_type="virtualMachines",
        resource_name="vm-01",
        include_guid=True,
    )
    print(f"\nEnhanced (with GUID):\n  {enhanced_id}")

    # Generating two IDs with same name → different GUIDs
    id_a = generate_resource_id(
        subscription_id="sub-001",
        resource_group="prod-rg",
        provider_namespace="ITL.Compute",
        resource_type="virtualMachines",
        resource_name="vm-01",
        include_guid=True,
    )
    id_b = generate_resource_id(
        subscription_id="sub-001",
        resource_group="prod-rg",
        provider_namespace="ITL.Compute",
        resource_type="virtualMachines",
        resource_name="vm-01",
        include_guid=True,
    )
    print(f"\nSame name, different GUIDs (proves uniqueness):")
    print(f"  A: {id_a}")
    print(f"  B: {id_b}")
    print(f"  Different: {id_a != id_b}")


# ============================================================================
# EXAMPLE 3: Parse resource IDs back to components
# ============================================================================

def example_3_parse_resource_ids():
    """Parse resource IDs to extract subscription, RG, provider, type, name."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Parsing Resource IDs")
    print("=" * 60)

    # Parse a standard resource ID
    vm_id = "/subscriptions/sub-001/resourceGroups/prod-rg/providers/ITL.Compute/virtualMachines/web-server-01"
    parsed = parse_resource_id(vm_id)
    print(f"\nParsing: {vm_id}")
    print(f"  subscription_id:    {parsed.get('subscription_id')}")
    print(f"  resource_group:     {parsed.get('resource_group')}")
    print(f"  provider_namespace: {parsed.get('provider_namespace')}")
    print(f"  resource_type:      {parsed.get('resource_type')}")
    print(f"  resource_name:      {parsed.get('resource_name')}")
    print(f"  guid:               {parsed.get('guid')}")

    # Parse a subscription-level resource ID (no resource group)
    sub_id = "/subscriptions/sub-001/providers/ITL.Storage/storageAccounts/proddata2026"
    parsed_sub = parse_resource_id(sub_id)
    print(f"\nParsing (subscription-level): {sub_id}")
    print(f"  subscription_id:    {parsed_sub.get('subscription_id')}")
    print(f"  resource_group:     {parsed_sub.get('resource_group')}")
    print(f"  provider_namespace: {parsed_sub.get('provider_namespace')}")
    print(f"  resource_type:      {parsed_sub.get('resource_type')}")
    print(f"  resource_name:      {parsed_sub.get('resource_name')}")

    # Parse a GUID-enhanced resource ID
    guid_id = "/subscriptions/sub-001/resourceGroups/prod-rg/providers/ITL.Compute/virtualMachines/vm-01?guid=550e8400-e29b-41d4-a716-446655440000"
    parsed_guid = parse_resource_id(guid_id)
    print(f"\nParsing (with GUID):")
    print(f"  resource_name:      {parsed_guid.get('resource_name')}")
    print(f"  guid:               {parsed_guid.get('guid')}")


# ============================================================================
# EXAMPLE 4: ResourceIdentity class for dual-ID management
# ============================================================================

def example_4_resource_identity():
    """Use ResourceIdentity for combined path + GUID management."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: ResourceIdentity (Dual-ID System)")
    print("=" * 60)

    # Create identity with auto-generated GUID
    vm_identity = ResourceIdentity.create(
        subscription_id="sub-001",
        resource_group="prod-rg",
        provider_namespace="ITL.Compute",
        resource_type="virtualMachines",
        resource_name="web-server-01",
    )
    print(f"\nVM Identity:")
    print(f"  Path ID:  {vm_identity.resource_id}")
    print(f"  GUID:     {vm_identity.resource_guid}")

    # Create identity with a specific GUID (e.g., from database)
    known_guid = "550e8400-e29b-41d4-a716-446655440000"
    db_identity = ResourceIdentity.create(
        subscription_id="sub-001",
        resource_group="prod-rg",
        provider_namespace="ITL.Compute",
        resource_type="virtualMachines",
        resource_name="db-server-01",
        guid=known_guid,
    )
    print(f"\nDB Identity (known GUID):")
    print(f"  Path ID:  {db_identity.resource_id}")
    print(f"  GUID:     {db_identity.resource_guid}")

    # Subscription-level resource (no resource group)
    sub_identity = ResourceIdentity.create(
        subscription_id="sub-001",
        resource_group=None,
        provider_namespace="ITL.Storage",
        resource_type="storageAccounts",
        resource_name="globalstore",
    )
    print(f"\nSubscription-level Identity:")
    print(f"  Path ID:  {sub_identity.resource_id}")
    print(f"  GUID:     {sub_identity.resource_guid}")

    # Serialize to dict (useful for API responses and storage)
    identity_dict = vm_identity.model_dump()
    print(f"\nSerialized to dict:")
    for key, value in identity_dict.items():
        print(f"  {key}: {value}")


# ============================================================================
# EXAMPLE 5: Real-world pattern - building resource references
# ============================================================================

def example_5_real_world_patterns():
    """Practical patterns for working with resource IDs in production."""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Real-World Patterns")
    print("=" * 60)

    # Pattern 1: Create resources and track by identity
    resources = {}
    for i in range(3):
        identity = ResourceIdentity.create(
            subscription_id="sub-prod-001",
            resource_group="app-rg",
            provider_namespace="ITL.Compute",
            resource_type="virtualMachines",
            resource_name=f"worker-{i:02d}",
        )
        resources[identity.resource_guid] = {
            "identity": identity,
            "status": "Running",
        }

    print(f"\nCreated {len(resources)} VM resources:")
    for guid, info in resources.items():
        print(f"  [{guid[:8]}...] {info['identity'].resource_id}")

    # Pattern 2: Cross-reference resources by parsing IDs
    vm_id = "/subscriptions/sub-001/resourceGroups/prod-rg/providers/ITL.Compute/virtualMachines/app-vm"
    nic_id = "/subscriptions/sub-001/resourceGroups/prod-rg/providers/ITL.Network/networkInterfaces/app-vm-nic"

    vm_parts = parse_resource_id(vm_id)
    nic_parts = parse_resource_id(nic_id)

    same_rg = vm_parts.get("resource_group") == nic_parts.get("resource_group")
    same_sub = vm_parts.get("subscription_id") == nic_parts.get("subscription_id")
    print(f"\nCross-reference check:")
    print(f"  VM:  {vm_parts.get('resource_name')} ({vm_parts.get('provider_namespace')})")
    print(f"  NIC: {nic_parts.get('resource_name')} ({nic_parts.get('provider_namespace')})")
    print(f"  Same subscription: {same_sub}")
    print(f"  Same resource group: {same_rg}")

    # Pattern 3: Build child resource IDs from parent
    parent_id = "/subscriptions/sub-001/resourceGroups/prod-rg/providers/ITL.Network/virtualNetworks/prod-vnet"
    parent = parse_resource_id(parent_id)
    subnet_id = generate_resource_id(
        subscription_id=parent["subscription_id"],
        resource_group=parent["resource_group"],
        provider_namespace=parent["provider_namespace"],
        resource_type="subnets",
        resource_name="web-subnet",
    )
    print(f"\nChild resource from parent:")
    print(f"  Parent VNet: {parent_id}")
    print(f"  Child Subnet: {subnet_id}")


if __name__ == "__main__":
    example_1_basic_resource_ids()
    example_2_guid_resource_ids()
    example_3_parse_resource_ids()
    example_4_resource_identity()
    example_5_real_world_patterns()
    print("\nAll Resource ID examples completed!")
