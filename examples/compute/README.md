# Compute Examples

Virtual machine and compute resource handlers.

## Files

### `big_3_examples.py` - VirtualMachineHandler
Demonstrates the Big 3 handler patterns with VM-specific validation:
- Validation: VM naming (3-63 chars), size validation (Standard_B1s, Standard_D2s_v3, etc.)
- Provisioning states: Creating → Succeeded → Deleting → Deleted
- Timestamps: createdTime, createdBy, modifiedTime, modifiedBy
- Scoping: Subscription + Resource Group (can reuse name in different RG)

**Key example:**
```python
class VirtualMachineHandler(ValidatedResourceHandler, ProvisioningStateHandler, 
                             TimestampedResourceHandler, ScopedResourceHandler):
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION, UniquenessScope.RESOURCE_GROUP]
    RESOURCE_TYPE = "virtualmachines"
    SCHEMA_CLASS = VirtualMachineSchema
```

**Run:** `python big_3_examples.py`

### `scoped_resource_examples.py` - VirtualMachineHandler
Demonstrates resource scoping patterns specific to VMs:
- RG-scoped uniqueness enforcement
- Multi-handler provider integration
- Real-world VM provisioning workflow

**Run:** `python scoped_resource_examples.py`

## Concepts

### Virtual Machine Scoping
- **Scope**: Subscription + Resource Group
- **Uniqueness**: Can have same name in different RGs within same subscription
- **Example**: `prod-rg/my-vm` and `dev-rg/my-vm` can coexist

### VM Handler Pattern
```python
handler = VirtualMachineHandler(storage)
resource_id, config = handler.create_resource(
    "web-server-01",
    {
        "vm_name": "web-server-01",
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
```

### VM Sizes (Validated)
- Standard_B1s, Standard_B1ms, Standard_B2s, Standard_B2ms
- Standard_D2s_v3, Standard_D4s_v3, Standard_D8s_v3
- Standard_E2s_v3, Standard_E4s_v3, Standard_E8s_v3

### VM Configuration Properties
- `vm_name`: 3-63 characters, alphanumeric + hyphens
- `size`: Predefined Azure VM sizes
- `os_type`: Windows or Linux
- `admin_username`: Optional
- `image_publisher`, `image_offer`, `image_sku`: Optional

## Use Cases

- Deploy web servers (web-server-01, web-server-02)
- Create development VMs (dev-vm-01, dev-vm-02)
- Scale compute resources with validation
- Track who provisioned which VMs and when
