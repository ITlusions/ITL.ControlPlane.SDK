"""
Core module: SDK base classes, HTTP models, exceptions, and infrastructure models.

Exports the foundational components used across all resource providers.
"""

from itl_controlplane_sdk.core.models import (
    # Base Models
    CoreBaseModel,
    CoreRequestBaseModel,
    # HTTP Models
    ProvisioningState,
    ResourceMetadata,
    ResourceRequest,
    ResourceResponse,
    ResourceListResponse,
    ErrorResponse,
    # Infrastructure Models
    Tag,
    ResourceGroup,
    ManagementGroup,
    Deployment,
    Subscription,
    Location,
    ExtendedLocation,
    Policy,
    ProviderConfiguration,
    # Resource Group Models
    ResourceGroupProperties,
    CreateResourceGroupRequest,
    ResourceGroupResponse,
    # Management Group Models
    ManagementGroupProperties,
    CreateManagementGroupRequest,
    ManagementGroupResponse,
    # Deployment Models
    DeploymentProperties,
    CreateDeploymentRequest,
    DeploymentResponse,
    # Subscription Models
    SubscriptionProperties,
    CreateSubscriptionRequest,
    SubscriptionResponse,
    # Tag Models
    TagValue,
    TagProperties,
    CreateTagRequest,
    TagResponse,
    # Policy Models
    PolicyRule,
    PolicyProperties,
    CreatePolicyRequest,
    PolicyResponse,
    # Location Models
    LocationProperties,
    CreateLocationRequest,
    LocationResponse,
    # Extended Location Models
    ExtendedLocationProperties,
    CreateExtendedLocationRequest,
    ExtendedLocationResponse,
    # Enums
    ResourceState,
    DeploymentState,
    # Constants
    PROVIDER_NAMESPACE,
    RESOURCE_TYPE_RESOURCE_GROUPS,
    RESOURCE_TYPE_MANAGEMENT_GROUPS,
    RESOURCE_TYPE_DEPLOYMENTS,
    RESOURCE_TYPE_SUBSCRIPTIONS,
    RESOURCE_TYPE_TAGS,
    RESOURCE_TYPE_POLICIES,
    RESOURCE_TYPE_LOCATIONS,
    RESOURCE_TYPE_EXTENDED_LOCATIONS,
    ITL_RESOURCE_TYPES,
    DEFAULT_LOCATIONS,
    EXTENDED_LOCATIONS,
)

from itl_controlplane_sdk.core.exceptions import (
    ResourceProviderError,
    ResourceNotFoundError,
    ResourceConflictError,
    ValidationError,
)

__all__ = [
    # Base Models
    "CoreBaseModel",
    "CoreRequestBaseModel",
    # HTTP Models
    "ProvisioningState",
    "ResourceMetadata",
    "ResourceRequest",
    "ResourceResponse",
    "ResourceListResponse",
    "ErrorResponse",
    # Infrastructure Models
    "Tag",
    "ResourceGroup",
    "ManagementGroup",
    "Deployment",
    "Subscription",
    "Location",
    "ExtendedLocation",
    "Policy",
    "ProviderConfiguration",
    # Resource Group Models
    "ResourceGroupProperties",
    "CreateResourceGroupRequest",
    "ResourceGroupResponse",
    # Management Group Models
    "ManagementGroupProperties",
    "CreateManagementGroupRequest",
    "ManagementGroupResponse",
    # Deployment Models
    "DeploymentProperties",
    "CreateDeploymentRequest",
    "DeploymentResponse",
    # Subscription Models
    "SubscriptionProperties",
    "CreateSubscriptionRequest",
    "SubscriptionResponse",
    # Tag Models
    "TagValue",
    "TagProperties",
    "CreateTagRequest",
    "TagResponse",
    # Policy Models
    "PolicyRule",
    "PolicyProperties",
    "CreatePolicyRequest",
    "PolicyResponse",
    # Location Models
    "LocationProperties",
    "CreateLocationRequest",
    "LocationResponse",
    # Extended Location Models
    "ExtendedLocationProperties",
    "CreateExtendedLocationRequest",
    "ExtendedLocationResponse",
    # Enums
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
    "ITL_RESOURCE_TYPES",
    "DEFAULT_LOCATIONS",
    "EXTENDED_LOCATIONS",
    # Exceptions
    "ResourceProviderError",
    "ResourceNotFoundError",
    "ResourceConflictError",
    "ValidationError",
]

