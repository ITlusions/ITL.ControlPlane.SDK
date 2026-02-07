# Compute - Advanced Level

Resource scoping and multi-handler provider patterns for VMs.

## Files
- **`scoped_resource_examples.py`** - Advanced VM handler patterns
  - VirtualMachineHandler with RG scoping
  - ComputeProvider using multiple handlers
  - Multi-resource provisioning workflows
  - Duplicate detection and error handling
  - Real-world VM stack provisioning (VM + NIC + Storage)

**Run:** `python scoped_resource_examples.py`

## Key Patterns

### RG-Scoped Uniqueness
```python
# Same VM name allowed in different RGs
vm1 = handler.create_resource(
    "web-vm",
    {...},
    "Microsoft.Compute/virtualMachines",
    {"subscription_id": "sub", "resource_group": "app-rg"}  # app-rg
)

vm2 = handler.create_resource(
    "web-vm",  # Same name, different RG - OK!
    {...},
    "Microsoft.Compute/virtualMachines",
    {"subscription_id": "sub", "resource_group": "network-rg"}  # network-rg
)

# But duplicate in same RG fails
vm3 = handler.create_resource(
    "web-vm",  # Duplicate in app-rg - ERROR!
    {...},
    {"subscription_id": "sub", "resource_group": "app-rg"}
)  # ValueError: Resource already exists in app-rg
```

### Multi-Handler Provider
```python
class ComputeProvider:
    def __init__(self):
        self.vm_handler = VirtualMachineHandler(storage)
        self.nic_handler = NetworkInterfaceHandler(storage)
        self.sa_handler = StorageAccountHandler(storage)
    
    async def provision_vm_stack(self, vm_name, sub_id, rg_name):
        """Provision complete VM with NIC and storage"""
        sa_id, _ = self.sa_handler.create_from_config(...)  # Global
        nic_id, _ = self.nic_handler.create_from_config(...)  # RG-scoped
        vm_id, _ = self.vm_handler.create_from_spec(...)  # RG-scoped
        return {"vm_id": vm_id, "nic_id": nic_id, "sa_id": sa_id}
```

### Scope Context Requirements
```python
# RG-scoped: need both subscription_id AND resource_group
scope_context = {
    "subscription_id": "prod-sub",
    "resource_group": "app-rg"
}

# Global: no context needed
scope_context = {}
```

## Concepts

### Uniqueness Scope Matrix

| Scope | Definition | Example |
|-------|------------|---------|
| **Subscription + RG** | Unique within RG only | VM: prod-rg/web-vm AND dev-rg/web-vm OK |
| **Subscription** | Unique per subscription | RG: same name in different subs OK |
| **Global** | Unique across system | Storage Account: name never reusable |
| **Management Group** | Unique per MG | Policy: same name in different MGs OK |

### Real-World Scenario: Multi-Environment

```python
# Same names in different environments - perfectly valid!

for env in ["dev", "staging", "prod"]:
    vm_id = handler.create_resource(
        "app-server",  # Same name everywhere
        {...},
        "Microsoft.Compute/virtualMachines",
        {
            "subscription_id": f"{env}-sub",
            "resource_group": f"{env}-rg"
        }
    )
```

## Prerequisites
- Complete [intermediate/](../intermediate/) level

## Next Steps
→ **[Deployment](../../deployment/intermediate/)** - Deploy computed resources with Pulumi
