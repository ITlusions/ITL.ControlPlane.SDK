# Deployment - Intermediate Level

Pulumi Infrastructure as Code with SDK integration.

## Files
- **`pulumi_deployment_example.py`** - Complete Pulumi program
  - Environment-specific configuration
  - Resource group deployment
  - Compute, storage, and network resources
  - Export outputs (IDs, connection strings)
  - Stack management

**Run:** `pulumi up` (after `pulumi stack init`)

## Basic Pulumi Concepts

### Stacks
Stacks represent environments:
- `dev` - Development environment
- `staging` - Staging environment
- `prod` - Production environment

### Programs
Programs define resources via SDK:

```python
from itl_control_plane_sdk import ResourceProvider, Resource

def create_app_stack():
    # Create provider (control plane)
    provider = ResourceProvider("azure-provider")
    
    # Create resource group
    rg = provider.create_resource(
        "app-rg",
        {"location": "westeurope"},
        "Microsoft.Resources/resourceGroups"
    )
    
    # Create VM
    vm = provider.create_resource(
        "app-vm",
        {"size": "Standard_D2s_v3"},
        "Microsoft.Compute/virtualMachines",
        {"subscription_id": "...", "resource_group": rg.id}
    )
    
    return {"rg": rg, "vm": vm}

resources = create_app_stack()
```

## Environment-Specific Configuration

```yaml
# Pulumi.dev.yaml
config:
  azure:region: westeurope
  app:environment: development
  app:vm_size: Standard_B2s
  app:instance_count: 1
  
# Pulumi.prod.yaml
config:
  azure:region: westeurope
  app:environment: production
  app:vm_size: Standard_D2s_v3
  app:instance_count: 3
```

### Using Configuration

```python
import pulumi

config = pulumi.Config()
env = config.get('environment') or 'dev'
vm_size = config.get('vm_size') or 'Standard_B2s'
instance_count = config.get_int('instance_count') or 1

# Create VMs based on environment
vms = []
for i in range(instance_count):
    vm = provider.create_resource(
        f"vm-{env}-{i:02d}",
        {"size": vm_size},
        "Microsoft.Compute/virtualMachines",
        {...}
    )
    vms.append(vm)

# Export outputs
pulumi.export('vm_ids', [vm.id for vm in vms])
```

## Deployment Workflow

### 1. Initialize Stack
```bash
pulumi stack init dev
pulumi config set azure:region westeurope
```

### 2. Preview Changes
```bash
pulumi preview
```

### 3. Deploy
```bash
pulumi up
```

### 4. View Outputs
```bash
pulumi stack output vm_ids
```

### 5. Clean Up
```bash
pulumi destroy
```

## Single Deployment Example

```python
import pulumi
import json
from itl_control_plane_sdk import ResourceProvider

config = pulumi.Config()
environment = config.get('environment') or 'dev'
location = config.get('location') or 'westeurope'

provider = ResourceProvider("azure-provider")

# Create resource group
rg = provider.create_resource(
    f"app-{environment}-rg",
    {"location": location},
    "Microsoft.Resources/resourceGroups"
)

# Create storage account
storage = provider.create_resource(
    f"storage{environment}",
    {
        "account_type": "Standard_GRS",
        "location": location
    },
    "Microsoft.Storage/storageAccounts",
    {"subscription_id": "...", "resource_group": rg.id}
)

# Create virtual network
vnet = provider.create_resource(
    f"vnet-{environment}",
    {"address_space": "10.0.0.0/16"},
    "Microsoft.Network/virtualNetworks",
    {"subscription_id": "...", "resource_group": rg.id}
)

# Export important outputs
pulumi.export('resource_group_id', rg.id)
pulumi.export('storage_account_name', storage.properties.get('name'))
pulumi.export('vnet_address_space', vnet.properties.get('address_space'))
```

## Prerequisites
- Install Pulumi: `curl -fsSL https://get.pulumi.com | sh`
- Understand SDK basics (see [core/beginner/](../../core/beginner/))
- Understand resource handlers (see [compute/intermediate/](../../compute/intermediate/))

## Next Steps
→ **[Advanced](../advanced/)** - Learn multi-environment deployments
