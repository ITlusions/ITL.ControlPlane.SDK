"""Extended Location models."""

from itl_controlplane_sdk.core.models.extended_locations.properties import ExtendedLocationProperties
from itl_controlplane_sdk.core.models.extended_locations.requests import (
    CreateExtendedLocationRequest,
    UpdateExtendedLocationRequest,
)
from itl_controlplane_sdk.core.models.extended_locations.responses import (
    ExtendedLocationResponse,
    PaginatedExtendedLocationList,
    ExtendedLocationErrorResponse,
    ExtendedLocationMetadata,
)

__all__ = [
    "ExtendedLocationProperties",
    "CreateExtendedLocationRequest",
    "UpdateExtendedLocationRequest",
    "ExtendedLocationResponse",
    "PaginatedExtendedLocationList",
    "ExtendedLocationErrorResponse",
    "ExtendedLocationMetadata",
]
