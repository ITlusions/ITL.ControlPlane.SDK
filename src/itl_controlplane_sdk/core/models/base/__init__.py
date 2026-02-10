"""
Base module: HTTP models, enums, constants, and infrastructure models.

Contains all foundational and shared models used across the SDK.
"""

# --- HTTP Models ---
from itl_controlplane_sdk.core.models.base.models import (
    CoreBaseModel,
    CoreRequestBaseModel,
    ResourceMetadata,
    ResourceRequest,
    ResourceResponse,
    ResourceListResponse,
    ErrorResponse,
)

# --- Enumerations ---
from itl_controlplane_sdk.core.models.base.enums import (
    ProvisioningState,
    ResourceState,
    DeploymentState,
)

# --- Constants ---
from itl_controlplane_sdk.core.models.base.constants import (
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
)

# --- Infrastructure Models ---
from itl_controlplane_sdk.core.models.base.infrastructure import (
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

__all__ = [
    # HTTP Models
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
]
