"""
Utility functions for providers

Provides:
- Registry: Provider registration and management
- Resource ID utilities: ID generation and parsing
"""

from .registry import ResourceProviderRegistry, resource_registry
from .resource_ids import ResourceIdentity, generate_resource_id, parse_resource_id

__all__ = [
    # Registry
    "ResourceProviderRegistry",
    "resource_registry",
    # Resource ID utilities
    "ResourceIdentity",
    "generate_resource_id",
    "parse_resource_id",
]
