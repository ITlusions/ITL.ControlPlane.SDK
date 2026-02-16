"""
Tests for resource groups seeding functionality.

Tests validate:
1. Missing subscriptions (dependency check)
2. Subscription name matching
3. Foreign key constraint handling
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import exc as sa_exc

from itl_controlplane_sdk.core.services.seed.resource_groups import (
    seed_default_resource_groups,
    DEFAULT_RESOURCE_GROUPS,
)
from itl_controlplane_sdk.core.services.seed.tenant import DEFAULT_TENANT_UUID


class MockAsyncSession:
    """Mock AsyncSession for testing without a real database."""
    
    def __init__(self):
        self.executed_queries = []
        self.execute_side_effect = None
        
    async def execute(self, query, params=None):
        """Mock execute method."""
        self.executed_queries.append({
            "query": query,
            "params": params
        })
        if self.execute_side_effect:
            return self.execute_side_effect(query, params)
        return MagicMock()
    
    async def commit(self):
        """Mock commit method."""
        pass


async def test_seed_resource_groups_no_subscriptions():
    """
    Test ISSUE #1: Should raise RuntimeError when no subscriptions exist.
    
    Validates that the function checks for subscription dependencies
    and fails with a clear error message when none are found.
    """
    session = MockAsyncSession()
    
    # Mock query result: no subscriptions returned
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    
    async def side_effect(query, params):
        if "subscriptions" in str(query):
            return mock_result
        return MagicMock()
    
    session.execute_side_effect = side_effect
    
    # Should raise RuntimeError due to missing subscriptions
    error_raised = False
    error_msg = ""
    try:
        await seed_default_resource_groups(session, DEFAULT_TENANT_UUID)
    except RuntimeError as e:
        error_raised = True
        error_msg = str(e)
    
    assert error_raised, "Should raise RuntimeError"
    # Verify error message mentions subscriptions
    assert "No subscriptions found" in error_msg or "subscriptions" in error_msg
    assert "seed_default_subscriptions" in error_msg
    print("✓ Test passed: RuntimeError raised for missing subscriptions")


async def test_seed_resource_groups_name_mismatch():
    """
    Test ISSUE #2: Should handle subscription names that don't match.
    
    Validates that the function identifies subscription names in the
    code that don't exist in the database.
    """
    session = MockAsyncSession()
    
    # Mock query result: return subscriptions with different names than expected
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        # Only return one subscription instead of all five
        ("itl-prod-westeurope", "subscription:tenant:itl-prod-westeurope", "uuid-prod"),
    ]
    
    async def side_effect(query, params):
        if "SELECT name, id, subscription_id" in str(query):
            return mock_result
        # For INSERT operations, return successful result
        return MagicMock()
    
    session.execute_side_effect = side_effect
    
    # Run seeding - should succeed but report missing subscriptions
    result = await seed_default_resource_groups(session, DEFAULT_TENANT_UUID)
    
    # Should have found the one subscription
    assert result["created"] >= 0
    # Should have reported missing subscriptions
    assert "missing_subscriptions" in result
    # Should list the missing subscriptions
    missing = result.get("missing_subscriptions", [])
    expected_missing = set(DEFAULT_RESOURCE_GROUPS.keys()) - {"itl-prod-westeurope"}
    for sub_name in expected_missing:
        assert sub_name in missing, f"Expected {sub_name} in missing_subscriptions"
    
    print(f"✓ Test passed: Name mismatch detected. Missing: {missing}")


async def test_seed_resource_groups_fk_constraint_violation():
    """
    Test ISSUE #3: Should handle foreign key constraint violations gracefully.
    
    Validates that the function catches IntegrityError and provides
    detailed error messages about the FK constraint failure.
    """
    session = MockAsyncSession()
    
    # Mock query result: return subscriptions
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        ("itl-prod-westeurope", "invalid-fk-ref", "uuid-prod"),
    ]
    
    insert_called = False
    
    async def side_effect(query, params):
        nonlocal insert_called
        
        if "SELECT name, id, subscription_id" in str(query):
            return mock_result
        elif "SELECT id FROM resource_groups" in str(query):
            # Resource group doesn't exist yet
            not_found = MagicMock()
            not_found.scalar.return_value = None
            return not_found
        elif "INSERT INTO resource_groups" in str(query):
            insert_called = True
            # Simulate foreign key constraint violation
            error = sa_exc.IntegrityError(
                "INSERT statement with invalid FK",
                None,
                None,
                orig=Exception("FOREIGN KEY constraint failed: subscription_id")
            )
            raise error
        return MagicMock()
    
    session.execute_side_effect = side_effect
    
    # Should raise RuntimeError with FK constraint details
    error_raised = False
    error_msg = ""
    try:
        await seed_default_resource_groups(session, DEFAULT_TENANT_UUID)
    except RuntimeError as e:
        error_raised = True
        error_msg = str(e)
    
    # Verify error message mentions FK constraint
    assert insert_called, "INSERT was not executed"
    assert error_raised, "Should raise RuntimeError for FK constraint"
    assert "FK constraint" in error_msg or "subscription_id" in error_msg
    print("✓ Test passed: FK constraint violation caught with details")


async def test_seed_resource_groups_success():
    """
    Test happy path: successful seeding when subscriptions exist.
    
    Validates that resource groups are created when:
    - Subscriptions exist with correct names
    - Database constraints are satisfied
    - No FK violations occur
    """
    session = MockAsyncSession()
    
    # Mock query results
    mock_subscriptions = MagicMock()
    mock_subscriptions.fetchall.return_value = [
        ("itl-prod-westeurope", "subscription:tenant:itl-prod", "uuid-prod"),
        ("itl-dev-westeurope", "subscription:tenant:itl-dev", "uuid-dev"),
        ("itl-staging-westeurope", "subscription:tenant:itl-staging", "uuid-staging"),
        ("itl-infra-global", "subscription:tenant:itl-infra", "uuid-infra"),
        ("itl-sandbox", "subscription:tenant:itl-sandbox", "uuid-sandbox"),
    ]
    
    async def side_effect(query, params):
        if "SELECT name, id, subscription_id" in str(query):
            return mock_subscriptions
        elif "SELECT id FROM resource_groups" in str(query):
            # All RGs don't exist yet
            not_found = MagicMock()
            not_found.scalar.return_value = None
            return not_found
        elif "INSERT INTO resource_groups" in str(query):
            # Successful insert
            return MagicMock()
        return MagicMock()
    
    session.execute_side_effect = side_effect
    
    # Run seeding
    result = await seed_default_resource_groups(session, DEFAULT_TENANT_UUID)
    
    # Calculate expected RGs
    expected_created = sum(len(rgs) for rgs in DEFAULT_RESOURCE_GROUPS.values())
    
    # Verify results
    assert result["created"] == expected_created, f"Expected {expected_created} created, got {result['created']}"
    assert result["skipped"] == 0
    assert "missing_subscriptions" not in result or result.get("missing_subscriptions") == []
    
    # Verify INSERT statements were executed
    insert_count = sum(
        1 for q in session.executed_queries 
        if "INSERT INTO resource_groups" in str(q.get("query", ""))
    )
    assert insert_count == expected_created, f"Expected {expected_created} INSERT statements, got {insert_count}"
    
    print(f"✓ Test passed: Successfully created {result['created']} resource groups")


async def test_seed_resource_groups_idempotent():
    """
    Test that seeding is idempotent - can be called multiple times safely.
    
    Validates that:
    - Already existing RGs are skipped
    - No duplicate creation attempts
    - Returns skipped count
    """
    session = MockAsyncSession()
    
    # Mock query results
    mock_subscriptions = MagicMock()
    mock_subscriptions.fetchall.return_value = [
        ("itl-prod-westeurope", "subscription:tenant:itl-prod", "uuid-prod"),
    ]
    
    async def side_effect(query, params):
        if "SELECT name, id, subscription_id" in str(query):
            return mock_subscriptions
        elif "SELECT id FROM resource_groups" in str(query):
            # All RGs already exist
            found = MagicMock()
            found.scalar.return_value = "existing-rg-id"
            return found
        return MagicMock()
    
    session.execute_side_effect = side_effect
    
    # Run seeding
    result = await seed_default_resource_groups(session, DEFAULT_TENANT_UUID)
    
    # Should skip existing RGs
    expected_rgs = len(DEFAULT_RESOURCE_GROUPS["itl-prod-westeurope"])
    assert result["created"] == 0, "Should not create new RGs"
    assert result["skipped"] == expected_rgs, f"Should skip {expected_rgs} existing RGs"
    
    # Verify no INSERT statements were executed
    insert_count = sum(
        1 for q in session.executed_queries 
        if "INSERT INTO resource_groups" in str(q.get("query", ""))
    )
    assert insert_count == 0, "Should not execute INSERT for existing RGs"
    
    print(f"✓ Test passed: Seeding is idempotent, skipped {result['skipped']} existing RGs")


if __name__ == "__main__":
    import asyncio
    
    print("\n" + "="*70)
    print("Testing Resource Groups Seeding - Issue Fixes")
    print("="*70)
    
    async def run_tests():
        print("\n[Test 1] No subscriptions found (Issue #1)")
        try:
            await test_seed_resource_groups_no_subscriptions()
        except AssertionError as e:
            print(f"✗ Test failed: {e}")
        
        print("\n[Test 2] Subscription name mismatch (Issue #2)")
        try:
            await test_seed_resource_groups_name_mismatch()
        except AssertionError as e:
            print(f"✗ Test failed: {e}")
        
        print("\n[Test 3] FK constraint violation (Issue #3)")
        try:
            await test_seed_resource_groups_fk_constraint_violation()
        except AssertionError as e:
            print(f"✗ Test failed: {e}")
        
        print("\n[Test 4] Happy path - successful seeding")
        try:
            await test_seed_resource_groups_success()
        except AssertionError as e:
            print(f"✗ Test failed: {e}")
        
        print("\n[Test 5] Idempotent seeding")
        try:
            await test_seed_resource_groups_idempotent()
        except AssertionError as e:
            print(f"✗ Test failed: {e}")
    
    asyncio.run(run_tests())
    print("\n" + "="*70)
    print("All tests completed!")
    print("="*70 + "\n")
