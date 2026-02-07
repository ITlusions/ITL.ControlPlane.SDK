"""
Example: Using Pulumi Module with ITL ControlPlane SDK

Demonstrates deploying infrastructure using Pulumi and ITL resources.
"""

import asyncio
from itl_controlplane_sdk.pulumi import (
    PulumiDeployment,
    StackEnvironment,
)


async def deploy_example():
    """Example deployment workflow."""
    
    # Initialize deployment manager
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
            "Team": "platform",
            "Project": "controlplane"
        }
    )
    
    print(f"Created stack: {dev_stack.config.full_stack_name}")
    
    # Define resources
    resources = [
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
        },
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
    ]
    
    # Deploy resources
    print("Deploying resources...")
    result = await deployer.deploy_resources(
        stack_name="dev",
        resources=resources
    )
    
    print(f"Deployment result:")
    print(f"  Success: {result.success}")
    print(f"  Duration: {result.duration_seconds:.2f}s")
    if result.errors:
        print(f"  Errors: {result.errors}")
    print(f"  Outputs: {result.outputs}")
    
    # Get stack outputs
    try:
        state = await deployer.get_stack_outputs("dev")
        print(f"\nStack state: {state}")
    except Exception as e:
        print(f"Error getting stack state: {e}")
    
    # Cleanup
    print("\nDestroying stack...")
    destroy_result = await deployer.destroy_stack("dev")
    print(f"Destroy success: {destroy_result.success}")


async def multi_environment_example():
    """Example deploying to multiple environments."""
    
    deployer = PulumiDeployment(
        organization="itlusions",
        project="controlplane-multi-env"
    )
    
    environments = [
        ("dev", StackEnvironment.DEV, "eu-west-1"),
        ("staging", StackEnvironment.STAGING, "eu-west-1"),
        ("prod", StackEnvironment.PROD, "eu-central-1"),
    ]
    
    stacks = {}
    
    # Create stacks for each environment
    for stack_name, env, region in environments:
        print(f"Creating {stack_name} stack...")
        stack = await deployer.create_stack(
            stack_name=stack_name,
            environment=env,
            region=region,
            tags={"Environment": env.value}
        )
        stacks[stack_name] = stack
    
    print(f"Created stacks: {deployer.list_stacks()}")
    print(f"Supported resource types: {deployer.get_resource_types()}")


if __name__ == "__main__":
    # Run example
    asyncio.run(deploy_example())
    
    # Run multi-environment example
    print("\n" + "="*60 + "\n")
    asyncio.run(multi_environment_example())
