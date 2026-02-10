# Pulumi Infrastructure as Code Module

Sub-module for Pulumi integration with ITL ControlPlane SDK.

## Overview

The `pulumi` module provides Infrastructure as Code (IaC) capabilities by integrating Pulumi with the ITL ControlPlane SDK. It enables:

- **Stack Management**: Create, deploy, and destroy Pulumi stacks
- **Resource Mapping**: Convert ITL ControlPlane resources to Pulumi resources
- **Multi-Environment Support**: Manage dev, staging, and production deployments
- **Deployment Orchestration**: Automate infrastructure deployments with full lifecycle management

## Components

### `stack.py` - Stack Management

Core class for Pulumi stack lifecycle:

```python
from itl_controlplane_sdk.pulumi import PulumiStack, StackConfig, StackEnvironment

# Create stack configuration
config = StackConfig(
    organization="itlusions",
    project="my-project",
    stack="dev",
    environment=StackEnvironment.DEV,
    region="eu-west-1"
)

# Initialize and deploy
stack = PulumiStack(config)
await stack.create_stack()
await stack.deploy()

# Get stack state
state = await stack.get_state()
print(state["outputs"])

# Cleanup
await stack.destroy()
```

### `resource_mapper.py` - Resource Mapping

Maps ITL ControlPlane resources to Pulumi:

```python
from itl_controlplane_sdk.pulumi import ResourceMapper

mapper = ResourceMapper()

# Map ITL resource to Pulumi format
itl_resource = {
    "type": "resourcegroups",
    "name": "platform-core",
    "properties": {
        "display_name": "Core Platform Resources",
        "tags": {"env": "dev"}
    }
}

pulumi_def = mapper.map_resource(itl_resource)

# Get supported types
types = mapper.get_supported_types()
print(types)  # ["resourcegroups", "tags", "locations"]
```

### `deployment.py` - Deployment Orchestration

High-level deployment management:

```python
from itl_controlplane_sdk.pulumi import PulumiDeployment, StackEnvironment

deployer = PulumiDeployment(
    organization="itlusions",
    project="infrastructure"
)

# Create stack
stack = await deployer.create_stack(
    stack_name="dev",
    environment=StackEnvironment.DEV,
    region="eu-west-1",
    tags={"Team": "platform"}
)

# Deploy resources
resources = [...]  # ITL resource definitions
result = await deployer.deploy_resources("dev", resources)

print(f"Success: {result.success}")
print(f"Duration: {result.duration_seconds}s")
print(f"Outputs: {result.outputs}")

# Cleanup
await deployer.destroy_stack("dev")
```

## Supported Resource Types

- **resourcegroups** - Maps to AWS Security Groups
- **tags** - Generic resource tags
- **locations** - Maps to AWS Availability Zones
- More types can be registered via `ResourceMapper.register_mapping()`

## Environment Support

- `DEV` - Development environment
- `STAGING` - Staging/UAT environment
- `PROD` - Production environment

## Dependencies

Requires:
- `pulumi>=3.0.0`
- `pulumi-automation>=0.4.0`
- Python 3.9+

## Usage Patterns

### Simple Stack Deployment

```python
async def deploy():
    deployer = PulumiDeployment("org", "project")
    
    await deployer.create_stack(
        "prod",
        StackEnvironment.PROD,
        "eu-central-1"
    )
    
    result = await deployer.deploy_resources("prod", resources)
    return result.success
```

### Multi-Environment Deployment

```python
async def deploy_all():
    deployer = PulumiDeployment("org", "project")
    
    for env_name, env, region in [
        ("dev", StackEnvironment.DEV, "eu-west-1"),
        ("staging", StackEnvironment.STAGING, "eu-west-1"),
        ("prod", StackEnvironment.PROD, "eu-central-1")
    ]:
        await deployer.create_stack(env_name, env, region)
    
    # Deploy resources to each environment
    for stack_name in deployer.list_stacks():
        result = await deployer.deploy_resources(stack_name, resources)
        print(f"{stack_name}: {result.success}")
```

### Custom Resource Mapping

```python
from itl_controlplane_sdk.pulumi import ResourceMapper, ResourceMapping

mapper = ResourceMapper()

# Register custom mapping
mapper.register_mapping(ResourceMapping(
    itl_type="custom-resource",
    pulumi_type="aws:s3:Bucket",
    mapper_fn=lambda itl: {
        "bucket": itl["properties"]["bucket_name"],
        "acl": "private"
    }
))
```

## Error Handling

All async methods raise exceptions on failure:

```python
try:
    result = await deployer.deploy_resources("stack", resources)
    if not result.success:
        print(f"Errors: {result.errors}")
except Exception as e:
    print(f"Deployment error: {e}")
```

## See Also

- [Pulumi Documentation](https://www.pulumi.com/docs/)
- [Pulumi Automation API](https://www.pulumi.com/docs/reference/automation-api/)
- [ITL ControlPlane Integration](../05-INTEGRATION.md)
