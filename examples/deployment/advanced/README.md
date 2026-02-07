# Deployment - Advanced Level

Multi-environment deployments and complex infrastructure patterns.

## Files
- (Advanced patterns in repository root `src/`)

## Multi-Environment Strategy

Advanced deployments handle multiple environments with:
- Shared infrastructure (security, logging)
- Environment-specific scaling
- Cross-environment dependencies
- Cost optimization per environment

### Architecture Pattern

```
┌─────────────────────────────────────┐
│    Shared Infrastructure MG         │
│  (Security, Logging, Compliance)    │
└────────────────┬────────────────────┘
                 │
    ┌────────────┼────────────┐
    ▼            ▼            ▼
 Production   Staging     Development
    │            │            │
    ├── Compute  ├── Compute  ├── Compute (B2s)
    ├── DB       ├── DB       └── DB
    ├── Network  ├── Network
    └── Storage  └── Storage
```

## Complex Deployment Example

```python
import pulumi
from itl_control_plane_sdk import ResourceProvider

config = pulumi.Config()
environment = config.get('environment')
subscription_id = config.require('subscription_id')

provider = ResourceProvider("multi-env-provider")

# Shared security RG
security_rg = provider.create_resource(
    "security-rg",
    {"location": "westeurope"},
    "Microsoft.Resources/resourceGroups",
    {"subscription_id": subscription_id}
)

# Environment-specific RG
app_rg = provider.create_resource(
    f"app-{environment}-rg",
    {"location": "westeurope"},
    "Microsoft.Resources/resourceGroups",
    {"subscription_id": subscription_id}
)

# Environment-specific scaling
scaling_config = {
    'prod': {
        'vm_size': 'Standard_D4s_v3',
        'instance_count': 3,
        'db_edition': 'Premium',
        'backup_retention': 35
    },
    'staging': {
        'vm_size': 'Standard_D2s_v3',
        'instance_count': 2,
        'db_edition': 'Standard',
        'backup_retention': 14
    },
    'dev': {
        'vm_size': 'Standard_B2s',
        'instance_count': 1,
        'db_edition': 'Basic',
        'backup_retention': 7
    }
}[environment]

# Create compute based on environment
vms = []
for i in range(scaling_config['instance_count']):
    vm = provider.create_resource(
        f"app-vm-{i:02d}",
        {"size": scaling_config['vm_size']},
        "Microsoft.Compute/virtualMachines",
        {
            "subscription_id": subscription_id,
            "resource_group": app_rg.id
        }
    )
    vms.append(vm)

# Create database with environment-specific settings
database = provider.create_resource(
    f"appdb-{environment}",
    {
        "db_type": "SQL",
        "edition": scaling_config['db_edition'],
        "backup_retention": scaling_config['backup_retention']
    },
    "Microsoft.Sql/servers/databases",
    {
        "subscription_id": subscription_id,
        "resource_group": app_rg.id
    }
)

# Export environment-specific outputs
pulumi.export('environment', environment)
pulumi.export('vm_count', scaling_config['instance_count'])
pulumi.export('vm_sku', scaling_config['vm_size'])
pulumi.export('database_edition', scaling_config['db_edition'])
```

## Multi-Stack Dependencies

Share outputs between stacks:

```python
# Stack 1: Networking (shared)
import pulumi

vnet = provider.create_resource(
    "shared-vnet",
    {"address_space": "10.0.0.0/16"}
)

pulumi.export('vnet_id', vnet.id)
pulumi.export('vnet_address_space', vnet.properties.address_space)

# Stack 2: Application (depends on networking)
import pulumi
from pulumi import automation as auto

# Read vnet from other stack
stack_ref = pulumi.StackReference(f"org/project/networking/prod")
vnet_id = stack_ref.get_output('vnet_id')

# Create resources that depend on vnet
subnet = provider.create_resource(
    "app-subnet",
    {
        "vnet_id": vnet_id,
        "address_prefix": "10.0.1.0/24"
    }
)
```

## Deployment with Validation

```python
import pulumi

def validate_deployment(resources: dict) -> bool:
    """Validate all resources created successfully"""
    required = ['resource_group', 'vms', 'database']
    
    for req in required:
        if req not in resources or not resources[req]:
            pulumi.export('validation_error', f'Missing {req}')
            return False
    
    return True

# Create all resources
rg = provider.create_resource(...)
vms = [provider.create_resource(...) for _ in range(3)]
db = provider.create_resource(...)

resources = {
    'resource_group': rg,
    'vms': vms,
    'database': db
}

# Validate before export
if validate_deployment(resources):
    pulumi.export('status', 'success')
    pulumi.export('resource_ids', {
        'rg': rg.id,
        'vms': [vm.id for vm in vms],
        'db': db.id
    })
else:
    pulumi.export('status', 'failed')
```

## Pulumi Automation API

Programmatic deployment:

```python
import pulumi
from pulumi import automation as auto

def deploy_stack(environment: str, config: dict):
    """Deploy via automation API"""
    
    def deploy_program():
        # Your deployment code
        pass
    
    # Create or select stack
    stack = auto.create_or_select_stack(
        stack_name=environment,
        project_name="myapp",
        program=deploy_program
    )
    
    # Set configuration
    stack.set_config('environment', auto.ConfigValue(value=environment))
    
    # Preview
    preview = stack.preview()
    
    # Deploy
    up_result = stack.up()
    
    return up_result
```

## Concepts

### Stack Configuration
- Stored in `Pulumi.{stack}.yaml`
- Encrypted secrets via `pulumi config set --secret`
- Environment-specific values
- Multiple source support (env vars, files)

### Stack Outputs
- Exported via `pulumi.export()`
- Accessible from other stacks
- Used for cross-stack references
- Available in `pulumi stack output` command

### Stack State
- Stored in backend (local, S3, Pulumi Service)
- Tracks resource lifecycle
- Enables destroy and updates
- Critical for CI/CD pipelines

## Prerequisites
- Complete [intermediate/](../intermediate/) level
- Install Pulumi CLI
- Understand stack management
- Familiar with all resource types

## Next Steps
→ **[Tests](../../tests/integration/)** - Test your deployments
