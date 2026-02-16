"""
ITL ControlPlane SDK - Modular Architecture

The SDK is now organized into two main modules:
1. Core Module - Base infrastructure, models, exceptions
2. Identity Module - Pluggable identity provider framework
"""

SDK Structure:
==============

itl_controlplane_sdk/
│
├── core/                          # Core module - Base functionality
│   ├── __init__.py               # Exports all core components
│   ├── models.py                 # HTTP models, infrastructure models, constants
│   └── exceptions.py             # Standard exception hierarchy
│
├── identity/                      # Identity module - Provider framework
│   ├── __init__.py               # Factory and provider exports
│   ├── identity_provider_base.py # IdentityProvider ABC
│   ├── identity_provider_factory.py # Factory pattern
│   └── exceptions.py             # Identity-specific exceptions
│
├── fastapi/                       # HTTP routing support
│   ├── __init__.py
│   ├── app_factory.py
│   ├── config.py
│   ├── middleware/
│   │   ├── error_handling.py
│   │   └── logging.py
│   └── routes/
│       └── metadata.py
│
├── __init__.py                    # Main SDK entry point (unified exports)
├── resource_provider.py           # ResourceProvider ABC
├── registry.py                    # ResourceProviderRegistry
└── resource_ids.py               # Resource ID utilities


Core Module Exports:
====================

HTTP Models:
  - ProvisioningState
  - ResourceMetadata
  - ResourceRequest
  - ResourceResponse
  - ResourceListResponse
  - ErrorResponse

Infrastructure Models (8):
  - Tag
  - ResourceGroup
  - ManagementGroup
  - Deployment
  - Subscription
  - Location
  - ExtendedLocation
  - Policy
  - ProviderConfiguration (config model)

Enums (2):
  - ResourceState (Active, Inactive, Deleted, Pending)
  - DeploymentState (Running, Succeeded, Failed, Canceled)

Exceptions (4):
  - ResourceProviderError (base)
  - ResourceNotFoundError
  - ResourceConflictError
  - ValidationError

Constants:
  - PROVIDER_NAMESPACE
  - 8 RESOURCE_TYPE_* constants
  - ITL_RESOURCE_TYPES (list of all types)
  - DEFAULT_LOCATIONS (8 default locations)


Identity Module Exports:
=========================

Interfaces:
  - IdentityProvider (ABC)

Factory:
  - IdentityProviderFactory
  - get_factory()
  - register_provider()
  - create_provider()
  - get_or_create_provider()

Exceptions:
  - IdentityProviderError (base)
  - IdentityProviderNotFoundError
  - InvalidCredentialsError
  - RealmAlreadyExistsError
  - ClientAlreadyExistsError


Main SDK Exports:
=================

From core:
  - All HTTP models, infrastructure models, constants, exceptions

From identity:
  - IdentityProvider, IdentityProviderFactory, factory functions

Base classes:
  - ResourceProvider
  - ResourceProviderRegistry

Utilities:
  - ResourceIdentity
  - generate_resource_id()
  - parse_resource_id()


Usage Examples:
===============

# Import from core
from itl_controlplane_sdk.core import (
    ResourceRequest,
    ResourceResponse,
    ResourceGroup,
    ResourceProviderError,
)

# Or import from main SDK
from itl_controlplane_sdk import (
    ResourceRequest,
    ResourceResponse,
    ResourceGroup,
)

# Identity provider framework
from itl_controlplane_sdk.identity import (
    get_factory as get_identity_factory,
    register_provider,
)
from keycloak_identity_provider import KeycloakIdentityProvider

# Register and use
register_provider("keycloak", KeycloakIdentityProvider)
factory = get_identity_factory()
provider = factory.create("keycloak", config)

# Resource provider framework
from itl_controlplane_sdk import ResourceProvider, ResourceProviderRegistry

class MyProvider(ResourceProvider):
    async def create_or_update_resource(self, request):
        ...

registry = ResourceProviderRegistry()
registry.register_provider("my-provider", MyProvider("namespace"))


Benefits of Modular Architecture:
==================================

✓ Separation of Concerns
  - Core: Base models and exceptions
  - Identity: Pluggable identity providers
  
✓ Clear Dependencies
  - Core has no external dependencies (except pydantic)
  - Identity imports from core
  - Main SDK imports from both
  
✓ Easier Testing
  - Test core without identity
  - Test identity with mock providers
  - Test main SDK with all components
  
✓ Maintainability
  - Each module has single responsibility
  - Changes localized to relevant module
  - Easier to understand and extend
  
✓ Scalability
  - Easy to add new identity providers
  - Can add new modules (e.g., storage, compute) without affecting existing
  - Clear import patterns for all providers
