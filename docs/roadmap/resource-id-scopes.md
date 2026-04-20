# Resource ID & Scope Fixes

**Status**: Open (Bugs + Features)  
**Version**: 1.0  
**Created**: 2026-04-20  
**Project**: SDK Resource ID Scope Fix  
**Issues**: [#7](https://github.com/ITlusions/ITL.ControlPlane.SDK/issues/7) · [#8](https://github.com/ITlusions/ITL.ControlPlane.SDK/issues/8) · [#9](https://github.com/ITlusions/ITL.ControlPlane.SDK/issues/9) · [#10](https://github.com/ITlusions/ITL.ControlPlane.SDK/issues/10)

---

## Overview

Four related issues in `src/itl_sdk/resource/uniqueness.py` and `build_resource_id()` / `build_storage_key()`. Two are bugs in existing scope behaviour, two add new scopes required for subscription-level and nested resource types.

**Affected file**: `src/itl_sdk/resource/uniqueness.py`

---

## Current Scope Enum

```python
class UniquenessScope(Enum):
    TENANT = "tenant"
    MANAGEMENT_GROUP = "management_group"
    SUBSCRIPTION = "subscription"         # ← BUG: generates wrong path (#8)
    RESOURCE_GROUP_CONTAINER = "resource_group_container"
    RESOURCE_GROUP = "resource_group"
    EXTENSION = "extension"
    # Missing: SUBSCRIPTION_ONLY (#7), PARENT_RESOURCE (#9)
```

## Target Scope Enum (after all fixes)

```python
class UniquenessScope(Enum):
    TENANT = "tenant"
    MANAGEMENT_GROUP = "management_group"
    SUBSCRIPTION = "subscription"
    SUBSCRIPTION_ONLY = "subscription_only"   # NEW (#7)
    RESOURCE_GROUP_CONTAINER = "resource_group_container"
    RESOURCE_GROUP = "resource_group"
    PARENT_RESOURCE = "parent_resource"        # NEW (#9)
    EXTENSION = "extension"
```

---

## CP-SDK-008: Fix SUBSCRIPTION Scope Path Bug — `#8`

**Type**: Bug · **Priority**: High

### Problem

`build_resource_id()` with `SUBSCRIPTION` scope incorrectly inserts `/resourceGroups/None/` in the path:

```
# Current (WRONG):
/subscriptions/a1b2-.../resourceGroups/None/providers/Microsoft.Authorization/policyAssignments/my-policy

# Expected (CORRECT):
/subscriptions/a1b2-.../providers/Microsoft.Authorization/policyAssignments/my-policy
```

### Root Cause

`SUBSCRIPTION` scope uses the resource group template branch when it should use a subscription-level path (no `/resourceGroups/` segment).

### Fix

```python
case UniquenessScope.SUBSCRIPTION | UniquenessScope.SUBSCRIPTION_ONLY:
    # No resourceGroups segment for subscription-level resources
    return f"/subscriptions/{subscription_id}/providers/{namespace}/{resource_type}/{resource_name}"
```

### Acceptance Criteria

- [ ] `SUBSCRIPTION` scope generates path without `/resourceGroups/` segment
- [ ] Resulting path: `/subscriptions/{sub}/providers/{ns}/{type}/{name}`
- [ ] `RESOURCE_GROUP` scope unchanged (still requires `resource_group` parameter)
- [ ] Regression test added
- [ ] Existing tests pass

---

## CP-SDK-007: Add SUBSCRIPTION_ONLY Scope — `#7`

**Type**: Feature · **Priority**: High

### Problem

Subscription-level resources (role assignments, policy assignments) that are unique per subscription but not per resource group need their own scope. `SUBSCRIPTION` currently conflates resource-group-scoped and subscription-scoped resources.

### New Scope

```python
SUBSCRIPTION_ONLY = "subscription_only"
```

**ARM path format**:
```
/subscriptions/{subscription_id}/providers/{namespace}/{resource_type}/{resource_name}
```

**Example**:
```
/subscriptions/a1b2c3d4-e5f6-7890-abcd-ef1234567890/providers/Microsoft.Authorization/policyAssignments/itl-foundation-v1
```

**Storage key format** (see also #10):
```
sub:{subscription_id}/{resource_type}/{resource_name}
```

### Acceptance Criteria

- [ ] `SUBSCRIPTION_ONLY` added to `UniquenessScope` enum
- [ ] `build_resource_id()` produces correct subscription-level path for `SUBSCRIPTION_ONLY`
- [ ] Storage key uses `sub:{sub}/` prefix (no resource group segment)
- [ ] Existing `SUBSCRIPTION` scope behaviour unchanged
- [ ] Unit tests for ID generation with `SUBSCRIPTION_ONLY`

---

## CP-SDK-009: Add PARENT_RESOURCE Scope — `#9`

**Type**: Feature · **Priority**: Medium

### Problem

Nested resources (blob container under storage account, database under SQL server) require the parent's full ARM ID in their path. No current scope handles this pattern.

### New Scope

```python
PARENT_RESOURCE = "parent_resource"
```

**ARM path format**:
```
/subscriptions/{sub}/resourceGroups/{rg}/providers/{ns}/{parent_type}/{parent_name}/{child_type}/{child_name}
```

**Example**:
```
/subscriptions/a1b2.../resourceGroups/rg-storage/providers/Microsoft.Storage/storageAccounts/stitlplatform/blobServices/default
```

### `build_resource_id()` extension

```python
case UniquenessScope.PARENT_RESOURCE:
    if not parent_resource_id:
        raise ValueError("parent_resource_id required for PARENT_RESOURCE scope")
    return f"{parent_resource_id}/{resource_type}/{resource_name}"
```

### Acceptance Criteria

- [ ] `PARENT_RESOURCE` added to enum
- [ ] `build_resource_id()` accepts `parent_resource_id` parameter
- [ ] Generated path is a correctly nested ARM path
- [ ] `ValueError` raised when `parent_resource_id` is missing
- [ ] Unit test: blob container under storage account

---

## CP-SDK-010: Fix Storage Key Generation — `#10`

**Type**: Bug · **Priority**: High

### Problem

Storage key for `SUBSCRIPTION_ONLY` scope incorrectly includes resource group segment, causing key conflicts between resources in different subscriptions.

```python
# Current (WRONG):
"subscription/providers/Microsoft.Authorization/policyAssignments/my-policy"

# Expected:
"sub:a1b2c3d4.../policyAssignments/my-policy"
```

### Target Storage Key Format

| Scope | Key format |
|-------|-----------|
| `TENANT` | `tenant/{ns}/{type}/{name}` |
| `MANAGEMENT_GROUP` | `mg:{mg_id}/{type}/{name}` |
| `SUBSCRIPTION` | `sub:{sub_id}/{rg}/{type}/{name}` |
| `SUBSCRIPTION_ONLY` | `sub:{sub_id}/{type}/{name}` ← no resource group |
| `RESOURCE_GROUP` | `rg:{sub_id}/{rg}/{type}/{name}` |
| `PARENT_RESOURCE` | `parent:{parent_hash_12}/{type}/{name}` |

### `build_storage_key()` fix (SUBSCRIPTION_ONLY case)

```python
case UniquenessScope.SUBSCRIPTION_ONLY:
    return f"sub:{subscription_id}/{resource_type}/{resource_name}"

case UniquenessScope.PARENT_RESOURCE:
    import hashlib
    parent_hash = hashlib.sha256(parent_resource_id.encode()).hexdigest()[:12]
    return f"parent:{parent_hash}/{resource_type}/{resource_name}"
```

### Acceptance Criteria

- [ ] `SUBSCRIPTION_ONLY` key contains no resource group segment
- [ ] `SUBSCRIPTION_ONLY` key contains no `None` string
- [ ] `SUBSCRIPTION` and `SUBSCRIPTION_ONLY` generate different keys for the same resource
- [ ] All scope variants generate unique keys (no conflicts)
- [ ] Tests pass for all scope combinations

---

## Implementation Order

These 4 issues are tightly coupled — fix/add in this order:

```
#8  Fix SUBSCRIPTION scope path bug           ← unblocks rest
#7  Add SUBSCRIPTION_ONLY scope               ← depends on #8 fix
#10 Fix storage key generation                ← depends on #7
#9  Add PARENT_RESOURCE scope                 ← independent, can be parallel
```

---

## Test Coverage Targets

```python
class TestBuildResourceId:
    def test_subscription_scope_no_resource_group_segment(self): ...
    def test_subscription_only_scope_path(self): ...
    def test_parent_resource_scope_nested_path(self): ...
    def test_parent_resource_missing_parent_raises(self): ...

class TestBuildStorageKey:
    def test_subscription_only_no_resource_group(self): ...
    def test_subscription_only_no_none_string(self): ...
    def test_subscription_vs_subscription_only_different_keys(self): ...
    def test_parent_resource_key_format(self): ...
    def test_all_scopes_generate_unique_keys(self): ...
```

---

## Architecture Recommendation: Pluggable ID Strategy

While fixing #7–#10, the root cause is that `_generate_resource_id()` has the format logic hardcoded in one method with a growing if/match block. Every new scope forces a change to the same function. The recommended fix is to extract the format logic into a **strategy pattern**, making scope additions and format changes independent of handler logic.

### Proposed: `ResourceIdStrategy`

```python
# src/itl_controlplane_sdk/providers/utilities/resource_id_strategy.py

from abc import ABC, abstractmethod
from typing import Optional

class ResourceIdStrategy(ABC):
    @abstractmethod
    def generate(self, context: dict) -> str: ...

    @abstractmethod
    def parse(self, resource_id: str) -> dict: ...


class ArmResourceIdStrategy(ResourceIdStrategy):
    """
    Default strategy — ARM-style hierarchical path.

    Produces:
      RG-scoped:    /subscriptions/{sub}/resourceGroups/{rg}/providers/{ns}/{type}/{name}
      Sub-level:    /subscriptions/{sub}/providers/{ns}/{type}/{name}
      MG-level:     /providers/ITL.Management/managementGroups/{mg}/providers/{ns}/{type}/{name}
      Global:       /providers/{ns}/{type}/{name}
      Parent-child: {parent_resource_id}/{type}/{name}
    """
    def generate(self, context: dict) -> str:
        sub = context.get("subscription_id", "unknown")
        rg = context.get("resource_group")
        mg = context.get("management_group_id")
        parent = context.get("parent_resource_id")
        ns = context.get("provider_namespace", "unknown")
        resource_type = context.get("resource_type", "unknown")
        name = context.get("resource_name", "unknown")

        if parent:
            return f"{parent}/{resource_type}/{name}"
        if mg:
            return f"/providers/ITL.Management/managementGroups/{mg}/providers/{ns}/{resource_type}/{name}"
        if sub and rg:
            return f"/subscriptions/{sub}/resourceGroups/{rg}/providers/{ns}/{resource_type}/{name}"
        if sub:
            return f"/subscriptions/{sub}/providers/{ns}/{resource_type}/{name}"
        return f"/providers/{ns}/{resource_type}/{name}"

    def parse(self, resource_id: str) -> dict:
        from itl_controlplane_sdk.providers.utilities.resource_ids import parse_resource_id
        return parse_resource_id(resource_id)
```

### Integration into `ScopedResourceHandler`

```python
class ScopedResourceHandler:
    UNIQUENESS_SCOPE: List[UniquenessScope] = [UniquenessScope.GLOBAL]
    RESOURCE_TYPE: str = "unknown"
    ID_STRATEGY: ResourceIdStrategy = ArmResourceIdStrategy()   # ← pluggable per handler

    def _generate_resource_id(self, name: str, resource_type: str, scope_context: dict) -> str:
        return self.ID_STRATEGY.generate({
            **scope_context,
            "resource_type": resource_type,
            "resource_name": name,
        })
```

Each handler can override `ID_STRATEGY` independently without touching shared logic:

```python
class VirtualMachineHandler(ScopedResourceHandler):
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION, UniquenessScope.RESOURCE_GROUP]
    RESOURCE_TYPE = "virtualMachines"
    ID_STRATEGY = ArmResourceIdStrategy()   # explicit, or just inherit default
```

### `azure_id` alias on `ResourceResponse`

For providers that proxy real Azure resources, add an optional alias field to `ResourceResponse`:

```python
class ResourceResponse(CoreBaseModel):
    id: str                                 # ITL ARM path (primary, always present)
    resource_guid: Optional[str]            # UUID4 (stable across renames)
    azure_id: Optional[str] = None          # Real Azure ARM ID (only when proxying Azure)
    ...
```

Providers set it when creating the backing Azure resource:

```python
return ResourceResponse(
    id=itl_resource_id,
    azure_id=f"/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Compute/virtualMachines/{name}",
    ...
)
```

### Deprecation: `?guid=` suffix in `generate_resource_id()`

The `include_guid=True` option in `generate_resource_id()` appends a query string (`?guid={uuid}`) to the ARM path. This is non-standard, breaks URL parsers and Azure SDK clients, and is already superseded by `resource_guid` on `ResourceResponse` and `ResourceMetadata`.

**Action**: Remove `include_guid` parameter and the `?guid=` branch from `generate_resource_id()`. The `resource_guid` field is the correct mechanism.

### Recommended Delivery Order

```
1. Add ResourceIdStrategy ABC + ArmResourceIdStrategy    ← no behaviour change, pure refactor
2. Wire strategy into ScopedResourceHandler              ← replaces hardcoded if-block
3. Fix #8 SUBSCRIPTION path bug inside ArmResourceIdStrategy
4. Add SUBSCRIPTION_ONLY (#7) and PARENT_RESOURCE (#9) scopes
5. Fix storage key generation (#10)
6. Add azure_id to ResourceResponse + ResourceMetadata
7. Remove include_guid / ?guid= from generate_resource_id()
```
