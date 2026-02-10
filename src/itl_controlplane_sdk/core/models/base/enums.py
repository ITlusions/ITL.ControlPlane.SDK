"""
Enumerations for the ITL ControlPlane SDK.
"""
from enum import Enum


class ProvisioningState(Enum):
    """Standard resource provisioning states."""
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    CANCELED = "Canceled"
    CREATING = "Creating"
    UPDATING = "Updating"
    DELETING = "Deleting"


class ResourceState(str, Enum):
    """Possible states for a resource."""
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    DELETED = "Deleted"
    PENDING = "Pending"


class DeploymentState(str, Enum):
    """Possible deployment states."""
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    CANCELED = "Canceled"
