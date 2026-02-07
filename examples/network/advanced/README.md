# Network - Advanced Level

Resource scoping and multi-NIC VM patterns.

## Files
- **`scoped_resource_examples.py`** - Advanced NIC handler patterns
  - NetworkInterfaceHandler with RG scoping
  - Multi-NIC VM configurations
  - NIC-to-VM linkage patterns
  - Real-world networking scenarios

**Run:** `python scoped_resource_examples.py`

## Key Patterns

### RG-Scoped Uniqueness (Like VMs)
```python
# Same NIC name allowed in different RGs
nic1 = handler.create_resource(
    "app-nic",
    {...},
    "Microsoft.Network/networkInterfaces",
    {"subscription_id": "sub", "resource_group": "app-rg"}
)

nic2 = handler.create_resource(
    "app-nic",  # Same name, different RG - OK!
    {...},
    {"subscription_id": "sub", "resource_group": "network-rg"}
)

# But duplicate in same RG fails
nic3 = handler.create_resource(
    "app-nic",  # Duplicate in app-rg - ERROR!
    {...},
    {"subscription_id": "sub", "resource_group": "app-rg"}
)  # ValueError: Resource already exists in app-rg
```

### Multi-NIC VM Configuration

Some VMs need multiple NICs for:
- Separation of concerns (traffic types)
- Multiple subnets
- Performance optimization

```python
class ComputeProvider:
    async def provision_multi_nic_vm(self, vm_name, sub_id, rg_name):
        # Primary NIC (public traffic)
        primary_nic = self.nic_handler.create_from_config(
            f"{vm_name}-primary",
            {
                "vm_id": vm_id,
                "subnet_id": public_subnet_id
            },
            sub_id, rg_name
        )
        
        # Secondary NIC (data traffic)
        secondary_nic = self.nic_handler.create_from_config(
            f"{vm_name}-secondary",
            {
                "vm_id": vm_id,
                "subnet_id": data_subnet_id
            },
            sub_id, rg_name
        )
        
        return [primary_nic, secondary_nic]
```

## Real-World Scenario: Application Tier

```python
# Web tier - NICs in public subnet
for i in range(3):
    web_nic = handler.create_resource(
        f"web-{i:02d}-nic",
        {
            "vm_id": f"/subscriptions/.../web-{i:02d}",
            "subnet_id": public_subnet_id
        },
        {...},
        {"subscription_id": "prod", "resource_group": "web-rg"}
    )

# Database tier - NICs in private subnet
for i in range(2):
    db_nic = handler.create_resource(
        f"db-{i:02d}-nic",
        {
            "vm_id": f"/subscriptions/.../db-{i:02d}",
            "subnet_id": private_subnet_id
        },
        {...},
        {"subscription_id": "prod", "resource_group": "data-rg"}
    )
```

## NIC Configuration Patterns

### Pattern 1: Static IP Assignment
```python
handler.create_resource(
    "static-ip-nic",
    {
        "nic_name": "static-ip-nic",
        "vm_id": vm_id,
        "subnet_id": subnet_id,
        "private_ip": "10.0.1.100"  # Fixed IP
    },
    ...
)
```

### Pattern 2: NSG Association
```python
handler.create_resource(
    "secure-nic",
    {
        "nic_name": "secure-nic",
        "vm_id": vm_id,
        "subnet_id": subnet_id,
        "network_security_group": nsg_id  # Link NSG
    },
    ...
)
```

### Pattern 3: Multiple Subnets
```python
# App subnet NIC
nic1 = handler.create_resource(
    "vm-app-nic",
    {
        "subnet_id": app_subnet_id,
        "vm_id": vm_id
    },
    ...
)

# Data subnet NIC
nic2 = handler.create_resource(
    "vm-data-nic",
    {
        "subnet_id": data_subnet_id,
        "vm_id": vm_id
    },
    ...
)
```

## Concepts

### NIC Lifecycle
1. **Create** - Attach to subnet
2. **Attach** - Link to VM
3. **Configure** - Set IPs, DNS, NSG
4. **Monitor** - Track state and metrics
5. **Delete** - Detach from VM and subnet

### RG Scoping for Network
Like compute resources, NICs are RG-scoped:
- Same name allowed in different RGs
- Scope context: `subscription_id` + `resource_group`
- Uniqueness check: per RG only

## Prerequisites
- Complete [intermediate/](../intermediate/) level
- Understand RG scoping (see [compute/advanced/](../../compute/advanced/))
- Understand VM-NIC relationships

## Next Steps
→ **[Deployment](../../deployment/intermediate/)** - Deploy network resources with Pulumi
