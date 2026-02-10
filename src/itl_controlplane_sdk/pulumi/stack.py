"""
Pulumi Stack Configuration and Management

Base class for managing Pulumi stacks with ITL ControlPlane resources.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from enum import Enum
import pulumi
import pulumi.automation as auto


class StackEnvironment(str, Enum):
    """Supported Pulumi stack environments."""
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


@dataclass
class StackConfig:
    """Configuration for a Pulumi stack."""
    
    organization: str
    project: str
    stack: str
    environment: StackEnvironment
    region: str
    tags: Dict[str, str] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def full_stack_name(self) -> str:
        """Get full stack name in organization/project/stack format."""
        return f"{self.organization}/{self.project}/{self.stack}"


class PulumiStack:
    """
    Base class for managing Pulumi stacks with ITL ControlPlane SDK.
    
    Provides stack lifecycle management, resource deployment, and state management.
    """
    
    def __init__(self, config: StackConfig):
        """
        Initialize Pulumi stack manager.
        
        Args:
            config: StackConfig with stack configuration
        """
        self.config = config
        self.stack: Optional[auto.Stack] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the Pulumi stack."""
        try:
            self.stack = await auto.select_stack(
                stack_name=self.config.stack,
                project_name=self.config.project,
                work_dir=f"./stacks/{self.config.project}"
            )
            self._initialized = True
        except Exception as e:
            raise RuntimeError(f"Failed to initialize stack: {e}")
    
    async def create_stack(self) -> None:
        """Create a new Pulumi stack."""
        if self._initialized:
            raise RuntimeError("Stack already initialized")
        
        try:
            self.stack = await auto.create_stack(
                stack_name=self.config.stack,
                project_name=self.config.project,
                program=self._get_program
            )
            self._initialized = True
        except Exception as e:
            raise RuntimeError(f"Failed to create stack: {e}")
    
    async def deploy(self) -> None:
        """Deploy the stack."""
        if not self._initialized or not self.stack:
            raise RuntimeError("Stack not initialized")
        
        try:
            # Set configuration
            await self._set_config()
            
            # Run update
            result = await self.stack.up()
            
            return {
                "status": "success",
                "outputs": result.outputs,
                "summary": result.summary
            }
        except Exception as e:
            raise RuntimeError(f"Deployment failed: {e}")
    
    async def destroy(self) -> None:
        """Destroy the stack."""
        if not self._initialized or not self.stack:
            raise RuntimeError("Stack not initialized")
        
        try:
            await self.stack.destroy()
        except Exception as e:
            raise RuntimeError(f"Destroy failed: {e}")
    
    async def get_state(self) -> Dict[str, Any]:
        """Get current stack state."""
        if not self._initialized or not self.stack:
            raise RuntimeError("Stack not initialized")
        
        try:
            # Refresh to get latest state
            await self.stack.refresh()
            
            # Get outputs
            outputs = await self.stack.get_outputs()
            
            return {
                "stack_name": self.config.stack,
                "environment": self.config.environment.value,
                "outputs": outputs
            }
        except Exception as e:
            raise RuntimeError(f"Failed to get state: {e}")
    
    async def _set_config(self) -> None:
        """Set stack configuration."""
        if not self.stack:
            return
        
        config_map = {
            "aws:region": self.config.region,
            "pulumi:tags": self.config.tags,
        }
        
        # Add custom config
        config_map.update({
            f"{self.config.project}:{key}": str(value)
            for key, value in self.config.config.items()
        })
        
        for key, value in config_map.items():
            await self.stack.set_config(key, auto.ConfigValue(value=str(value)))
    
    def _get_program(self) -> None:
        """
        Get Pulumi program for this stack.
        
        Override this method in subclasses to define resources.
        """
        pass
    
    def export(self, name: str, value: Any) -> None:
        """Export a stack output."""
        pulumi.export(name, value)
