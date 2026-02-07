# Network Examples

Network interface and networking resource handlers.

## Files

### `big_3_examples.py` - NetworkInterfaceHandler
Demonstrates the Big 3 handler patterns with network interface validation:
- Validation: NIC naming (3-80 characters)
- Linked to virtual machines and subnets
- Provisioning state management
- Timestamps for audit trail
- RG-scoped uniqueness

**Key example:**
```python
class NetworkInterfaceSchema(BaseModel):
    nic_name: str = Field(..., description="NIC name")
    vm_id: str = Field(..., description="VM resource ID")
    subnet_id: str = Field(..., description="Subnet resource ID")
    private_ip: Optional[str] = None

class NetworkInterfaceHandler(ValidatedResourceHandler, ProvisioningStateHandler,
                               TimestampedResourceHandler, ScopedResourceHandler):
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION, UniquenessScope.RESOURCE_GROUP]
    RESOURCE_TYPE = "networkinterfaces"
    SCHEMA_CLASS = NetworkInterfaceSchema
```

**Run:** `python big_3_examples.py`

### `scoped_resource_examples.py` - NetworkInterfaceHandler
Demonstrates RG-scoped networking resources:
- Network interface RG scoping
- Multi-handler provider integration
- Linked resource patterns (NICs attached to VMs)

**Run:** `python scoped_resource_examples.py`

## Concepts

### Network Interface Scoping
- **Scope**: Subscription + Resource Group
- **Uniqueness**: Can have same name in different RGs
- **Example**: `prod-rg/web-nic` and `dev-rg/web-nic` can coexist
- **Parent**: Always associated with a VM and subnet

### NIC Handler Pattern
```python
handler = NetworkInterfaceHandler(storage)
resource_id, config = handler.create_resource(
    "web-server-nic",
    {
        "nic_name": "web-server-nic",
        "vm_id": "/subscriptions/.../virtualMachines/web-server",
        "subnet_id": "/subscriptions/.../subnets/default",
        "private_ip": "10.0.1.10"
    },
    "Microsoft.Network/networkInterfaces",
    {
        "subscription_id": "prod-sub",
        "resource_group": "production",
        "user_id": "admin@company.com"
    }
)
```

### NIC Configuration Properties
- `nic_name`: 3-80 characters
- `vm_id`: Resource ID of attached VM
- `subnet_id`: Resource ID of subnet
- `private_ip`: Optional static IP (10.0.0.0/8 range)
- `ip_configurations`: Optional list of IP configs
- `dns_settings`: Optional DNS settings
- `network_security_group`: Optional NSG reference

## Use Cases

- Web tier NICs: `web-nic-01`, `web-nic-02`
- Database tier NICs: `db-nic-01`, `db-nic-02`
- Private endpoints: `endpoint-nic-sql`, `endpoint-nic-cosmos`
- Secondary NICs: `web-server-secondary-nic`

## Networking Patterns

### Pattern 1: NIC with Static IP
```python
handler.create_resource(
    "db-nic-01",
    {
        "nic_name": "db-nic-01",
        "vm_id": "...",
        "subnet_id": "...",
        "private_ip": "10.0.1.100"  # Static IP
    },
    ...
)
```

### Pattern 2: Multiple NICs on Single VM
```python
# Primary NIC
handler.create_resource("vm-primary-nic", {...})

# Secondary NIC for data network
handler.create_resource("vm-secondary-nic", {...})

# Both attached to same VM_id
```

### Pattern 3: NIC with Network Security Group
```python
handler.create_resource(
    "secure-nic",
    {
        "nic_name": "secure-nic",
        "vm_id": "...",
        "subnet_id": "...",
        "network_security_group": "/subscriptions/.../networkSecurityGroups/web-nsg"
    },
    ...
)
```

## Related Resources

NICs are typically created as part of:
1. VM provisioning (primary NIC)
2. Network configuration changes
3. Multi-NIC VM setups
4. Private endpoint creation

See `compute/` examples for VM provisioning workflows.
