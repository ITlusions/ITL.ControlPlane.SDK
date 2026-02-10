"""Tag models."""

from itl_controlplane_sdk.core.models.tags.properties import TagValue, TagProperties
from itl_controlplane_sdk.core.models.tags.requests import CreateTagRequest
from itl_controlplane_sdk.core.models.tags.responses import TagResponse

__all__ = [
    "TagValue",
    "TagProperties",
    "CreateTagRequest",
    "TagResponse",
]
