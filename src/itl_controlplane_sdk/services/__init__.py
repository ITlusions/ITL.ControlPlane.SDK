"""
Services module - Application-layer service patterns

Provides reusable service base classes and utilities for all resource providers:
- Idempotency (prevent duplicate operations)
- Event publishing (event-driven architecture)
- Tenant isolation (multi-tenant safety)
- Error handling and retry queueing
- Transaction safety and state management

Each provider implements provider-specific services that inherit from BaseResourceService:
- TenantService (manage tenants)
- OrganizationService (manage organizations)
- ResourceGroupService (manage resource groups)
- etc.
"""

from .base import BaseResourceService

__all__ = [
    "BaseResourceService",
]
