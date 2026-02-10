"""
Core data models for the ITL ControlPlane SDK.

This package contains HTTP models, infrastructure models, enums, and constants
used across all resource providers.

All symbols are re-exported here for backward compatibility — consumers can
continue to use::

    from itl_controlplane_sdk.core.models import ResourceResponse

Or import from specific sub-modules for clarity::

    from itl_controlplane_sdk.core.models.base import ResourceResponse
    from itl_controlplane_sdk.core.models.enums import ProvisioningState
"""

# --- Base module (shared models, enums, constants, infrastructure) --------
from itl_controlplane_sdk.core.models.base import (
    CoreBaseModel,
    CoreRequestBaseModel,
    ResourceMetadata,
    ResourceRequest,
    ResourceResponse,
    ResourceListResponse,
    ErrorResponse,
    ProvisioningState,
    ResourceState,
    DeploymentState,
    PROVIDER_NAMESPACE,
    RESOURCE_TYPE_RESOURCE_GROUPS,
    RESOURCE_TYPE_MANAGEMENT_GROUPS,
    RESOURCE_TYPE_DEPLOYMENTS,
    RESOURCE_TYPE_SUBSCRIPTIONS,
    RESOURCE_TYPE_TAGS,
    RESOURCE_TYPE_POLICIES,
    RESOURCE_TYPE_LOCATIONS,
    RESOURCE_TYPE_EXTENDED_LOCATIONS,
    RESOURCE_TYPE_TENANTS,
    DEFAULT_TENANT_ID,
    ITL_RESOURCE_TYPES,
    EXTENDED_LOCATIONS,
    DEFAULT_LOCATIONS,
    Tag,
    ResourceGroup,
    ManagementGroup,
    Deployment,
    Subscription,
    Location,
    ExtendedLocation,
    Policy,
    ProviderConfiguration,
)

# --- Resource Group API models ---------------------------------------------
from itl_controlplane_sdk.core.models.resource_groups import (
    ResourceGroupProperties,
    CreateResourceGroupRequest,
    ResourceGroupResponse,
)

# --- Management Group API models -------------------------------------------
from itl_controlplane_sdk.core.models.management_groups import (
    ManagementGroupProperties,
    CreateManagementGroupRequest,
    ManagementGroupResponse,
)

# --- Deployment API models -------------------------------------------------
from itl_controlplane_sdk.core.models.deployments import (
    DeploymentProperties,
    CreateDeploymentRequest,
    DeploymentResponse,
)

# --- Subscription API models -----------------------------------------------
from itl_controlplane_sdk.core.models.subscriptions import (
    SubscriptionProperties,
    CreateSubscriptionRequest,
    SubscriptionResponse,
)

# --- Tag API models --------------------------------------------------------
from itl_controlplane_sdk.core.models.tags import (
    TagValue,
    TagProperties,
    CreateTagRequest,
    TagResponse,
)

# --- Policy API models -----------------------------------------------------
from itl_controlplane_sdk.core.models.policies import (
    PolicyRule,
    PolicyProperties,
    CreatePolicyRequest,
    PolicyResponse,
)

# --- Location API models ---------------------------------------------------
from itl_controlplane_sdk.core.models.locations import (
    LocationProperties,
    CreateLocationRequest,
    LocationResponse,
)

# --- Extended Location API models ------------------------------------------
from itl_controlplane_sdk.core.models.extended_locations import (
    ExtendedLocationProperties,
    CreateExtendedLocationRequest,
    ExtendedLocationResponse,
)

# --- Tenant API models -----------------------------------------------------
from itl_controlplane_sdk.core.models.tenants import (
    TenantProperties,
    CreateTenantRequest,
    TenantResponse,
)

__all__ = [
    # Base Models
    "CoreBaseModel",
    "CoreRequestBaseModel",
    "ResourceMetadata",
    "ResourceRequest",
    "ResourceResponse",
    "ResourceListResponse",
    "ErrorResponse",
    # Enums
    "ProvisioningState",
    "ResourceState",
    "DeploymentState",
    # Constants
    "PROVIDER_NAMESPACE",
    "RESOURCE_TYPE_RESOURCE_GROUPS",
    "RESOURCE_TYPE_MANAGEMENT_GROUPS",
    "RESOURCE_TYPE_DEPLOYMENTS",
    "RESOURCE_TYPE_SUBSCRIPTIONS",
    "RESOURCE_TYPE_TAGS",
    "RESOURCE_TYPE_POLICIES",
    "RESOURCE_TYPE_LOCATIONS",
    "RESOURCE_TYPE_EXTENDED_LOCATIONS",
    "RESOURCE_TYPE_TENANTS",
    "DEFAULT_TENANT_ID",
    "ITL_RESOURCE_TYPES",
    "EXTENDED_LOCATIONS",
    "DEFAULT_LOCATIONS",
    # Infrastructure dataclasses
    "Tag",
    "ResourceGroup",
    "ManagementGroup",
    "Deployment",
    "Subscription",
    "Location",
    "ExtendedLocation",
    "Policy",
    "ProviderConfiguration",
    # Resource Group API models
    "ResourceGroupProperties",
    "CreateResourceGroupRequest",
    "ResourceGroupResponse",
    # Management Group API models
    "ManagementGroupProperties",
    "CreateManagementGroupRequest",
    "ManagementGroupResponse",
    # Deployment API models
    "DeploymentProperties",
    "CreateDeploymentRequest",
    "DeploymentResponse",
    # Subscription API models
    "SubscriptionProperties",
    "CreateSubscriptionRequest",
    "SubscriptionResponse",
    # Tag API models
    "TagValue",
    "TagProperties",
    "CreateTagRequest",
    "TagResponse",
    # Policy API models
    "PolicyRule",
    "PolicyProperties",
    "CreatePolicyRequest",
    "PolicyResponse",
    # Location API models
    "LocationProperties",
    "CreateLocationRequest",
    "LocationResponse",
    # Extended Location API models
    "ExtendedLocationProperties",
    "CreateExtendedLocationRequest",
    "ExtendedLocationResponse",
    # Tenant API models
    "TenantProperties",
    "CreateTenantRequest",
    "TenantResponse",
]
