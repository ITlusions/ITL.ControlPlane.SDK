"""
Compatibility module for sync models.

This module provides imports that reference itl_controlplane_sdk.persistence.sync.models.
All actual model definitions are delegated to itl_controlplane_sdk.persistence.data.models.

This is used by neo4j_sync.py and other sync-related code.
"""

# Re-export all SQLAlchemy models from data.models
try:
    from ..data.models import (
        Base,
        ManagementGroupModel,
        SubscriptionModel,
        ResourceGroupModel,
        LocationModel,
        ExtendedLocationModel,
        PolicyModel,
        TagModel,
        DeploymentModel,
        ResourceRelationshipModel,
    )
except ImportError as e:
    # Provide helpful error message if import fails
    raise ImportError(
        f"Failed to import models from itl_controlplane_sdk.persistence.data.models: {e}"
    ) from e

__all__ = [
    "Base",
    "ManagementGroupModel",
    "SubscriptionModel",
    "ResourceGroupModel",
    "LocationModel",
    "ExtendedLocationModel",
    "PolicyModel",
    "TagModel",
    "DeploymentModel",
    "ResourceRelationshipModel",
]
