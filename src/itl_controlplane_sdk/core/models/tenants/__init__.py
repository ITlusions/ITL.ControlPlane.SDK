"""Tenant models."""

from itl_controlplane_sdk.core.models.tenants.properties import TenantProperties
from itl_controlplane_sdk.core.models.tenants.requests import CreateTenantRequest
from itl_controlplane_sdk.core.models.tenants.responses import TenantResponse

__all__ = [
    "TenantProperties",
    "CreateTenantRequest",
    "TenantResponse",
]
