# Compute - Intermediate Level

Virtual Machine handler with the "Big 3" patterns: Validation, Provisioning States, and Timestamps.

## Files
- **`big_3_examples.py`** - VirtualMachineHandler implementation
  - Pydantic validation for VM names, sizes, OS types
  - Provisioning state management (Creating → Succeeded → Deleting → Deleted)
  - Automatic audit timestamps (createdTime, createdBy, etc.)
  - RG-scoped uniqueness (can reuse names in different RGs)

**Run:** `python big_3_examples.py`

## Key Patterns

### VM Validation
```python
@validator('vm_name')
def validate_vm_name(cls, v):
    """VM names: 3-63 chars, alphanumeric + hyphen"""
    if len(v) < 3 or len(v) > 63:
        raise ValueError('VM name must be 3-63 characters')
    return v

@validator('size')
def validate_size(cls, v):
    """Only allow known Azure sizes"""
    valid_sizes = {
        'Standard_B1s', 'Standard_B2s', 'Standard_D2s_v3', ...
    }
    if v not in valid_sizes:
        raise ValueError(f'Invalid VM size')
    return v
```

### VM Scoping
```python
class VirtualMachineHandler(ValidatedResourceHandler, ProvisioningStateHandler,
                             TimestampedResourceHandler, ScopedResourceHandler):
    # Unique within RG, can reuse name in different RGs
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION, UniquenessScope.RESOURCE_GROUP]
```

## Use Cases
- Deploy web servers: `web-server-01`, `web-server-02`
- Development VMs: `dev-vm`, `test-vm`
- Database servers: `db-server-prod`, `db-server-dev`

## Prerequisites
- Understand SDK basics (see [core/beginner/](../../core/beginner/))

## Next Steps
→ **[Advanced](../advanced/)** - Learn resource scoping patterns
