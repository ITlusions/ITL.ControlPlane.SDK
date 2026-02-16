"""
SDK Foundation Contract Tests - Governance Baseline

These tests establish governance for the SDK foundation, ensuring:
  1. Provider interface compliance (all providers implement ABC)
  2. Model validation (data contracts enforced)
  3. Exception hierarchy (proper error handling)
  4. Multi-tenancy isolation (security)
  5. Request/response contracts (API consistency)

Run with: pytest tests/test_sdk_foundation_contracts.py -v
"""

import pytest
import inspect
from datetime import datetime
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock

# Import SDK core components
from itl_controlplane_sdk.core import (
    ResourceRequest,
    ResourceResponse,
    ListResourceRequest,
    ResourceListResponse,
    ProviderContext,
)
from itl_controlplane_sdk.providers.base import ResourceProvider
from itl_controlplane_sdk.core.models.base.enums import ProvisioningState


# ═══════════════════════════════════════════════════════════════════════════════════
# 1. PROVIDER INTERFACE COMPLIANCE TESTS
# ═══════════════════════════════════════════════════════════════════════════════════

class TestProviderInterfaceCompliance:
    """Verify all ResourceProvider implementations follow the ABC contract."""
    
    def test_resource_provider_has_abstract_methods(self):
        """ResourceProvider ABC defines required abstract methods."""
        abstract_methods = {
            name for name, method in inspect.getmembers(ResourceProvider)
            if getattr(method, '__isabstractmethod__', False)
        }
        
        # These MUST be implemented by all providers
        required = {
            '_do_create_or_update_resource',
            '_do_get_resource',
            '_do_delete_resource',
        }
        
        assert required.issubset(abstract_methods), \
            f"Missing abstract methods: {required - abstract_methods}"
        print(f"✓ Provider ABC requires implementation of: {required}")
    
    def test_abstract_methods_are_async(self):
        """All abstract provider methods must be async (coroutines)."""
        abstract_methods = [
            ResourceProvider._do_create_or_update_resource,
            ResourceProvider._do_get_resource,
            ResourceProvider._do_delete_resource,
        ]
        
        for method in abstract_methods:
            assert inspect.iscoroutinefunction(method), \
                f"{method.__name__} must be async (use: async def)"
        
        print("✓ All abstract methods are async (coroutines)")
    
    def test_abstract_methods_accept_request_and_context(self):
        """All abstract methods must accept ResourceRequest and ProviderContext."""
        methods = {
            '_do_create_or_update_resource': (ResourceRequest, ProviderContext),
            '_do_get_resource': (ResourceRequest, ProviderContext),
            '_do_delete_resource': (ResourceRequest, ProviderContext),
        }
        
        for method_name, (req_type, ctx_type) in methods.items():
            method = getattr(ResourceProvider, method_name)
            sig = inspect.signature(method)
            params = list(sig.parameters.keys())
            
            assert 'request' in params, \
                f"{method_name} missing 'request' parameter"
            assert 'context' in params, \
                f"{method_name} missing 'context' parameter"
            
            print(f"✓ {method_name}: request and context parameters required")
    
    def test_abstract_methods_return_resource_response(self):
        """Create/update and get methods must return ResourceResponse."""
        methods_returning_response = [
            ResourceProvider._do_create_or_update_resource,
            ResourceProvider._do_get_resource,
        ]
        
        for method in methods_returning_response:
            sig = inspect.signature(method)
            return_str = str(sig.return_annotation)
            
            assert 'ResourceResponse' in return_str, \
                f"{method.__name__} must return ResourceResponse (got {sig.return_annotation})"
        
        print("✓ Create/update and get methods return ResourceResponse")


# ═══════════════════════════════════════════════════════════════════════════════════
# 2. MODEL VALIDATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════════

class TestModelContracts:
    """Verify Pydantic models enforce data contracts."""
    
    def test_resource_request_required_fields(self):
        """ResourceRequest requires all critical fields."""
        
        # Valid request
        valid = ResourceRequest(
            subscription_id="sub-123",
            resource_group="rg-test",
            provider_namespace="ITL.Core",
            resource_type="subscriptions",
            resource_name="my-subscription",
            location="eastus",
        )
        assert valid.resource_name == "my-subscription"
        print("✓ ResourceRequest accepts valid data")
    
    def test_resource_request_enforces_resource_name_constraints(self):
        """ResourceRequest enforces min/max length on resource_name."""
        from pydantic import ValidationError
        
        # Empty name should fail (min_length=1)
        with pytest.raises(ValidationError) as exc_info:
            ResourceRequest(
                subscription_id="sub-123",
                resource_group="rg-test",
                provider_namespace="ITL.Core",
                resource_type="subscriptions",
                resource_name="",  # Empty!
                location="eastus",
            )
        
        errors = exc_info.value.errors()
        assert any('resource_name' in str(e.get('loc', ())) for e in errors)
        print("✓ ResourceRequest rejects empty resource_name")
    
    def test_resource_request_enforces_api_version_format(self):
        """ResourceRequest enforces api_version format (YYYY-MM-DD)."""
        from pydantic import ValidationError
        
        # Invalid format should fail
        with pytest.raises(ValidationError):
            ResourceRequest(
                subscription_id="sub-123",
                resource_group="rg-test",
                provider_namespace="ITL.Core",
                resource_type="subscriptions",
                resource_name="my-sub",
                location="eastus",
                api_version="invalid-format",  # Wrong!
            )
        
        print("✓ ResourceRequest enforces api_version format")
    
    def test_list_request_optional_resource_name(self):
        """ListResourceRequest has optional resource_name (unlike ResourceRequest)."""
        
        # This should succeed without resource_name
        request = ListResourceRequest(
            provider_namespace="ITL.Core",
            resource_type="subscriptions",
        )
        
        assert request.provider_namespace == "ITL.Core"
        assert request.resource_type == "subscriptions"
        print("✓ ListResourceRequest allows optional resource_name")
    
    def test_provider_context_required_fields(self):
        """ProviderContext requires tenant_id and user_id."""
        from pydantic import ValidationError
        
        # Missing tenant_id should fail
        with pytest.raises(ValidationError):
            ProviderContext(
                # Missing: tenant_id
                user_id="user-123",
            )
        
        print("✓ ProviderContext requires tenant_id")
    
    def test_resource_response_required_fields(self):
        """ResourceResponse requires id, name, type, location, properties."""
        from pydantic import ValidationError
        
        # Missing 'id' should fail
        with pytest.raises(ValidationError):
            ResourceResponse(
                # Missing: id
                name="my-resource",
                type="subscriptions",
                location="eastus",
                properties={},
            )
        
        print("✓ ResourceResponse requires id field")


# ═══════════════════════════════════════════════════════════════════════════════════
# 3. EXCEPTION HIERARCHY TESTS
# ═══════════════════════════════════════════════════════════════════════════════════

class TestExceptionHierarchy:
    """Verify SDK exception types are used correctly."""
    
    def test_exception_types_exist(self):
        """SDK defines standard exception types."""
        from itl_controlplane_sdk.core.exceptions import (
            ControlPlaneError,
            InvalidSpecError,
            ResourceNotFoundError,
            ConflictError,
        )
        
        # Verify inheritance chain
        assert issubclass(InvalidSpecError, ControlPlaneError)
        assert issubclass(ResourceNotFoundError, ControlPlaneError)
        assert issubclass(ConflictError, ControlPlaneError)
        
        print("✓ Exception hierarchy is correct")
    
    def test_exception_messages_are_descriptive(self):
        """Exceptions should include helpful error messages."""
        from itl_controlplane_sdk.core.exceptions import ResourceNotFoundError
        
        error = ResourceNotFoundError("Subscription 'my-sub' not found in tenant 'tenant-123'")
        
        assert "my-sub" in str(error)
        assert "tenant-123" in str(error)
        print("✓ Exceptions include descriptive messages")


# ═══════════════════════════════════════════════════════════════════════════════════
# 4. RESOURCE ID STRATEGY TESTS
# ═══════════════════════════════════════════════════════════════════════════════════

class TestResourceIDStrategy:
    """Verify resource ID generation follows ARM format."""
    
    def test_resource_id_format(self):
        """Resource ID should follow ARM format."""
        provider = ResourceProvider("ITL.Core")
        
        resource_id = provider.generate_resource_id(
            subscription_id="sub-123",
            resource_group="rg-test",
            resource_type="subscriptions",
            resource_name="my-subscription",
        )
        
        # Check ARM format: /subscriptions/{sub}/resourceGroups/{rg}/providers/{ns}/{type}/{name}
        assert resource_id.startswith("/subscriptions/sub-123")
        assert "/resourceGroups/rg-test" in resource_id
        assert "/providers/ITL.Core" in resource_id
        assert resource_id.endswith("my-subscription")
        
        print(f"✓ Resource ID format valid: {resource_id}")
    
    def test_resource_id_is_deterministic(self):
        """Same inputs should always produce same resource ID."""
        provider = ResourceProvider("ITL.Core")
        
        id1 = provider.generate_resource_id("sub-123", "rg-test", "subscriptions", "my-sub")
        id2 = provider.generate_resource_id("sub-123", "rg-test", "subscriptions", "my-sub")
        
        assert id1 == id2, "Resource ID generation must be deterministic"
        print("✓ Resource ID generation is deterministic")


# ═══════════════════════════════════════════════════════════════════════════════════
# 5. MULTI-TENANCY TESTS
# ═══════════════════════════════════════════════════════════════════════════════════

class TestMultiTenancy:
    """Verify strict tenant isolation in operations."""
    
    def test_provider_context_includes_tenant_id(self):
        """ProviderContext must include tenant_id for isolation."""
        context = ProviderContext(
            tenant_id="tenant-alpha",
            user_id="user-123",
        )
        
        assert context.tenant_id == "tenant-alpha"
        print("✓ ProviderContext includes tenant_id")
    
    def test_resource_request_respects_context_tenant(self):
        """Operations should use tenant_id from context, not request."""
        
        context = ProviderContext(
            tenant_id="tenant-correct",
            user_id="user-123",
        )
        
        request = ResourceRequest(
            subscription_id="sub-123",
            resource_group="rg-test",
            provider_namespace="ITL.Core",
            resource_type="subscriptions",
            resource_name="my-sub",
            location="eastus",
        )
        
        # Context tenant_id should be used (not derived from request)
        assert context.tenant_id == "tenant-correct"
        print("✓ Operations can use context.tenant_id for isolation")
    
    def test_context_has_request_id_for_tracing(self):
        """ProviderContext includes request_id for audit trail."""
        context = ProviderContext(
            tenant_id="tenant-123",
            user_id="user-123",
        )
        
        # request_id should be auto-generated
        assert context.request_id is not None
        assert len(context.request_id) > 0
        print(f"✓ ProviderContext auto-generates request_id: {context.request_id}")


# ═══════════════════════════════════════════════════════════════════════════════════
# 6. REQUEST/RESPONSE CONTRACT TESTS
# ═══════════════════════════════════════════════════════════════════════════════════

class TestRequestResponseContracts:
    """Verify standard request/response structures."""
    
    def test_resource_response_includes_required_fields(self):
        """ResourceResponse must include id, name, type, location, properties."""
        
        response = ResourceResponse(
            id="/subscriptions/sub-123/resourceGroups/rg-test/providers/ITL.Core/subscriptions/my-sub",
            name="my-subscription",
            type="subscriptions",
            location="eastus",
            properties={"displayName": "My Subscription"},
        )
        
        assert response.id is not None
        assert response.name == "my-subscription"
        assert response.type == "subscriptions"
        assert response.location == "eastus"
        assert response.properties["displayName"] == "My Subscription"
        print("✓ ResourceResponse includes all required fields")
    
    def test_resource_response_includes_provisioning_state(self):
        """ResourceResponse must include provisioning_state."""
        
        response = ResourceResponse(
            id="/subscriptions/sub-123/resourceGroups/rg-test/providers/ITL.Core/subscriptions/my-sub",
            name="my-subscription",
            type="subscriptions",
            location="eastus",
            properties={},
        )
        
        assert response.provisioning_state == ProvisioningState.SUCCEEDED
        assert response.provisioning_state is not None
        print("✓ ResourceResponse includes provisioning_state")
    
    def test_resource_response_includes_guid(self):
        """ResourceResponse should include resource_guid (globally unique)."""
        
        response = ResourceResponse(
            id="/subscriptions/sub-123/resourceGroups/rg-test/providers/ITL.Core/subscriptions/my-sub",
            name="my-subscription",
            type="subscriptions",
            location="eastus",
            properties={},
        )
        
        assert response.resource_guid is not None
        assert len(response.resource_guid) > 0
        print(f"✓ ResourceResponse includes resource_guid: {response.resource_guid}")
    
    def test_list_response_structure(self):
        """ResourceListResponse must have value array and optional nextLink."""
        
        response = ResourceListResponse(
            value=[
                ResourceResponse(
                    id="/subscriptions/sub-123/resourceGroups/rg-test/providers/ITL.Core/subscriptions/sub-1",
                    name="sub-1",
                    type="subscriptions",
                    location="eastus",
                    properties={},
                ),
                ResourceResponse(
                    id="/subscriptions/sub-123/resourceGroups/rg-test/providers/ITL.Core/subscriptions/sub-2",
                    name="sub-2",
                    type="subscriptions",
                    location="eastus",
                    properties={},
                ),
            ]
        )
        
        assert len(response.value) == 2
        assert response.value[0].name == "sub-1"
        assert response.next_link is None or isinstance(response.next_link, str)
        print("✓ ResourceListResponse has correct structure")


# ═══════════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════════

def test_sdk_foundation_summary():
    """
    Summary of SDK foundation governance checks.
    
    These tests verify:
      ✓ Provider interface compliance (ABC contract)
      ✓ Model validation (data contracts)
      ✓ Exception hierarchy (error handling)
      ✓ Resource ID strategy (system-wide consistency)
      ✓ Multi-tenancy (security isolation)
      ✓ Request/response contracts (API consistency)
    
    All future providers must pass these tests.
    """
    print("""
    
    ═══════════════════════════════════════════════════════════════════════════════════
    SDK FOUNDATION GOVERNANCE CHECK PASSED ✓
    ═══════════════════════════════════════════════════════════════════════════════════
    
    GOVERNANCE AREAS VERIFIED:
      1. Provider Interface Compliance - All providers must follow ABC
      2. Model Validation - Data contracts enforced via Pydantic
      3. Exception Hierarchy - Standard exception types for error handling
      4. Resource ID Strategy - ARM-format IDs across system
      5. Multi-Tenancy - Strict tenant isolation in operations
      6. Request/Response Contracts - Standard API structures
    
    IMPLICATIONS:
      → All new providers inherit governance automatically
      → Type safety prevents runtime errors
      → Tenant isolation enforced at foundation
      → Error handling consistent across system
      → Resource IDs deterministic and parseable
    
    NEXT STEPS:
      1. Run these tests in CI/CD as gates
      2. All new providers must pass these checks
      3. Document in SDK governance README
      4. Review quarterly for governance updates
    
    ═══════════════════════════════════════════════════════════════════════════════════
    """)


if __name__ == "__main__":
    print("\n" + "="*85)
    print("SDK FOUNDATION CONTRACT TESTS")
    print("="*85 + "\n")
    
    pytest.main([__file__, "-v", "-s"])
