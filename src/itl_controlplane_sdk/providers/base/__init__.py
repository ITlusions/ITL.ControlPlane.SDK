"""
Base classes for resource providers

Provides:
- ResourceProvider: Abstract base class for all providers
- ProviderServer: Base class for standalone provider servers
- BaseResourceService: Reusable service pattern (idempotency, events, tenants, retry)
- HealthStatus: Provider health status representation
- ResourceStatus: Resource operational status representation
"""

from .provider import ResourceProvider, HealthStatus, ResourceStatus
from .server import ProviderServer
from .service import BaseResourceService

__all__ = [
    "ResourceProvider",
    "HealthStatus",
    "ResourceStatus",
    "ProviderServer",
    "BaseResourceService",
]
