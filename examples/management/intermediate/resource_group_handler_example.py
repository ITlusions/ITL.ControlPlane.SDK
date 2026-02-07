"""
ResourceGroup Handler Example

Demonstrates the full ResourceGroup handler using all Big 3 mixins:
1. ValidatedResourceHandler - Pydantic schema validation
2. ProvisioningStateHandler - Lifecycle state management
3. TimestampedResourceHandler - Automatic audit trail

Plus:
4. Subscription-scoped uniqueness (same name allowed in different subscriptions)
5. Schema validation (location, tags format)
6. Full CRUD lifecycle

The ResourceGroupHandler is the reference implementation for building
your own handlers with the Big 3 pattern.
"""

from itl_controlplane_sdk.providers.resource_group_handler import (
    ResourceGroupHandler,
    ResourceGroupSchema,
)
from itl_controlplane_sdk.providers.scoped_resources import UniquenessScope


# ============================================================================
# EXAMPLE 1: Create resource groups with validation
# ============================================================================

def example_1_create_resource_groups():
    """Create resource groups with automatic validation and state management."""
    print("=" * 60)
    print("EXAMPLE 1: Creating Resource Groups")
    print("=" * 60)

    storage = {}
    handler = ResourceGroupHandler(storage)

    # Show handler configuration
    print(f"\nHandler Config:")
    print(f"   Scope:    {[s.value for s in handler.UNIQUENESS_SCOPE]}")
    print(f"   Type:     {handler.RESOURCE_TYPE}")
    print(f"   Schema:   {handler.SCHEMA_CLASS.__name__}")

    # Create a production resource group
    resource_id, config = handler.create_resource(
        "prod-rg",
        {
            "location": "westeurope",
            "tags": {"environment": "production", "team": "platform", "cost-center": "CC-001"},
        },
        "Microsoft.Resources/resourceGroups",
        {
            "subscription_id": "sub-001",
            "user_id": "admin@company.com",
        },
    )

    print(f"\nCreated Resource Group:")
    print(f"   ID:                {resource_id}")
    print(f"   Location:          {config.get('location')}")
    print(f"   Tags:              {config.get('tags')}")
    print(f"   Provisioning:      {config.get('provisioning_state')}")
    print(f"   Created by:        {config.get('createdBy')}")
    print(f"   Created at:        {config.get('createdTime')}")
    print(f"   Modified by:       {config.get('modifiedBy')}")
    print(f"   Modified at:       {config.get('modifiedTime')}")

    # Create a dev resource group
    resource_id2, config2 = handler.create_resource(
        "dev-rg",
        {
            "location": "eastus",
            "tags": {"environment": "development"},
        },
        "Microsoft.Resources/resourceGroups",
        {
            "subscription_id": "sub-001",
            "user_id": "developer@company.com",
        },
    )
    print(f"\nCreated: {config2.get('location')} (by {config2.get('createdBy')})")


# ============================================================================
# EXAMPLE 2: Subscription-scoped uniqueness
# ============================================================================

def example_2_scoping():
    """Demonstrate subscription-scoped uniqueness enforcement."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Subscription-Scoped Uniqueness")
    print("=" * 60)

    storage = {}
    handler = ResourceGroupHandler(storage)

    # Create RG in subscription A
    handler.create_resource(
        "shared-rg",
        {"location": "westeurope"},
        "Microsoft.Resources/resourceGroups",
        {"subscription_id": "sub-A", "user_id": "admin-a@company.com"},
    )
    print(f"\n'shared-rg' created in sub-A")

    # Same name in subscription B → ALLOWED (different subscription)
    handler.create_resource(
        "shared-rg",
        {"location": "eastus"},
        "Microsoft.Resources/resourceGroups",
        {"subscription_id": "sub-B", "user_id": "admin-b@company.com"},
    )
    print(f"'shared-rg' created in sub-B → ALLOWED (different subscription)")

    # Same name in subscription A → BLOCKED (duplicate within subscription)
    try:
        handler.create_resource(
            "shared-rg",
            {"location": "northeurope"},
            "Microsoft.Resources/resourceGroups",
            {"subscription_id": "sub-A", "user_id": "admin-a@company.com"},
        )
    except ValueError as e:
        print(f"'shared-rg' again in sub-A → BLOCKED: {e}")

    print(f"\nScope rule: RG names unique per subscription")
    print(f"   sub-A/shared-rg + sub-B/shared-rg = OK (different subscriptions)")
    print(f"   sub-A/shared-rg + sub-A/shared-rg = BLOCKED (same subscription)")


# ============================================================================
# EXAMPLE 3: Schema validation
# ============================================================================

def example_3_validation():
    """Demonstrate Pydantic schema validation for resource groups."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Schema Validation")
    print("=" * 60)

    storage = {}
    handler = ResourceGroupHandler(storage)

    # Valid schema
    print(f"\nResourceGroupSchema fields:")
    for field_name, field_info in ResourceGroupSchema.model_fields.items():
        print(f"   {field_name}: {field_info.annotation} - {field_info.description}")

    # Invalid location
    try:
        handler.create_resource(
            "bad-location-rg",
            {"location": ""},  # Empty location
            "Microsoft.Resources/resourceGroups",
            {"subscription_id": "sub-001", "user_id": "admin@company.com"},
        )
    except Exception as e:
        print(f"\n Empty location: {e}")

    # Invalid tags (non-string values)
    try:
        handler.create_resource(
            "bad-tags-rg",
            {"location": "westeurope", "tags": {"key": 123}},  # 123 is not a string
            "Microsoft.Resources/resourceGroups",
            {"subscription_id": "sub-001", "user_id": "admin@company.com"},
        )
    except Exception as e:
        print(f" Non-string tag value: {e}")

    # Valid with all fields
    resource_id, config = handler.create_resource(
        "valid-rg",
        {
            "location": "westeurope",
            "tags": {"env": "staging", "team": "qa"},
        },
        "Microsoft.Resources/resourceGroups",
        {"subscription_id": "sub-001", "user_id": "admin@company.com"},
    )
    print(f"\nValid RG created: {config.get('location')}")


# ============================================================================
# EXAMPLE 4: Full CRUD lifecycle
# ============================================================================

def example_4_crud_lifecycle():
    """Full create → get → list → update → delete lifecycle."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Full CRUD Lifecycle")
    print("=" * 60)

    storage = {}
    handler = ResourceGroupHandler(storage)
    scope = {"subscription_id": "sub-001", "user_id": "admin@company.com"}

    # CREATE
    rid1, c1 = handler.create_resource(
        "app-rg", {"location": "westeurope", "tags": {"app": "web"}},
        "Microsoft.Resources/resourceGroups", scope,
    )
    rid2, c2 = handler.create_resource(
        "data-rg", {"location": "northeurope", "tags": {"app": "data"}},
        "Microsoft.Resources/resourceGroups", scope,
    )
    print(f"\nCreated: app-rg, data-rg")

    # GET
    result = handler.get_resource("app-rg", scope)
    if result:
        _, data = result
        print(f"\nGet app-rg:")
        print(f"   Location:     {data.get('location')}")
        print(f"   State:        {data.get('provisioning_state')}")
        print(f"   Created by:   {data.get('createdBy')}")
        print(f"   Tags:         {data.get('tags')}")

    # LIST
    all_rgs = handler.list_resources(scope)
    print(f"\nList all RGs in sub-001: {len(all_rgs)}")
    for rid, data in all_rgs:
        name = rid.split("/")[-1] if "/" in rid else rid
        print(f"   • {name} ({data.get('location')})")

    # UPDATE (via update_resource)
    handler.update_resource(
        "app-rg",
        {"tags": {"app": "web", "version": "2.0", "updated": "true"}},
        {**scope, "user_id": "devops@company.com"},
    )
    updated = handler.get_resource("app-rg", scope)
    if updated:
        _, data = updated
        print(f"\nUpdated app-rg:")
        print(f"   Tags:        {data.get('tags')}")
        print(f"   Modified by: {data.get('modifiedBy')}")
        print(f"   Modified at: {data.get('modifiedTime')}")
        # createdBy should be preserved
        print(f"   Created by:  {data.get('createdBy')} (preserved)")

    # DELETE
    deleted = handler.delete_resource("app-rg", scope)
    if deleted:
        print(f"\n Deleted: app-rg")
    remaining = handler.list_resources(scope)
    print(f"   Remaining: {len(remaining)} RGs")


# ============================================================================
# EXAMPLE 5: Convenience method (create_from_properties)
# ============================================================================

def example_5_convenience_method():
    """Use the simplified create_from_properties method."""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Convenience Method")
    print("=" * 60)

    storage = {}
    handler = ResourceGroupHandler(storage)

    # Use the convenience method
    response = handler.create_from_properties(
        name="quick-rg",
        properties={
            "location": "westeurope",
            "tags": {"created_by": "convenience-method"},
        },
        subscription_id="sub-001",
    )

    print(f"\nCreated via create_from_properties:")
    print(f"   Name:     {response.get('name', 'quick-rg')}")
    print(f"   ID:       {response.get('id')}")
    for key, value in response.items():
        if key not in ("id", "name"):
            print(f"   {key}: {value}")

    print(f"\ncreate_from_properties is a simplified API for quick creation")
    print(f"   Use create_resource for full control over scope and metadata")


if __name__ == "__main__":
    example_1_create_resource_groups()
    example_2_scoping()
    example_3_validation()
    example_4_crud_lifecycle()
    example_5_convenience_method()
    print("\nAll ResourceGroup Handler examples completed!")
