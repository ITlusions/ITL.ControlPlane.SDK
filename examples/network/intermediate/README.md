# Network - Intermediate Level

Network Interface handler with the "Big 3" patterns: Validation, Provisioning States, and Timestamps.

## Files
- **`big_3_examples.py`** - NetworkInterfaceHandler implementation
  - Pydantic validation for NIC naming (3-80 characters)
  - Linked to virtual machines and subnets
  - IP configuration management
  - Provisioning state tracking
  - Automatic audit timestamps
  - RG-scoped uniqueness (like VMs)

**Run:** `python big_3_examples.py`

## Key Patterns

### NIC Validation
```python
class NetworkInterfaceSchema(BaseModel):
    nic_name: str = Field(..., description="NIC name")
    vm_id: str = Field(..., description="VM resource ID")
    subnet_id: str = Field(..., description="Subnet resource ID")
    private_ip: Optional[str] = None  # e.g., 10.0.1.10

@validator('nic_name')
def validate_name(cls, v):
    if len(v) < 3 or len(v) > 80:
        raise ValueError('NIC name must be 3-80 characters')
    return v
```

### NIC Scoping
```python
class NetworkInterfaceHandler(...):
    # Like VMs - unique within RG
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION, UniquenessScope.RESOURCE_GROUP]
```

## NIC Basics

A Network Interface Card is:
- Always attached to a VM
- Connected to a specific subnet
- Has IP configuration(s)
- Can have DNS settings and NSG rules

```python
handler.create_resource(
    "web-nic",
    {
        "nic_name": "web-nic",
        "vm_id": "/subscriptions/.../virtualMachines/web-server",
        "subnet_id": "/subscriptions/.../subnets/app-subnet",
        "private_ip": "10.0.1.10"  # Optional static IP
    },
    "Microsoft.Network/networkInterfaces",
    {
        "subscription_id": "sub",
        "resource_group": "app-rg"
    }
)
```

## Use Cases
- Primary NIC: `web-server-nic`
- Secondary NIC: `web-server-nic-secondary`
- Database NIC: `db-server-nic`
- Private endpoints: `api-endpoint-nic`

## Prerequisites
- Understand SDK basics (see [core/beginner/](../../core/beginner/))
- Understand VMs (see [compute/intermediate/](../../compute/intermediate/))

## Next Steps
→ **[Advanced](../advanced/)** - Learn NIC scoping and multi-NIC patterns
