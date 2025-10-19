"""
ITL ControlPlane SDK - Core Framework

This package provides the core framework for building resource providers
and managing cloud resources through a unified interface.
"""

__version__ = "1.0.0"

# Core SDK components
from .models import (
    ResourceRequest,
    ResourceResponse, 
    ResourceListResponse,
    ProvisioningState
)
from .resource_provider import ResourceProvider
from .registry import ResourceProviderRegistry, resource_registry

# Convenience exports
__all__ = [
    'ResourceRequest',
    'ResourceResponse',
    'ResourceListResponse', 
    'ProvisioningState',
    'ResourceProvider',
    'ResourceProviderRegistry',
    'resource_registry'
]
