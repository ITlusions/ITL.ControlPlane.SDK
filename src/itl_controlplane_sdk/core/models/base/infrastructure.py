"""
Infrastructure dataclass models for the ITL ControlPlane SDK.

Domain models representing core infrastructure resources:
Tag, ResourceGroup, ManagementGroup, Deployment, Subscription,
Location, ExtendedLocation, Policy, and ProviderConfiguration.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

from itl_controlplane_sdk.core.models.base.enums import ResourceState, DeploymentState


@dataclass
class Tag:
    """Resource tag for metadata and organization."""
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
    """Configuration for Resource Providers."""
    subscription_id: Optional[str] = None
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    default_location: str = "eastus"
    environment: str = "azure"
    properties: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProviderConfiguration":
        """Create configuration from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
