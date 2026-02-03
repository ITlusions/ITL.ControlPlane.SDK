"""
Advanced Resource Handler Mixins

Provides production-ready mixins for resource handlers:
- TimestampedResourceHandler: Auto timestamps on all operations
- ProvisioningStateHandler: Resource lifecycle state management
- ValidatedResourceHandler: Pydantic schema validation

These can be mixed with ScopedResourceHandler for scope-aware resources:
    class MyResource(
        TimestampedResourceHandler,
        ProvisioningStateHandler,
        ValidatedResourceHandler,
        ScopedResourceHandler
    ):
        UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION]
        SCHEMA_CLASS = MySchema
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Type
from enum import Enum
from pydantic import BaseModel, ValidationError

from .scoped_resources import ScopedResourceHandler, UniquenessScope


class ProvisioningState(str, Enum):
    """Azure resource provisioning state machine."""
    NOT_STARTED = "NotStarted"
    ACCEPTED = "Accepted"
    PROVISIONING = "Provisioning"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    DELETING = "Deleting"
    DELETED = "Deleted"


class TimestampedResourceHandler:
    """
    Mixin: Automatically adds created and modified timestamps to all resources.
    
    Every resource gets these fields:
    - createdTime: UTC ISO 8601 timestamp when created
    - modifiedTime: UTC ISO 8601 timestamp when last modified
    - createdBy: User ID that created the resource
    - modifiedBy: User ID that last modified the resource
    
    Assumes subclass has create_resource and update_resource methods.
    
    Example:
        class VMHandler(TimestampedResourceHandler, ScopedResourceHandler):
            UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION, UniquenessScope.RESOURCE_GROUP]
            RESOURCE_TYPE = "virtualmachines"
        
        handler = VMHandler(storage_dict)
        resource_id, config = handler.create_resource(
            "my-vm",
            {"size": "Standard_D2s_v3"},
            "Compute/virtualmachines",
            {"subscription_id": "sub-1", "user_id": "user@company.com"}
        )
        # config now has: createdTime, modifiedTime, createdBy, modifiedBy
    """
    """
    Automatically adds created and modified timestamps to all resources.
    
    Every resource gets these fields:
    - createdTime: UTC ISO 8601 timestamp when created
    - modifiedTime: UTC ISO 8601 timestamp when last modified
    - createdBy: User ID that created the resource
    - modifiedBy: User ID that last modified the resource
    
    Example:
        class VMHandler(TimestampedResourceHandler):
            UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION, UniquenessScope.RESOURCE_GROUP]
            RESOURCE_TYPE = "virtualmachines"
        
        handler = VMHandler(storage_dict)
        resource_id, config = handler.create_resource(
            "my-vm",
            {"size": "Standard_D2s_v3"},
            "Compute/virtualmachines",
            {"subscription_id": "sub-1", "user_id": "user@company.com"}
        )
        # config now has: createdTime, modifiedTime, createdBy, modifiedBy
    """
    
    def create_resource(
        self,
        name: str,
        resource_data: Dict[str, Any],
        resource_type: str,
        scope_context: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """Create resource with automatic timestamps."""
        now = datetime.utcnow().isoformat() + "Z"
        user_id = scope_context.get("user_id", "system")
        
        resource_data = {
            **resource_data,
            "createdTime": now,
            "modifiedTime": now,
            "createdBy": user_id,
            "modifiedBy": user_id,
        }
        
        return super().create_resource(name, resource_data, resource_type, scope_context)
    
    def update_resource(
        self,
        name: str,
        resource_data: Dict[str, Any],
        scope_context: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """Update resource with new modified timestamp."""
        now = datetime.utcnow().isoformat() + "Z"
        user_id = scope_context.get("user_id", "system")
        
        # Get existing resource to preserve createdTime
        result = self.get_resource(name, scope_context)
        if result:
            resource_id, existing_data = result
            resource_data = {
                **existing_data,
                **resource_data,
                "modifiedTime": now,
                "modifiedBy": user_id,
                # Preserve createdTime and createdBy
            }
        else:
            resource_data = {
                **resource_data,
                "modifiedTime": now,
                "modifiedBy": user_id,
            }
        
        return super().update_resource(name, resource_data, scope_context)


class ProvisioningStateHandler:
    """
    Mixin: Manages Azure resource provisioning state lifecycle.
    
    Resources transition through states:
    - NotStarted → Accepted → Provisioning → Succeeded
    - Or: → Failed (if something went wrong)
    - Delete: Deleting → Deleted
    
    State transitions are validated (no jumping from Provisioning to Deleted, etc.).
    
    Designed to be mixed with other handlers:
        class MyHandler(ProvisioningStateHandler, ScopedResourceHandler):
            pass
    
    Example:
        class RGHandler(ProvisioningStateHandler, ScopedResourceHandler):
            UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION]
            RESOURCE_TYPE = "resourcegroups"
        
        handler = RGHandler(storage_dict)
        resource_id, config = handler.create_resource(
            "prod-rg",
            {"location": "eastus"},
            "Microsoft.Resources/resourceGroups",
            {"subscription_id": "sub-1", "user_id": "user@company.com"}
        )
        # config.provisioning_state = "Accepted" initially
        # Handler internally transitions to "Provisioning" then "Succeeded"
    """
    
    # Valid state transitions
    STATE_TRANSITIONS = {
        ProvisioningState.NOT_STARTED: [ProvisioningState.ACCEPTED],
        ProvisioningState.ACCEPTED: [ProvisioningState.PROVISIONING, ProvisioningState.FAILED],
        ProvisioningState.PROVISIONING: [ProvisioningState.SUCCEEDED, ProvisioningState.FAILED],
        ProvisioningState.SUCCEEDED: [ProvisioningState.DELETING],
        ProvisioningState.FAILED: [ProvisioningState.DELETING, ProvisioningState.ACCEPTED],
        ProvisioningState.DELETING: [ProvisioningState.DELETED],
        ProvisioningState.DELETED: [],  # Terminal state
    }
    
    def __init__(self, storage: Dict[str, Any]):
        """Initialize handler with state tracking."""
        super().__init__(storage)
        self._state_history = {}  # {resource_id: [state1, state2, ...]}
    
    def create_resource(
        self,
        name: str,
        resource_data: Dict[str, Any],
        resource_type: str,
        scope_context: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """Create resource in 'Accepted' state."""
        resource_data = {
            **resource_data,
            "provisioning_state": ProvisioningState.ACCEPTED.value,
        }
        
        resource_id, config = super().create_resource(
            name, resource_data, resource_type, scope_context
        )
        
        # Track state transition
        self._track_state(resource_id, ProvisioningState.ACCEPTED)
        
        # Automatically advance to Provisioning then Succeeded
        # In production, these would be async tasks
        self._advance_state(resource_id, ProvisioningState.PROVISIONING, scope_context)
        self._advance_state(resource_id, ProvisioningState.SUCCEEDED, scope_context)
        
        return resource_id, self.get_resource(name, scope_context)[1]
    
    def _advance_state(
        self,
        resource_id: str,
        new_state: ProvisioningState,
        scope_context: Dict[str, Any]
    ) -> None:
        """
        Transition resource to new state.
        
        Validates state machine and updates resource.
        """
        # Get current state
        storage_key = None
        current_config = None
        
        for key, value in self.storage.items():
            # Value is either (resource_id, config) or just config
            if isinstance(value, tuple):
                stored_id, stored_config = value
            else:
                stored_config = value
                stored_id = None
            
            if stored_id == resource_id or stored_config.get("id") == resource_id:
                storage_key = key
                current_config = stored_config
                break
        
        if not current_config:
            raise ValueError(f"Resource not found: {resource_id}")
        
        current_state = ProvisioningState(current_config.get("provisioning_state", "NotStarted"))
        
        # Validate state transition
        if new_state not in self.STATE_TRANSITIONS.get(current_state, []):
            raise ValueError(
                f"Invalid state transition: {current_state.value} → {new_state.value}"
            )
        
        # Update state
        current_config["provisioning_state"] = new_state.value
        current_config["modifiedTime"] = datetime.utcnow().isoformat() + "Z"
        current_config["modifiedBy"] = scope_context.get("user_id", "system")
        
        # Track transition
        self._track_state(resource_id, new_state)
    
    def delete_resource(
        self,
        name: str,
        scope_context: Dict[str, Any]
    ) -> bool:
        """Delete resource (transitions through Deleting → Deleted)."""
        result = self.get_resource(name, scope_context)
        if not result:
            return False
        
        resource_id, config = result
        
        # Transition to Deleting
        current_state = ProvisioningState(config.get("provisioning_state", "Succeeded"))
        if current_state != ProvisioningState.DELETED:
            self._advance_state(resource_id, ProvisioningState.DELETING, scope_context)
            self._advance_state(resource_id, ProvisioningState.DELETED, scope_context)
        
        # Actually delete
        return super().delete_resource(name, scope_context)
    
    def _track_state(self, resource_id: str, state: ProvisioningState) -> None:
        """Track state transitions for audit."""
        if resource_id not in self._state_history:
            self._state_history[resource_id] = []
        
        self._state_history[resource_id].append({
            "state": state.value,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
    
    def get_state_history(self, resource_id: str) -> List[Dict[str, str]]:
        """Retrieve state transition history for a resource."""
        return self._state_history.get(resource_id, [])


class ValidatedResourceHandler:
    """
    Mixin: Validates resource data against Pydantic schema before storing.
    
    Prevents invalid data from entering the system. Define SCHEMA_CLASS
    as a Pydantic BaseModel and all resource data will be validated.
    
    Designed to be mixed with other handlers:
        class MyHandler(ValidatedResourceHandler, ScopedResourceHandler):
            SCHEMA_CLASS = MySchema
    
    Example:
        from pydantic import BaseModel, validator
        
        class VMSchema(BaseModel):
            vm_name: str
            size: str
            os_type: str
            
            @validator('vm_name')
            def validate_name(cls, v):
                if not v or len(v) < 3:
                    raise ValueError('VM name must be at least 3 chars')
                return v
        
        class VirtualMachineHandler(ValidatedResourceHandler, ScopedResourceHandler):
            UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION, UniquenessScope.RESOURCE_GROUP]
            RESOURCE_TYPE = "virtualmachines"
            SCHEMA_CLASS = VMSchema
        
        handler = VirtualMachineHandler(storage_dict)
        
        # This works
        handler.create_resource("myvm", {"vm_name": "myvm", "size": "Standard_D2s_v3", "os_type": "Linux"}, ...)
        
        # This raises ValueError: validation error
        handler.create_resource("vm", {"vm_name": "vm", "size": "Invalid", "os_type": "Linux"}, ...)
    """
    
    SCHEMA_CLASS: Optional[Type[BaseModel]] = None
    """Override with Pydantic model to enable validation."""
    
    def create_resource(
        self,
        name: str,
        resource_data: Dict[str, Any],
        resource_type: str,
        scope_context: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """Create resource with validation."""
        validated_data = self._validate_data(resource_data)
        return super().create_resource(name, validated_data, resource_type, scope_context)
    
    def update_resource(
        self,
        name: str,
        resource_data: Dict[str, Any],
        scope_context: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """Update resource with validation."""
        validated_data = self._validate_data(resource_data)
        return super().update_resource(name, validated_data, scope_context)
    
    def _validate_data(self, resource_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate resource data against schema.
        
        Returns validated data (converted by Pydantic).
        Raises ValueError with detailed message if validation fails.
        """
        if not self.SCHEMA_CLASS:
            return resource_data
        
        try:
            # Pydantic validates and converts types
            validated = self.SCHEMA_CLASS(**resource_data)
            return validated.dict()
        except ValidationError as e:
            # Format error message with field names and reasons
            errors = []
            for error in e.errors():
                field = ".".join(str(x) for x in error["loc"])
                msg = error["msg"]
                errors.append(f"{field}: {msg}")
            
            raise ValueError(f"Validation failed: {'; '.join(errors)}")
        except TypeError as e:
            raise ValueError(f"Validation failed: {str(e)}")


__all__ = [
    "ProvisioningState",
    "TimestampedResourceHandler",
    "ProvisioningStateHandler",
    "ValidatedResourceHandler",
]
