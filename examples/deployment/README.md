# Deployment Examples

Infrastructure as Code and orchestration patterns using Pulumi.

## Files

### `pulumi_deployment_example.py`
Demonstrates Pulumi integration for infrastructure deployment:
- Single environment deployment (dev)
- Multi-environment deployment (dev, staging, prod)
- Resource group creation and tagging
- Async/await deployment workflows
- Stack management and outputs

**Key examples:**
```python
deployer = PulumiDeployment(
    organization="itlusions",
    project="controlplane-infrastructure"
)

# Create development stack
dev_stack = await deployer.create_stack(
    stack_name="dev",
    environment=StackEnvironment.DEV,
    region="eu-west-1",
    tags={
        "Environment": "dev",
        "Team": "platform"
    }
)

# Deploy resources
result = await deployer.deploy_resources(
    stack_name="dev",
    resources=[
        {
            "type": "resourcegroups",
            "name": "platform-core",
            "properties": {...}
        }
    ]
)
```

**Run:** `python pulumi_deployment_example.py`

## Concepts

### Pulumi Stack
- Isolated deployment environment
- Configuration and state management
- Resource tracking and outputs
- Environment-specific settings

### Stack Environments
- **DEV**: Development environment (eu-west-1)
- **STAGING**: Staging environment (eu-west-1)
- **PROD**: Production environment (eu-central-1)

### Deployment Workflow
1. Create stack with environment configuration
2. Define resources as dictionaries
3. Deploy resources (async operation)
4. Retrieve stack outputs
5. Destroy stack when done

## Use Cases

### Single Environment Deployment
```python
deployer = PulumiDeployment(
    organization="itlusions",
    project="my-project"
)

stack = await deployer.create_stack(
    stack_name="dev",
    environment=StackEnvironment.DEV,
    region="eu-west-1"
)

result = await deployer.deploy_resources(
    stack_name="dev",
    resources=[...]
)
```

### Multi-Environment Deployment
```python
environments = [
    ("dev", StackEnvironment.DEV, "eu-west-1"),
    ("staging", StackEnvironment.STAGING, "eu-west-1"),
    ("prod", StackEnvironment.PROD, "eu-central-1"),
]

stacks = {}
for stack_name, env, region in environments:
    stack = await deployer.create_stack(
        stack_name=stack_name,
        environment=env,
        region=region
    )
    stacks[stack_name] = stack

# Deploy to all stacks
for stack_name, stack in stacks.items():
    await deployer.deploy_resources(
        stack_name=stack_name,
        resources=[...]
    )
```

## Resource Types

### Resource Groups
```python
{
    "type": "resourcegroups",
    "name": "platform-core",
    "properties": {
        "display_name": "Platform Core Resources",
        "tags": {
            "component": "core",
            "managed": "true"
        }
    }
}
```

### Tags
```python
{
    "type": "tags",
    "name": "standard-tags",
    "properties": {
        "tags": {
            "CostCenter": "platform",
            "Owner": "devops-team",
            "Compliance": "true"
        }
    }
}
```

## Deployment Results

```python
result = await deployer.deploy_resources(...)

print(f"Success: {result.success}")
print(f"Duration: {result.duration_seconds:.2f}s")
print(f"Errors: {result.errors}")
print(f"Outputs: {result.outputs}")
```

## Stack Management

### Create Stack
```python
stack = await deployer.create_stack(
    stack_name="dev",
    environment=StackEnvironment.DEV,
    region="eu-west-1",
    tags={"Environment": "dev"}
)
```

### List Stacks
```python
stacks = deployer.list_stacks()
print(f"Stacks: {stacks}")
```

### Get Stack Outputs
```python
state = await deployer.get_stack_outputs("dev")
print(f"Stack state: {state}")
```

### Destroy Stack
```python
result = await deployer.destroy_stack("dev")
print(f"Destroy success: {result.success}")
```

## Regional Configuration

- **eu-west-1**: Ireland (Development, Staging)
- **eu-central-1**: Frankfurt (Production)
- **us-east-1**: US East (Alternative US region)
- **Custom regions**: Specify region parameter

## Tagging Strategy

Standard tags for deployments:
- **Environment**: dev, staging, prod
- **Team**: owning team name
- **Project**: project identifier
- **CostCenter**: billing center
- **ManagedBy**: automation tool (Pulumi)
- **CreatedDate**: ISO 8601 timestamp

## Integration Patterns

### Pattern 1: Deploy Full Stack
```python
# Create compute + storage + network together
resources = [
    {"type": "compute", "name": "vms", "properties": {...}},
    {"type": "storage", "name": "sa", "properties": {...}},
    {"type": "network", "name": "nics", "properties": {...}}
]

result = await deployer.deploy_resources(
    stack_name="prod",
    resources=resources
)
```

### Pattern 2: Environment Parity
```python
# Deploy identical resources to multiple environments
for env in ["dev", "staging", "prod"]:
    await deployer.deploy_resources(
        stack_name=env,
        resources=same_resources  # Same config, different env
    )
```

### Pattern 3: Progressive Deployment
```python
# Deploy to dev first
await deployer.deploy_resources(stack_name="dev", resources=resources)

# After testing, deploy to staging
await deployer.deploy_resources(stack_name="staging", resources=resources)

# Finally to production
await deployer.deploy_resources(stack_name="prod", resources=resources)
```

## Async/Await Patterns

```python
# Single deployment
result = await deployer.deploy_resources(...)

# Multiple deployments in parallel
results = await asyncio.gather(
    deployer.deploy_resources(stack_name="dev", resources=resources),
    deployer.deploy_resources(stack_name="staging", resources=resources),
    deployer.deploy_resources(stack_name="prod", resources=resources)
)
```

## Troubleshooting

- **Connection errors**: Verify Pulumi installation and configuration
- **Deployment timeouts**: Check resource complexity and region availability
- **Stack conflicts**: Ensure unique stack names per deployment
- **Resource conflicts**: Verify resource naming is unique within scope

## Prerequisites

```bash
pip install pulumi>=3.0.0
pulumi plugin install resource azure
pulumi login
```

## Related Examples

- See `compute/`, `storage/`, `network/` for resource handler examples
- See `management/` for governance patterns
- See `tests/` for deployment validation patterns
