"""
Core data models for the ITL ControlPlane SDK.

Contains HTTP models, infrastructure models, enums, and constants used
across all resource providers.
"""
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, ConfigDict


# ==================== HTTP MODELS ====================
# Standard request/response structures for API operations

class CoreBaseModel(BaseModel):
    """Base model for all Core API request/response models with shared configuration"""
    model_config = ConfigDict(json_schema_extra={})


class CoreRequestBaseModel(CoreBaseModel):
    """Base model for all Core API request models with shared fields"""
    subscription_id: str = Field(..., description="Subscription ID")
    resource_group: str = Field(..., description="Resource Group")
    provider_namespace: str = Field(default="ITL.Core", description="Provider namespace")
    resource_type: str = Field(..., description="Resource type")
    resource_name: str = Field(..., min_length=1, max_length=260, description="Resource name")
    location: str = Field(..., description="Location")
    body: Dict[str, Any] = Field(default_factory=dict, description="Request body")
    action: Optional[str] = Field(None, description="Action to perform")
    api_version: str = Field(default="2023-01-01", pattern=r"^\d{4}-\d{2}-\d{2}$", description="API version")


class ProvisioningState(Enum):
    """Standard resource provisioning states"""
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    CANCELED = "Canceled"
    CREATING = "Creating"
    UPDATING = "Updating"
    DELETING = "Deleting"


class ResourceMetadata(BaseModel):
    """Standard resource metadata"""
    id: str = Field(..., description="Hierarchical resource ID")
    name: str
    type: str
    location: str
    resource_group: str
    subscription_id: str
    tags: Optional[Dict[str, str]] = None
    created_time: Optional[datetime] = None
    modified_time: Optional[datetime] = None
    resource_guid: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), description="Globally unique identifier")


class ResourceRequest(CoreRequestBaseModel):
    """Standard resource request structure - inherits all fields from CoreRequestBaseModel"""
    pass


class ResourceResponse(CoreBaseModel):
    """Standard resource response structure"""
    id: str = Field(..., description="Hierarchical resource ID (ARM-style)")
    name: str
    type: str
    location: str
    properties: Dict[str, Any]
    tags: Optional[Dict[str, str]] = None
    provisioning_state: ProvisioningState = ProvisioningState.SUCCEEDED
    resource_guid: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), description="Globally unique identifier")


class ResourceListResponse(BaseModel):
    """Response for resource list operations"""
    value: List[ResourceResponse]
    next_link: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: Dict[str, Any]


# ==================== INFRASTRUCTURE MODELS ====================
# Shared across all resource providers

# Constants
PROVIDER_NAMESPACE = "ITL.Core"

RESOURCE_TYPE_RESOURCE_GROUPS = "resourcegroups"
RESOURCE_TYPE_MANAGEMENT_GROUPS = "managementgroups"
RESOURCE_TYPE_DEPLOYMENTS = "deployments"
RESOURCE_TYPE_SUBSCRIPTIONS = "subscriptions"
RESOURCE_TYPE_TAGS = "tags"
RESOURCE_TYPE_POLICIES = "policies"
RESOURCE_TYPE_LOCATIONS = "locations"
RESOURCE_TYPE_EXTENDED_LOCATIONS = "extendedlocations"

ITL_RESOURCE_TYPES = [
    RESOURCE_TYPE_RESOURCE_GROUPS,
    RESOURCE_TYPE_MANAGEMENT_GROUPS,
    RESOURCE_TYPE_DEPLOYMENTS,
    RESOURCE_TYPE_SUBSCRIPTIONS,
    RESOURCE_TYPE_TAGS,
    RESOURCE_TYPE_POLICIES,
    RESOURCE_TYPE_LOCATIONS,
    RESOURCE_TYPE_EXTENDED_LOCATIONS,
]

EXTENDED_LOCATIONS = [
    # CDN Edge Zones for Global Content Distribution (all physically in Europe)
    {"name": "cdn-london", "display_name": "CDN London Edge", "shortname": "CDL", "region": "United Kingdom", "location_type": "EdgeZone"},
    {"name": "cdn-frankfurt", "display_name": "CDN Frankfurt Edge", "shortname": "CDF", "region": "Germany", "location_type": "EdgeZone"},
    {"name": "cdn-paris", "display_name": "CDN Paris Edge", "shortname": "CDP", "region": "France", "location_type": "EdgeZone"},
    {"name": "cdn-amsterdam", "display_name": "CDN Amsterdam Edge", "shortname": "CDA", "region": "Netherlands", "location_type": "EdgeZone"},
    {"name": "cdn-stockholm", "display_name": "CDN Stockholm Edge", "shortname": "CDS", "region": "Sweden", "location_type": "EdgeZone"},
    {"name": "cdn-zurich", "display_name": "CDN Zurich Edge", "shortname": "CDZ", "region": "Switzerland", "location_type": "EdgeZone"},
]

DEFAULT_LOCATIONS = [
    # United States
    {"name": "eastus", "display_name": "East US", "shortname": "EUS", "region": "United States"},
    {"name": "westus", "display_name": "West US", "shortname": "WUS", "region": "United States"},
    {"name": "centralus", "display_name": "Central US", "shortname": "CUS", "region": "United States"},
    # United Kingdom
    {"name": "uksouth", "display_name": "UK South", "shortname": "UKS", "region": "United Kingdom"},
    {"name": "ukwest", "display_name": "UK West", "shortname": "UKW", "region": "United Kingdom"},
    # Europe - Regional
    {"name": "northeurope", "display_name": "North Europe", "shortname": "NOR", "region": "Europe"},
    {"name": "westeurope", "display_name": "West Europe", "shortname": "WES", "region": "Europe"},
    # Europe - Major Cities
    {"name": "germanywestcentral", "display_name": "Germany West Central", "shortname": "GWC", "region": "Germany"},
    {"name": "francecentral", "display_name": "France Central", "shortname": "FRA", "region": "France"},
    {"name": "switzerlandnorth", "display_name": "Switzerland North", "shortname": "SWI", "region": "Switzerland"},
    {"name": "swedencentral", "display_name": "Sweden Central", "shortname": "SWE", "region": "Sweden"},
    {"name": "italynorth", "display_name": "Italy North", "shortname": "ITA", "region": "Italy"},
    {"name": "polandcentral", "display_name": "Poland Central", "shortname": "POL", "region": "Poland"},
    {"name": "amsterdam", "display_name": "Amsterdam", "shortname": "AMS", "region": "Netherlands"},
    {"name": "rotterdam", "display_name": "Rotterdam", "shortname": "RTM", "region": "Netherlands"},
    {"name": "almere", "display_name": "Almere", "shortname": "ALM", "region": "Netherlands"},
    # Asia Pacific
    {"name": "southeastasia", "display_name": "Southeast Asia", "shortname": "SEA", "region": "Asia Pacific"},
    {"name": "eastasia", "display_name": "East Asia", "shortname": "EAS", "region": "Asia Pacific"},
] + EXTENDED_LOCATIONS


# Enums for infrastructure resources
class ResourceState(str, Enum):
    """Possible states for a resource"""
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    DELETED = "Deleted"
    PENDING = "Pending"


class DeploymentState(str, Enum):
    """Possible deployment states"""
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    CANCELED = "Canceled"


# Data Models
@dataclass
class Tag:
    """Resource tag for metadata and organization"""
    key: str
    value: str
    resource_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ResourceGroup:
    """
    Container for organizing related resources.
    
    Similar to AWS resource groups or Azure resource groups.
    """
    name: str
    display_name: Optional[str] = None
    location: str = "eastus"
    description: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    state: ResourceState = ResourceState.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    owner: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ManagementGroup:
    """
    Organizational hierarchy for governance and policy management.
    
    Used to organize resource groups into departments/divisions.
    """
    name: str
    display_name: Optional[str] = None
    parent_id: Optional[str] = None
    description: Optional[str] = None
    policies: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Deployment:
    """
    Infrastructure deployment (template-based infrastructure as code).
    
    Represents an Infrastructure-as-Code deployment in a resource group.
    """
    name: str
    template: Dict[str, Any]
    parameters: Dict[str, Any] = field(default_factory=dict)
    state: DeploymentState = DeploymentState.RUNNING
    resource_group_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    error_details: Optional[str] = None


@dataclass
class Subscription:
    """
    Billing and access boundary.
    
    Used for organizing billing, access control, and resource management.
    """
    name: str
    subscription_id: Optional[str] = None
    resource_group_id: Optional[str] = None
    billing_email: Optional[str] = None
    state: ResourceState = ResourceState.ACTIVE
    quota_cores: int = 100
    quota_storage_gb: int = 1000
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    owner: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Location:
    """
    Geographic region or availability zone.
    
    Represents a physical or logical datacenter location.
    """
    name: str
    display_name: str
    region: str
    availability_zones: List[str] = field(default_factory=lambda: ["1", "2", "3"])
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtendedLocation:
    """
    Custom on-premises or edge location.
    
    Extends default cloud locations with on-prem or edge resources.
    """
    name: str
    display_name: str
    location_type: str
    parent_location: Optional[str] = None
    connection_string: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Policy:
    """
    Governance policy for compliance and controls.
    
    Enforces rules on resources (encryption, tagging, location restrictions, etc.).
    """
    name: str
    policy_type: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    rules: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    scope: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderConfiguration:
    """Configuration for Resource Providers"""
    subscription_id: Optional[str] = None
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    default_location: str = "eastus"
    environment: str = "azure"
    properties: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProviderConfiguration":
        """Create configuration from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==================== PYDANTIC MODELS FOR OPENAPI ====================
# Resource-specific request and response models for API documentation

# Resource Groups
class ResourceGroupProperties(BaseModel):
    """Resource Group properties"""
    provisioning_state: Optional[str] = Field("Succeeded", description="Provisioning state")
    managed: Optional[bool] = Field(False, description="Whether the resource group is managed")
    environment: Optional[str] = Field(None, description="Environment (dev, test, prod)")


class CreateResourceGroupRequest(ResourceRequest):
    """Create Resource Group request"""
    tags: Optional[Dict[str, str]] = Field(None, description="Resource tags")
    properties: Optional[ResourceGroupProperties] = Field(None, description="Resource group properties")
    
    class Config:
        json_schema_extra = {
            "example": {
                "subscription_id": "sub-12345",
                "resource_group": "prod-rg",
                "provider_namespace": "ITL.Core",
                "resource_type": "resourcegroups",
                "resource_name": "prod-rg",
                "location": "westeurope",
                "body": {"managed": True},
                "tags": {"env": "production"}
            }
        }


class ResourceGroupResponse(ResourceResponse):
    """Resource Group response"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "/subscriptions/sub-12345/resourceGroups/prod-rg",
            "name": "prod-rg",
            "type": "ITL.Core/resourcegroups",
            "location": "westeurope",
            "properties": {"provisioning_state": "Succeeded", "managed": True},
            "tags": {"env": "production"},
            "provisioning_state": "Succeeded",
            "resource_guid": "550e8400-e29b-41d4-a716-446655440001"
        }
    })


# Management Groups
class ManagementGroupProperties(BaseModel):
    """Management Group properties"""
    tenant_id: str = Field(..., description="Azure Tenant ID")
    display_name: Optional[str] = Field(None, description="Display name for the management group")
    parent_id: Optional[str] = Field(None, description="Parent management group ID")
    child_count: int = Field(0, description="Number of child management groups")


class CreateManagementGroupRequest(ResourceRequest):
    """Create Management Group request"""
    tags: Optional[Dict[str, str]] = Field(None, description="Management group tags")
    properties: Optional[ManagementGroupProperties] = Field(None, description="Management group properties")


class ManagementGroupResponse(ResourceResponse):
    """Management Group response"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "/subscriptions/sub-12345/providers/ITL.Core/managementgroups/org-hierarchy",
            "name": "org-hierarchy",
            "type": "ITL.Core/managementgroups",
            "location": "global",
            "properties": {
                "tenant_id": "00000000-0000-0000-0000-000000000000",
                "display_name": "Organization Hierarchy",
                "parent_id": None,
                "child_count": 3
            },
            "tags": {
                "org": "contoso",
                "cost-center": "engineering",
                "environment": "production"
            },
            "provisioning_state": "Succeeded",
            "resource_guid": "550e8400-e29b-41d4-a716-446655440000"
        }
    })


# Deployments
class DeploymentProperties(BaseModel):
    """Deployment properties"""
    provisioning_state: str = Field("InProgress", description="Provisioning state (InProgress, Succeeded, Failed)")
    template: Optional[Dict[str, Any]] = Field(None, description="ARM template")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Template parameters")
    output: Optional[Dict[str, Any]] = Field(None, description="Deployment output")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracking")


class CreateDeploymentRequest(ResourceRequest):
    """Create Deployment request"""
    tags: Optional[Dict[str, str]] = Field(None, description="Deployment tags")
    properties: DeploymentProperties = Field(..., description="Deployment properties")


class DeploymentResponse(ResourceResponse):
    """Deployment response"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "/subscriptions/sub-12345/resourceGroups/prod-rg/providers/ITL.Core/deployments/app-001",
            "name": "app-deployment-001",
            "type": "ITL.Core/deployments",
            "location": "westeurope",
            "properties": {"provisioning_state": "Succeeded", "correlation_id": "550e8400-e29b"},
            "provisioning_state": "Succeeded",
            "resource_guid": "550e8400-e29b-41d4-a716-446655440002"
        }
    })


# Subscriptions
class SubscriptionProperties(BaseModel):
    """Subscription properties"""
    display_name: str = Field(..., description="Display name")
    state: str = Field("Enabled", description="Subscription state (Enabled, Warned, PastDue, Disabled)")
    subscription_policies: Optional[Dict[str, Any]] = Field(None, description="Subscription policies")
    quota: Optional[Dict[str, Any]] = Field(None, description="Quota information")


class CreateSubscriptionRequest(CoreBaseModel):
    """Create Subscription request - subscription_id is auto-generated by the server"""
    resource_name: str = Field(..., min_length=1, max_length=260, description="Resource name")
    subscription_id: Optional[str] = Field(None, description="Subscription ID (optional, server will generate if not provided)")
    resource_group: str = Field(..., description="Resource Group")
    resource_type: str = Field(..., description="Resource type")
    location: str = Field(..., description="Location")
    display_name: str = Field(..., description="Display name for the subscription")
    state: Optional[str] = Field("Enabled", description="Subscription state")
    tags: Optional[Dict[str, str]] = Field(None, description="Subscription tags")
    properties: Optional[SubscriptionProperties] = Field(None, description="Subscription properties")


class SubscriptionResponse(ResourceResponse):
    """Subscription response"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "/subscriptions/sub-12345",
            "name": "sub-prod-eastus",
            "type": "ITL.Core/subscriptions",
            "location": "global",
            "properties": {"display_name": "Production - East US", "state": "Enabled"},
            "provisioning_state": "Succeeded",
            "resource_guid": "550e8400-e29b-41d4-a716-446655440003"
        }
    })


# Tags
class TagValue(BaseModel):
    """Tag value entry"""
    key: str = Field(..., description="Tag key")
    value: str = Field(..., description="Tag value")


class TagProperties(BaseModel):
    """Tag properties"""
    count: int = Field(0, description="Number of resources with this tag")
    values: List[TagValue] = Field(default_factory=list, description="Tag values")


class CreateTagRequest(ResourceRequest):
    """Create Tag request"""
    values: Optional[List[TagValue]] = Field(None, description="Tag values")
    properties: Optional[TagProperties] = Field(None, description="Tag properties")


class TagResponse(ResourceResponse):
    """Tag response"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "/subscriptions/sub-12345/providers/ITL.Core/tags/environment",
            "name": "environment",
            "type": "ITL.Core/tags",
            "location": "global",
            "properties": {"count": 125, "values": [{"key": "environment", "value": "production"}]},
            "provisioning_state": "Succeeded",
            "resource_guid": "550e8400-e29b-41d4-a716-446655440004"
        }
    })


# Policies
class PolicyRule(BaseModel):
    """Policy rule definition"""
    if_: Optional[Dict[str, Any]] = Field(None, description="Condition", alias="if")
    then: Optional[Dict[str, Any]] = Field(None, description="Action to take")


class PolicyProperties(BaseModel):
    """Policy properties"""
    display_name: Optional[str] = Field(None, description="Display name")
    policy_type: str = Field(..., description="Policy type (BuiltIn, Custom)")
    mode: str = Field("Indexed", description="Policy mode (Indexed, All)")
    description: Optional[str] = Field(None, description="Policy description")
    rules: Optional[PolicyRule] = Field(None, description="Policy rules")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Policy parameters")


class CreatePolicyRequest(ResourceRequest):
    """Create Policy request"""
    tags: Optional[Dict[str, str]] = Field(None, description="Policy tags")
    properties: PolicyProperties = Field(..., description="Policy properties")


class PolicyResponse(ResourceResponse):
    """Policy response"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "/subscriptions/sub-12345/providers/ITL.Core/policies/require-tags",
            "name": "require-tags-policy",
            "type": "ITL.Core/policies",
            "location": "global",
            "properties": {"display_name": "Require Tags", "policy_type": "Custom", "mode": "Indexed"},
            "provisioning_state": "Succeeded",
            "resource_guid": "550e8400-e29b-41d4-a716-446655440005"
        }
    })


# Locations
class LocationProperties(BaseModel):
    """Location properties"""
    display_name: str = Field(..., description="Display name for the region")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")
    paired_region: Optional[str] = Field(None, description="Paired region for disaster recovery")
    physical_location: Optional[str] = Field(None, description="Physical data center location")


class CreateLocationRequest(ResourceRequest):
    """Create Location request"""
    display_name: Optional[str] = Field(None, description="Display name")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")
    paired_region: Optional[str] = Field(None, description="Paired region")
    properties: Optional[LocationProperties] = Field(None, description="Location properties")


class LocationResponse(ResourceResponse):
    """Location response"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "/subscriptions/sub-12345/providers/ITL.Core/locations/westeurope",
            "name": "westeurope",
            "type": "ITL.Core/locations",
            "location": "global",
            "properties": {"display_name": "West Europe", "latitude": 50.93, "longitude": 6.97, "paired_region": "northeurope"},
            "provisioning_state": "Succeeded",
            "resource_guid": "550e8400-e29b-41d4-a716-446655440006"
        }
    })


# Extended Locations
class ExtendedLocationProperties(BaseModel):
    """Extended Location properties"""
    display_name: str = Field(..., description="Display name for the extended location")
    location_type: str = Field(..., description="Type of extended location (e.g., 'EdgeZone', 'CustomLocation')")
    parent_location: Optional[str] = Field(None, description="Parent location")
    capabilities: Optional[List[str]] = Field(None, description="Available capabilities")
    status: str = Field("Available", description="Status (Available, Unavailable)")


class CreateExtendedLocationRequest(ResourceRequest):
    """Create Extended Location request"""
    location_type: str = Field(..., description="Type of extended location")
    parent_location: Optional[str] = Field(None, description="Parent location")
    display_name: Optional[str] = Field(None, description="Display name")
    capabilities: Optional[List[str]] = Field(None, description="Capabilities")
    properties: Optional[ExtendedLocationProperties] = Field(None, description="Extended location properties")


class ExtendedLocationResponse(ResourceResponse):
    """Extended Location response"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "/subscriptions/sub-12345/providers/ITL.Core/extendedlocations/edge-dc-01",
            "name": "edge-dc-01",
            "type": "ITL.Core/extendedlocations",
            "location": "westeurope",
            "properties": {"display_name": "Edge Zone Amsterdam", "location_type": "EdgeZone", "capabilities": ["vm", "storage"]},
            "provisioning_state": "Succeeded",
            "resource_guid": "550e8400-e29b-41d4-a716-446655440007"
        }
    })


