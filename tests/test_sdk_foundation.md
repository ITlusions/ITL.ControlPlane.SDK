# SDK Foundation Tests for Governance

## Purpose
Establish a **governance baseline** ensuring all SDK components follow core contracts and patterns.

---

## 1. **Provider Interface Compliance Tests**
**What:** Every ResourceProvider implementation must follow the ABC contract
**Why:** Prevents rogue providers that break the pipeline
**Tests:**
- [ ] All 3 abstract methods implemented (`_do_create_or_update_resource`, `_do_get_resource`, `_do_delete_resource`)
- [ ] Method signatures match ResourceProvider ABC exactly
- [ ] Methods are async (not sync)
- [ ] Proper lifecycle hooks called (on_creating, on_created, on_deleting, etc.)
- [ ] Exception types are SDK domain exceptions (not generic)
- [ ] Context parameter always respected (tenant_id isolation, request_id tracing)

**Location:** `tests/test_provider_contract.py`

---

## 2. **Model Validation Tests**
**What:** Pydantic models enforce data contracts
**Why:** Prevents invalid data flowing through the system
**Tests:**
- [ ] ResourceRequest: All required fields enforced
- [ ] ResourceRequest: resource_name has min/max length validation
- [ ] ResourceRequest: api_version matches pattern (YYYY-MM-DD)
- [ ] ResourceResponse: id, name, type are required
- [ ] ProviderContext: tenant_id and user_id cannot be empty
- [ ] ListResourceRequest: resource_name is optional (differs from ResourceRequest)
- [ ] Tags collection: Enforced key-value structure
- [ ] LocationCode: Valid Azure region identifiers only

**Location:** `tests/test_model_contracts.py`

---

## 3. **Exception Hierarchy Tests**
**What:** Proper exception types used throughout SDK
**Why:** Enables consistent error handling at API layer
**Tests:**
- [ ] ResourceNotFoundError: Used when resource doesn't exist
- [ ] InvalidSpecError: Used for validation failures
- [ ] ConflictError: Used for duplicate creation attempts
- [ ] ProviderError: Base for all provider operation failures
- [ ] Exception inheritance tree is correct (no orphans)
- [ ] Exception messages include actionable details
- [ ] Exceptions can be pickled (serializable for logging)

**Location:** `tests/test_exception_contracts.py`

---

## 4. **Resource ID Strategy Tests**
**What:** Consistent resource ID generation and parsing
**Why:** IDs are the unique identifier across the entire system
**Tests:**
- [ ] ID format is deterministic: `/subscriptions/{sub}/resourceGroups/{rg}/providers/{ns}/{type}/{name}`
- [ ] Same inputs produce same ID (idempotent)
- [ ] ID can be parsed back to components
- [ ] Special characters in names are escaped properly
- [ ] ID length has reasonable limits
- [ ] ID format matches ARM specification

**Location:** `tests/test_resource_id_strategy.py`

---

## 5. **Service Contract Tests**
**What:** Services follow async patterns and contract methods
**Why:** Ensures consistency across all service implementations
**Tests:**
- [ ] All service methods are async
- [ ] Idempotency: Calling twice with same spec produces same result
- [ ] Transaction handling: create/update/delete are atomic
- [ ] Tenant isolation: One tenant cannot see another's resources
- [ ] Request context propagation: request_id flows through entire operation
- [ ] Error handling: Failed operations don't leave partial state (rollback)

**Location:** `tests/test_service_contracts.py`

---

## 6. **Request/Response Contract Tests**
**What:** All API operations use standard request/response structures
**Why:** Enables generic request routing and response handling
**Tests:**
- [ ] Create operation returns ResourceResponse with id, name, properties
- [ ] Get operation returns same structure as Create
- [ ] List operation returns ResourceListResponse with value array
- [ ] Delete operation confirms deletion (returns deleted resource)
- [ ] All responses include provisioning_state
- [ ] All responses include resource_guid (globally unique)
- [ ] List operations support pagination (top/skip)
- [ ] List operations support filtering ($filter OData)

**Location:** `tests/test_request_response_contracts.py`

---

## 7. **Multi-Tenancy Tests**
**What:** Strict tenant isolation in all operations
**Why:** Critical for security and data isolation
**Tests:**
- [ ] Resource created in tenant A cannot be accessed by tenant B
- [ ] List operation only returns tenant's resources
- [ ] Delete operation only deletes tenant's resources
- [ ] tenant_id from context is enforced (not from request)
- [ ] Cross-tenant queries fail with 403 Forbidden
- [ ] Audit logs include tenant_id for all operations

**Location:** `tests/test_multi_tenancy_contracts.py`

---

## 8. **Async Lifecycle Tests**
**What:** Providers support async context manager pattern
**Why:** Ensures proper resource cleanup and initialization
**Tests:**
- [ ] Provider supports `async with provider:` syntax
- [ ] `__aenter__` calls `initialize()`
- [ ] `__aexit__` calls `cleanup()`
- [ ] Cleanup happens even if exception occurs
- [ ] Provider can be used without context manager (methods work standalone)
- [ ] Multiple initialization calls are safe (idempotent)

**Location:** `tests/test_async_lifecycle.py`

---

## 9. **Type Safety Tests**
**What:** All operations maintain type contracts
**Why:** Prevents runtime type errors
**Tests:**
- [ ] ResourceRequest validated with mypy (strict mode)
- [ ] ResourceResponse validated with mypy (strict mode)
- [ ] Provider methods have correct type hints
- [ ] No `Any` types used without justification
- [ ] Optional types properly handled (None checks)
- [ ] Generic types (List, Dict) have proper type parameters

**Location:** `tests/test_type_safety.py` + `mypy --strict`

---

## 10. **Provider Metadata Tests**
**What:** Providers correctly declare capabilities
**Why:** API knows what resources each provider supports
**Tests:**
- [ ] `provider_namespace` is set (e.g., "ITL.Core")
- [ ] `supported_resource_types` list is non-empty
- [ ] `get_provider_info()` returns metadata correctly
- [ ] `supports_resource_type()` matches supported list
- [ ] Metadata is immutable (no runtime changes)

**Location:** `tests/test_provider_metadata.py`

---

## Priority Order for Implementation

### **Tier 1 - Critical (Governance Foundation)**
1. Provider Interface Compliance (prevents bad providers)
2. Model Validation (enforces data contracts)
3. Exception Hierarchy (enables error handling)
4. Multi-Tenancy (security critical)

### **Tier 2 - Important (System Integrity)**
5. Resource ID Strategy (system-wide consistency)
6. Request/Response Contract (API consistency)
7. Service Contracts (operational consistency)

### **Tier 3 - Nice to Have (Quality)**
8. Async Lifecycle (resource management)
9. Type Safety (developer experience)
10. Provider Metadata (discoverability)

---

## Coverage Goals

| Category | Target | Rationale |
|----------|--------|-----------|
| Provider Methods | 100% coverage | Every provider must follow contract |
| Model Fields | 100% validation | Invalid data breaks the system |
| Exception Types | 100% usage | Enables consistent error handling |
| Resource IDs | 100% tested | IDs are the system-wide identifier |
| Multi-Tenancy | 100% isolation | Security requirement |
| Type Hints | 100% on public APIs | Prevents runtime errors |

---

## Example: Provider Compliance Test

```python
import pytest
import inspect
from abc import ABC, abstractmethod
from itl_controlplane_sdk.providers.base import ResourceProvider
from itl_controlplane_sdk.core import ResourceRequest, ProviderContext, ResourceResponse

@pytest.mark.asyncio
async def test_provider_implements_all_abstract_methods():
    """
    Every provider must implement all abstract methods from ResourceProvider ABC.
    This enforces the contract.
    """
    # Get all abstract methods from ResourceProvider
    abstract_methods = {
        name for name, method in inspect.getmembers(ResourceProvider, predicate=inspect.ismethod)
        if getattr(method, '__isabstractmethod__', False)
    }
    
    # Verify expected abstract methods exist
    expected = {
        '_do_create_or_update_resource',
        '_do_get_resource',
        '_do_delete_resource',
    }
    assert expected.issubset(abstract_methods), \
        f"Missing abstract methods: {expected - abstract_methods}"
    
    # Verify abstract methods are async
    for method_name in expected:
        method = getattr(ResourceProvider, method_name)
        assert inspect.iscoroutinefunction(method), \
            f"{method_name} must be async"

@pytest.mark.asyncio
async def test_provider_context_always_used():
    """Provider methods must accept and use ProviderContext."""
    methods = [
        ResourceProvider._do_create_or_update_resource,
        ResourceProvider._do_get_resource,
        ResourceProvider._do_delete_resource,
    ]
    
    for method in methods:
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        
        # Both request (ResourceRequest) and context (ProviderContext) required
        assert 'request' in params, f"{method.__name__} missing 'request' parameter"
        assert 'context' in params, f"{method.__name__} missing 'context' parameter"
        
        # Verify type hints
        context_param = sig.parameters['context']
        assert context_param.annotation == ProviderContext or \
               'ProviderContext' in str(context_param.annotation), \
               f"{method.__name__} context param must be typed as ProviderContext"

@pytest.mark.asyncio
async def test_provider_returns_correct_types():
    """Provider methods must return correct response types."""
    methods_to_test = [
        (ResourceProvider._do_create_or_update_resource, ResourceResponse),
        (ResourceProvider._do_get_resource, ResourceResponse),
    ]
    
    for method, expected_return_type in methods_to_test:
        sig = inspect.signature(method)
        return_annotation = sig.return_annotation
        
        # Check return type is ResourceResponse or wrapped in awaitable
        type_str = str(return_annotation)
        assert 'ResourceResponse' in type_str, \
            f"{method.__name__} must return ResourceResponse (got {return_annotation})"
```

---

## Example: Model Contract Test

```python
import pytest
from pydantic import ValidationError
from itl_controlplane_sdk.core import ResourceRequest, ListResourceRequest

def test_resource_request_requires_all_fields():
    """ResourceRequest requires subscription_id, resource_group, resource_name, etc."""
    
    # Missing resource_name should fail
    with pytest.raises(ValidationError) as exc_info:
        ResourceRequest(
            subscription_id="sub-123",
            resource_group="rg-test",
            provider_namespace="ITL.Core",
            resource_type="subscriptions",
            # Missing: resource_name
            location="eastus",
        )
    
    errors = exc_info.value.errors()
    assert any(e['loc'] == ('resource_name',) for e in errors)

def test_resource_request_enforces_constraints():
    """ResourceRequest enforces field constraints."""
    
    # Empty resource_name should fail (min_length=1)
    with pytest.raises(ValidationError):
        ResourceRequest(
            subscription_id="sub-123",
            resource_group="rg-test",
            provider_namespace="ITL.Core",
            resource_type="subscriptions",
            resource_name="",  # Empty string
            location="eastus",
        )
    
    # Too long should fail (max_length=260)
    with pytest.raises(ValidationError):
        ResourceRequest(
            subscription_id="sub-123",
            resource_group="rg-test",
            provider_namespace="ITL.Core",
            resource_type="subscriptions",
            resource_name="a" * 261,  # Too long
            location="eastus",
        )

def test_list_request_differs_from_resource_request():
    """ListResourceRequest is optional for resource_name, differs from ResourceRequest."""
    
    # This should succeed (resource_name not required for list)
    request = ListResourceRequest(
        subscription_id="sub-123",
        provider_namespace="ITL.Core",
        resource_type="subscriptions",
        # Note: resource_name is optional
    )
    
    assert request.resource_name is None or request.resource_name == ""
```

---

## Governance Benefits

These tests establish:

✓ **Consistency**: All providers follow same patterns
✓ **Security**: Multi-tenancy enforced at foundation
✓ **Reliability**: Type safety prevents runtime errors
✓ **Maintainability**: Clear contracts enable confident changes
✓ **Scalability**: New providers inherit governance automatically
✓ **Auditability**: All operations traceable via request_id

---

## Next Steps

1. Implement Tier 1 tests (critical foundation)
2. Add tests to CI/CD pipeline as gates
3. Document contracts in SDK README
4. Provide test templates for new providers
5. Generate SDK governance report quarterly
