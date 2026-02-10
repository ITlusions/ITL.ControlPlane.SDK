"""
Pulumi Deployment Manager

Handles deployment orchestration using Pulumi Automation API.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import asyncio

from .stack import PulumiStack, StackConfig, StackEnvironment
from .resource_mapper import ResourceMapper


@dataclass
class DeploymentResult:
    """Result of a deployment operation."""
    
    success: bool
    timestamp: datetime
    stack_name: str
    outputs: Dict[str, Any]
    errors: List[str]
    duration_seconds: float


class PulumiDeployment:
    """
    Orchestrates deployments using Pulumi and ITL ControlPlane resources.
    
    Manages lifecycle of multiple stacks and their resources.
    """
    
    def __init__(self, organization: str, project: str):
        """
        Initialize deployment manager.
        
        Args:
            organization: Pulumi organization name
            project: Pulumi project name
        """
        self.organization = organization
        self.project = project
        self.stacks: Dict[str, PulumiStack] = {}
        self.mapper = ResourceMapper()
    
    async def create_stack(
        self,
        stack_name: str,
        environment: StackEnvironment,
        region: str,
        tags: Optional[Dict[str, str]] = None
    ) -> PulumiStack:
        """
        Create a new deployment stack.
        
        Args:
            stack_name: Name of the stack
            environment: Environment type (dev, staging, prod)
            region: AWS region for deployment
            tags: Optional tags for the stack
            
        Returns:
            Created PulumiStack
        """
        config = StackConfig(
            organization=self.organization,
            project=self.project,
            stack=stack_name,
            environment=environment,
            region=region,
            tags=tags or {"Environment": environment.value}
        )
        
        stack = PulumiStack(config)
        await stack.create_stack()
        
        self.stacks[stack_name] = stack
        return stack
    
    async def deploy_resources(
        self,
        stack_name: str,
        resources: List[Dict[str, Any]]
    ) -> DeploymentResult:
        """
        Deploy resources to a stack.
        
        Args:
            stack_name: Target stack name
            resources: List of ITL resource definitions
            
        Returns:
            DeploymentResult with outcome
        """
        start_time = datetime.now()
        errors = []
        outputs = {}
        
        if stack_name not in self.stacks:
            return DeploymentResult(
                success=False,
                timestamp=start_time,
                stack_name=stack_name,
                outputs={},
                errors=["Stack not found"],
                duration_seconds=0
            )
        
        stack = self.stacks[stack_name]
        
        try:
            # Map and create resources
            for resource in resources:
                try:
                    pulumi_resource = self.mapper.create_resource(resource, stack_name)
                    stack.export(resource.get("name"), pulumi_resource)
                except Exception as e:
                    errors.append(f"Failed to create resource {resource.get('name')}: {str(e)}")
            
            # Deploy stack
            deploy_result = await stack.deploy()
            outputs = deploy_result.get("outputs", {})
            
            success = len(errors) == 0
            
        except Exception as e:
            success = False
            errors.append(f"Deployment failed: {str(e)}")
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return DeploymentResult(
            success=success,
            timestamp=start_time,
            stack_name=stack_name,
            outputs=outputs,
            errors=errors,
            duration_seconds=duration
        )
    
    async def destroy_stack(self, stack_name: str) -> DeploymentResult:
        """
        Destroy a stack and its resources.
        
        Args:
            stack_name: Stack to destroy
            
        Returns:
            DeploymentResult with outcome
        """
        start_time = datetime.now()
        
        if stack_name not in self.stacks:
            return DeploymentResult(
                success=False,
                timestamp=start_time,
                stack_name=stack_name,
                outputs={},
                errors=["Stack not found"],
                duration_seconds=0
            )
        
        stack = self.stacks[stack_name]
        
        try:
            await stack.destroy()
            del self.stacks[stack_name]
            success = True
            errors = []
        except Exception as e:
            success = False
            errors = [f"Destroy failed: {str(e)}"]
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return DeploymentResult(
            success=success,
            timestamp=start_time,
            stack_name=stack_name,
            outputs={},
            errors=errors,
            duration_seconds=duration
        )
    
    async def get_stack_outputs(self, stack_name: str) -> Dict[str, Any]:
        """
        Get outputs from a stack.
        
        Args:
            stack_name: Stack to query
            
        Returns:
            Stack outputs
        """
        if stack_name not in self.stacks:
            raise ValueError(f"Stack not found: {stack_name}")
        
        stack = self.stacks[stack_name]
        return await stack.get_state()
    
    def list_stacks(self) -> List[str]:
        """Get list of managed stacks."""
        return list(self.stacks.keys())
    
    def get_resource_types(self) -> List[str]:
        """Get supported resource types."""
        return self.mapper.get_supported_types()
