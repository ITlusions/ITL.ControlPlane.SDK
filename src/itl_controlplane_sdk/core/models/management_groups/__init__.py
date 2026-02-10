"""Management Group models."""

from itl_controlplane_sdk.core.models.management_groups.properties import ManagementGroupProperties
from itl_controlplane_sdk.core.models.management_groups.requests import CreateManagementGroupRequest
from itl_controlplane_sdk.core.models.management_groups.responses import ManagementGroupResponse

__all__ = [
    "ManagementGroupProperties",
    "CreateManagementGroupRequest",
    "ManagementGroupResponse",
]
