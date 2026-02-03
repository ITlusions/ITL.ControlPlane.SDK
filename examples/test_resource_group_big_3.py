"""
Test ResourceGroupHandler with Big 3 Features with Dynamic LocationsHandler
Demonstrates: TimestampedResourceHandler, ProvisioningStateHandler, ValidatedResourceHandler
Uses dynamic LocationsHandler for Azure region validation
"""
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from itl_controlplane_sdk.providers.resource_group_handler import ResourceGroupHandler
from itl_controlplane_sdk.providers.locations import LocationsHandler, AzureLocation


def test_1_create_with_validation():
    """Test 1: Create RG with validation"""
    print("\n" + "="*70)
    print("TEST 1: Resource Group Creation with Validation")
    print("="*70)
    
    storage = {}
    handler = ResourceGroupHandler(storage)
    
    # Test 1a: Valid creation
    print("\n[->] Creating resource group 'prod-rg' in eastus...")
    try:
        resource_id, rg_config = handler.create_resource(
            "prod-rg",
            {
                "location": "eastus",
                "tags": {"env": "production", "team": "platform"}
            },
            "Microsoft.Resources/resourceGroups",
            {
                "subscription_id": "sub-prod-001",
                "user_id": "admin@company.com"
            }
        )
        
        print(f"[OK] Created: {resource_id}")
        print(f"    State: {rg_config.get('provisioning_state')}")
        print(f"    Location: {rg_config.get('location')}")
        print(f"    Created by: {rg_config.get('createdBy')}")
        print(f"    Created at: {rg_config.get('createdTime')}")
        print(f"    Tags: {rg_config.get('tags')}")
        
        # Verify Big 3 features
        assert rg_config.get('provisioning_state') == 'Succeeded', "State should be Succeeded"
        assert rg_config.get('createdBy') == 'admin@company.com', "createdBy should be set"
        assert rg_config.get('createdTime') is not None, "createdTime should be set"
        assert rg_config.get('location') == 'eastus', "location should be eastus"
        print("[OK] All Big 3 features present!")
        
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False
    
    # Test 1b: Validation error - invalid location
    print("\n[->] Attempting to create RG with invalid location...")
    try:
        handler.create_resource(
            "bad-rg",
            {
                "location": "invalid-region",
                "tags": {}
            },
            "Microsoft.Resources/resourceGroups",
            {
                "subscription_id": "sub-prod-001",
                "user_id": "admin@company.com"
            }
        )
        print("[FAIL] Should have failed validation!")
        return False
    except ValueError as e:
        if "not a valid Azure location" in str(e) or "Location must be one of" in str(e):
            print(f"[OK] Validation caught: {str(e)[:70]}...")
        else:
            print(f"[FAIL] Wrong error: {e}")
            return False
    
    # Test 1c: Validation error - duplicate in subscription
    print("\n[->] Attempting to create duplicate RG in same subscription...")
    try:
        handler.create_resource(
            "prod-rg",
            {
                "location": "westus",
                "tags": {}
            },
            "Microsoft.Resources/resourceGroups",
            {
                "subscription_id": "sub-prod-001",
                "user_id": "admin@company.com"
            }
        )
        print("[FAIL] Should have detected duplicate!")
        return False
    except ValueError as e:
        if "already exists" in str(e):
            print(f"[OK] Correctly blocked duplicate: {str(e)}")
        else:
            print(f"[FAIL] Wrong error: {e}")
            return False
    
    return True


def test_2_timestamps_on_creation():
    """Test 2: Timestamps automatically added on creation"""
    print("\n" + "="*70)
    print("TEST 2: Automatic Timestamps on Creation")
    print("="*70)
    
    storage = {}
    handler = ResourceGroupHandler(storage)
    
    # Create
    print("\n[->] Creating resource group 'dev-rg'...")
    resource_id, rg_config = handler.create_resource(
        "dev-rg",
        {"location": "westus", "tags": {"env": "dev"}},
        "Microsoft.Resources/resourceGroups",
        {
            "subscription_id": "sub-dev-001",
            "user_id": "alice@company.com"
        }
    )
    
    created_time = rg_config.get('createdTime')
    created_by = rg_config.get('createdBy')
    modified_time = rg_config.get('modifiedTime')
    modified_by = rg_config.get('modifiedBy')
    
    print(f"[OK] Created at: {created_time} by {created_by}")
    print(f"    Modified at: {modified_time} by {modified_by}")
    assert created_by == 'alice@company.com', "createdBy should be alice"
    assert modified_by == 'alice@company.com', "modifiedBy should initially be alice"
    assert created_time is not None, "createdTime should be set"
    assert modified_time is not None, "modifiedTime should be set"
    
    # Verify timestamps are ISO 8601 format
    assert created_time.endswith('Z'), "Timestamps should be UTC (end with Z)"
    print("[OK] Timestamps correctly added in ISO 8601 format!")
    
    return True


def test_3_state_transitions():
    """Test 3: Provisioning state lifecycle"""
    print("\n" + "="*70)
    print("TEST 3: Provisioning State Management")
    print("="*70)
    
    storage = {}
    handler = ResourceGroupHandler(storage)
    
    # Create (auto-transitions to Succeeded)
    print("\n[->] Creating resource group 'qa-rg'...")
    resource_id, rg_config = handler.create_resource(
        "qa-rg",
        {"location": "eastus", "tags": {"env": "qa"}},
        "Microsoft.Resources/resourceGroups",
        {
            "subscription_id": "sub-qa-001",
            "user_id": "tester@company.com"
        }
    )
    
    state = rg_config.get('provisioning_state')
    print(f"[OK] State after create: {state}")
    assert state == 'Succeeded', "State should be Succeeded"
    
    # Delete (auto-transitions through states)
    print("\n[->] Deleting resource group...")
    deleted = handler.delete_resource(
        "qa-rg",
        {"subscription_id": "sub-qa-001"}
    )
    
    print(f"[OK] Delete completed: {deleted}")
    assert deleted, "Delete should succeed"
    
    # Verify it's gone
    result = handler.get_resource(
        "qa-rg",
        {"subscription_id": "sub-qa-001"}
    )
    print(f"[OK] After delete, get returns: {result}")
    assert result is None, "Should not find deleted RG"
    print("[OK] State transitions working!")
    
    return True


def test_4_multiple_subscriptions():
    """Test 4: Scope isolation - same RG name in different subscriptions"""
    print("\n" + "="*70)
    print("TEST 4: Subscription-Scoped Uniqueness")
    print("="*70)
    
    storage = {}
    handler = ResourceGroupHandler(storage)
    
    # Create same-named RG in different subscriptions
    print("\n[->] Creating 'shared-rg' in subscription 1...")
    resource_id_1, _ = handler.create_resource(
        "shared-rg",
        {"location": "eastus", "tags": {"sub": "1"}},
        "Microsoft.Resources/resourceGroups",
        {"subscription_id": "sub-001"}
    )
    print(f"[OK] Created: {resource_id_1}")
    
    print("\n[->] Creating 'shared-rg' in subscription 2...")
    resource_id_2, _ = handler.create_resource(
        "shared-rg",
        {"location": "westus", "tags": {"sub": "2"}},
        "Microsoft.Resources/resourceGroups",
        {"subscription_id": "sub-002"}
    )
    print(f"[OK] Created: {resource_id_2}")
    
    # Verify they're different
    assert resource_id_1 != resource_id_2, "IDs should be different"
    print("[OK] Same name allowed in different subscriptions!")
    
    # Verify duplication is blocked within same subscription
    print("\n[->] Attempting duplicate in subscription 1...")
    try:
        handler.create_resource(
            "shared-rg",
            {"location": "westus", "tags": {}},
            "Microsoft.Resources/resourceGroups",
            {"subscription_id": "sub-001"}
        )
        print("[ERROR] Should have blocked duplicate!")
        return False
    except ValueError as e:
        print(f"[OK] Correctly blocked: {str(e)}")
    
    return True


def test_5_convenience_methods():
    """Test 5: Convenience methods (create_from_properties, get_by_name, etc)"""
    print("\n" + "="*70)
    print("TEST 5: Convenience Methods with Big 3")
    print("="*70)
    
    storage = {}
    handler = ResourceGroupHandler(storage)
    
    # create_from_properties
    print("\n[->] Using create_from_properties...")
    result = handler.create_from_properties(
        "web-rg",
        {
            "location": "eastus",
            "tags": {"tier": "web"},
            "_subscription_id": "sub-web-001"
        },
        "sub-web-001"
    )
    
    print(f"[OK] Result:")
    print(f"    ID: {result['id']}")
    print(f"    State: {result['provisioning_state']}")
    assert result['provisioning_state'] == 'Succeeded'
    print("[OK] create_from_properties works with Big 3!")
    
    # get_by_name
    print("\n[->] Using get_by_name...")
    result = handler.get_by_name("web-rg", "sub-web-001")
    print(f"[OK] Retrieved: {result['name']} ({result['location']})")
    assert result['provisioning_state'] == 'Succeeded'
    
    # list_by_subscription
    print("\n[->] Using list_by_subscription...")
    handler.create_from_properties(
        "api-rg",
        {"location": "westus", "tags": {"tier": "api"}},
        "sub-web-001"
    )
    
    listing = handler.list_by_subscription("sub-web-001")
    print(f"[OK] Found {listing['count']} resource groups")
    assert listing['count'] == 2, "Should have 2 RGs"
    
    return True


if __name__ == "__main__":
    print("\n" + "#"*70)
    print("# ResourceGroupHandler - Big 3 Integration Test")
    print("#"*70)
    
    tests = [
        ("Creation & Validation", test_1_create_with_validation),
        ("Timestamps on Creation", test_2_timestamps_on_creation),
        ("State Management", test_3_state_transitions),
        ("Subscription Scoping", test_4_multiple_subscriptions),
        ("Convenience Methods", test_5_convenience_methods),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n[ERROR] Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results[name] = False
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for name, passed in results.items():
        status = "OK PASS" if passed else "ERROR FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(results.values())
    total = len(results)
    passed_count = sum(results.values())
    
    print(f"\nTotal: {passed_count}/{total} tests passed")
    
    if all_passed:
        print("\n[SUCCESS] ResourceGroupHandler with Big 3 is fully functional!")
    else:
        print("\n[FAILURE] Some tests failed")
        sys.exit(1)


