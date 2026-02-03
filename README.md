# ITL ControlPlane SDK

The core SDK framework for ITL ControlPlane, providing a complete resource management platform with identity integration, scoped resources, and production-ready handler patterns.

## Features

### Core Framework
- **Resource Provider Registry**: Thread-safe framework for registering and managing resource providers
- **Resource Provider Base Classes**: Abstract base classes for implementing custom resource providers  
- **Data Models**: Comprehensive Pydantic models for resources, requests, and responses
- **Clean Architecture**: Modular design with minimal dependencies and clear separation of concerns
- **Provider Isolation**: Support for containerized and standalone provider deployments
- **Async Support**: Built-in support for asynchronous resource operations
- **Type Safety**: Full type hints and validation using Pydantic models

### Advanced Resource Management
- **Scoped Resource Handlers**: Configurable scope-based uniqueness (subscription, resource group, management group, global)
- **Big 3 Handler Mixins**: Production-ready patterns for timestamps, provisioning states, and validation
- **Automatic Duplicate Detection**: Scope-aware duplicate checking with clear error messages
- **Resource ID Generation**: Hierarchical path-based IDs with automatic GUID generation
- **Backward Compatibility**: Seamless migration from non-scoped to scoped storage

### Identity & Multi-Tenancy
- **Identity Provider Framework**: Pluggable identity provider architecture (Keycloak, Azure AD, etc.)
- **Tenant Management**: Full tenant lifecycle with organizations, domains, and admin users
- **Organization Support**: Multi-organization tenants with custom domain support
- **Identity Provider Factory**: Centralized provider registration and instantiation

### FastAPI Integration
- **FastAPI Module**: Optional FastAPI integration with app factory pattern
- **Error Handling Middleware**: Automatic exception mapping to HTTP responses
- **Logging Middleware**: Request/response logging with correlation IDs
- **Health Check Routes**: Built-in health and readiness endpoints

### Infrastructure Resources
- **ITL Locations**: Dynamic location management with region metadata
- **Resource Groups**: Azure-style resource group management with provisioning states
- **Management Groups**: Hierarchical organization structure
- **Deployments**: ARM-style deployment tracking and management
- **Subscriptions**: Multi-subscription support with quota management
- **Tags & Policies**: Resource tagging and policy enforcement

## Installation

```bash
pip install itl-controlplane-sdk
```

For FastAPI integration:
```bash
pip install itl-controlplane-sdk[fastapi]
```

For development:
```bash
git clone https://github.com/ITlusions/ITL.ControlPlane.SDK.git
cd ITL.ControlPlane.SDK
pip install -e ".[dev]"
```

## Quick Start

### Basic Resource Provider

```python
from itl_controlplane_sdk import (
    ResourceProvider,
    ResourceRequest,
    ResourceResponse,
    ProvisioningState,
    generate_resource_id
)

class MyResourceProvider(ResourceProvider):
    def __init__(self):
        super().__init__("MyProvider")
        self.supported_resource_types = ["myresourcetype"]
    
    async def create_or_update_resource(self, request: ResourceRequest) -> ResourceResponse:
        resource_id = generate_resource_id(
            subscription_id=request.subscription_id,
            resource_group=request.resource_group,
            provider_namespace=request.provider_namespace,
            resource_type=request.resource_type,
            resource_name=request.resource_name
        )
        
        return ResourceResponse(
            id=resource_id,
            name=request.resource_name,
            type=f"{request.provider_namespace}/{request.resource_type}",
            location=request.location,
            properties=request.body.get("properties", {}),
            provisioning_state=ProvisioningState.SUCCEEDED
        )
```

### Scoped Resource Handler with Big 3 Mixins

```python
from itl_controlplane_sdk.providers import (
    ScopedResourceHandler,
    TimestampedResourceHandler,
    ProvisioningStateHandler,
    ValidatedResourceHandler,
    UniquenessScope
)

class MyResourceHandler(
    TimestampedResourceHandler,      # Adds createdTime, modifiedTime
    ProvisioningStateHandler,         # Manages provisioning state lifecycle
    ValidatedResourceHandler,         # Schema validation with Pydantic
    ScopedResourceHandler             # Must be last in MRO
):
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION]
    RESOURCE_TYPE = "myresources"
    
    # Define validation schema
    class ConfigSchema(BaseModel):
        name: str
        enabled: bool = True
        replicas: int = Field(ge=1, le=100)

# Usage - automatic timestamps, state transitions, and validation
handler = MyResourceHandler(storage)
resource_id, config = handler.create_resource(
    name="myresource",
    data={"enabled": True, "replicas": 3},
    resource_type="myresources",
    scope_context={
        "subscription_id": "sub-123",
        "resource_group": "rg-prod"
    }
)
# config includes: createdTime, modifiedTime, provisioning_state='Succeeded'
```

### Identity Provider Integration

```python
from itl_controlplane_sdk.identity import (
    IdentityProviderFactory,
    get_identity_factory,
    Tenant,
    Organization
)

# Register and use identity providers
factory = get_identity_factory()
keycloak_provider = factory.get_provider("keycloak", config={
    "server_url": "https://keycloak.example.com",
    "admin_realm": "master"
})

# Create tenant with organizations
tenant = await keycloak_provider.create_tenant(
    tenant_id="tenant-001",
    spec=TenantSpec(
        display_name="Acme Corp",
        admin_email="admin@acme.com"
    )
)

# Create organization within tenant
org = await keycloak_provider.create_organization(
    tenant_id="tenant-001",
    organization_id="org-sales",
    spec=OrganizationSpec(
        display_name="Sales Department",
        domains=["sales.acme.com"]
    )
)
```

### FastAPI Application

```python
from itl_controlplane_sdk.fastapi import create_app
from itl_controlplane_sdk import resource_registry

# Register your providers
resource_registry.register_provider("myprovider", MyResourceProvider())

# Create FastAPI app with middleware and health checks
app = create_app(
    title="My Control Plane API",
    version="1.0.0",
    include_health=True,
    include_error_middleware=True,
    include_logging_middleware=True
)

# Add custom routes
@app.get("/custom")
async def custom_endpoint():
    return {"message": "Hello from custom endpoint"}
```

## Project Structure

```
ITL.ControlPlane.SDK/
├── src/
│   └── itl_controlplane_sdk/           # Core SDK package
│       ├── __init__.py                 # Package exports
│       ├── core/                       # Core models and exceptions
│       │   ├── models.py               # Resource request/response models
│       │   └── exceptions.py           # SDK exceptions
│       ├── providers/                  # Resource provider framework
│       │   ├── base.py                 # ResourceProvider base class
│       │   ├── registry.py             # Provider registry
│       │   ├── resource_ids.py         # Resource ID utilities
│       │   ├── scoped_resources.py     # Scoped resource handler base
│       │   ├── resource_handlers.py    # Big 3 handler mixins
│       │   ├── resource_group_handler.py  # Resource group implementation
│       │   ├── locations.py            # Location management
│       │   └── itl_locations.py        # ITL location handler
│       ├── identity/                   # Identity provider framework
│       │   ├── identity_provider_base.py  # Base identity provider
│       │   ├── identity_provider_factory.py  # Provider factory
│       │   ├── tenant.py               # Tenant models
│       │   ├── organization.py         # Organization models
│       │   └── exceptions.py           # Identity exceptions
│       ├── fastapi/                    # FastAPI integration (optional)
│       │   ├── app_factory.py          # App factory pattern
│       │   ├── config.py               # FastAPI configuration
│       │   ├── middleware/             # Custom middleware
│       │   │   ├── error_handling.py   # Error handling middleware
│       │   │   └── logging.py          # Logging middleware
│       │   └── routes/                 # Built-in routes
│       │       └── health.py           # Health check endpoints
│       └── services/                   # Application layer services
│           └── base.py                 # Base service patterns
├── examples/                           # Usage examples
│   ├── quickstart.py                   # Getting started example
│   ├── scoped_resource_examples.py     # Scoped resource patterns
│   ├── big_3_examples.py               # Handler mixin examples
│   └── test_itl_locations.py           # Location management example
├── tests/                              # Test suite
│   ├── test_models.py                  # Model validation tests
│   ├── test_resource_provider.py       # Provider tests
│   └── test_resource_handlers.py       # Handler tests
├── docs/                               # Documentation
│   ├── ARCHITECTURE.md                 # Architecture overview
│   ├── AUTOMATED_VERSIONING.md         # Version management
│   ├── PIPELINE_SETUP.md               # CI/CD setup
│   ├── RESOURCE_ID_STRATEGY.md         # Resource ID design
│   ├── SCOPED_RESOURCE_HANDLER.md      # Scoped handler guide
│   ├── FASTAPI_MODULE_COMPLETE.md      # FastAPI integration guide
│   └── MODULAR_ARCHITECTURE.md         # Module design patterns
├── .github/                            # CI/CD workflows
│   ├── workflows/                      # GitHub Actions
│   │   ├── ci.yml                      # Continuous integration
│   │   ├── build-publish.yml           # PyPI publishing
│   │   └── provider-testing.yml        # Provider validation
│   └── PYPI_SETUP.md                   # PyPI configuration guide
├── ARCHITECTURE_SUMMARY.md             # Quick architecture reference
├── BIG_3_SUMMARY.md                    # Handler mixin summary
├── BIG_3_COMPLETE_SUMMARY.md           # Detailed handler guide
├── SCOPED_RESOURCE_HANDLER_COMPLETE.md # Complete scoped handler docs
├── QUICK_REFERENCE.md                  # Quick API reference
├── QUICK_REFERENCE_BIG_3.md            # Handler mixin quick ref
├── pyproject.toml                      # Package configuration
└── README.md                           # This file
```

## Architecture

The SDK follows a clean, modular architecture with clear separation of concerns:

### Core Layer
- **Models**: Pydantic-based data models for requests, responses, and resource metadata with full validation
- **Exceptions**: Hierarchical exception types for error handling
- **Constants**: Shared constants for resource types, locations, and provider namespaces

### Provider Layer
- **Registry**: Thread-safe centralized registration and management of resource providers
- **Base Classes**: Abstract base classes (`ResourceProvider`, `ScopedResourceHandler`) for implementations
- **Resource IDs**: Utilities for generating and parsing hierarchical resource IDs
- **Scoped Resources**: Configurable scope-based uniqueness and duplicate detection
- **Handler Mixins**: Production-ready patterns (timestamps, provisioning states, validation)

### Identity Layer
- **Identity Providers**: Pluggable identity provider framework
- **Factory Pattern**: Centralized provider registration and instantiation
- **Tenant Management**: Multi-tenant support with organization hierarchies
- **Domain Management**: Custom domain support and verification

### FastAPI Layer (Optional)
- **App Factory**: FastAPI application factory with configurable middleware
- **Middleware**: Error handling, logging, and request correlation
- **Routes**: Built-in health check and metadata endpoints
- **Configuration**: Environment-based configuration management

### Service Layer
- **Base Services**: Application-layer patterns for business logic
- **Resource Services**: High-level resource management APIs

### Design Principles
- **Separation of Concerns**: Clear boundaries between layers
- **Dependency Inversion**: Core SDK has no dependencies on FastAPI or identity providers
- **Type Safety**: Comprehensive type hints and runtime validation
- **Async-First**: Native async/await support throughout
- **Extensibility**: Easy to extend with custom providers and handlers
- **Backward Compatibility**: Seamless migration path for existing implementations

## Related Components

This SDK is part of the ITL ControlPlane ecosystem. Other components are in independent repositories:

### Core Infrastructure
- **ITL.ControlPlane.API**: REST API layer with ARM-compatible endpoints
- **ITL.ControlPlane.GraphDB**: Graph database for metadata storage and relationships
- **ITL.ControlPlane.CLI**: Command-line interface for resource management

### Resource Providers
- **ITL.ControlPlane.ResourceProvider.Core**: Core Azure-style resources (subscriptions, resource groups, deployments)
- **ITL.ControlPlane.ResourceProvider.IAM**: Identity and access management (Keycloak integration)
- **ITL.ControlPlane.ResourceProvider.Compute**: Virtual machines and compute resources
- **ITL.ControlPlane.ResourceProvider.Network**: Virtual networks, subnets, and network security
- **ITL.ControlPlane.ResourceProvider.Storage**: Storage accounts, blob containers, and file shares

### Tools & Extensions
- **ITL.ControlPlane.Portal**: Web-based management portal
- **ITL.ControlPlane.Terraform**: Terraform provider for infrastructure as code
- **ITL.ControlPlane.Ansible**: Ansible modules for automation

## Key Concepts

### Scoped Resources
Resources can have different uniqueness scopes:
- **Global**: Unique across entire platform
- **Management Group**: Unique within management group
- **Subscription**: Unique within subscription
- **Resource Group**: Unique within resource group

### Big 3 Handler Mixins
Production-ready patterns for resource handlers:
1. **TimestampedResourceHandler**: Automatic timestamp tracking (created/modified)
2. **ProvisioningStateHandler**: Azure-style provisioning state lifecycle
3. **ValidatedResourceHandler**: Pydantic schema validation with clear error messages

### Identity Provider Framework
Pluggable identity provider architecture supporting:
- Keycloak (primary)
- Azure AD
- Custom implementations

### Resource IDs
Hierarchical path-based IDs following Azure ARM patterns:
```
/subscriptions/{sub}/resourceGroups/{rg}/providers/{namespace}/{type}/{name}
```

Plus automatic GUID generation for global uniqueness.

## Development

```bash
# Clone the repository
git clone https://github.com/ITlusions/ITL.ControlPlane.SDK.git
cd ITL.ControlPlane.SDK

# Install development dependencies
pip install -e ".[dev]"

# Run validation tests
python test_sdk.py

# Run with pytest for more detailed output
pytest test_sdk.py -v

# Format code
black src/

# Type checking  
mypy src/

# Install SDK for use in other projects (editable install)
pip install -e .
```

## Getting Started with Provider Development

### 1. Basic Resource Provider

Create a simple resource provider by inheriting from `ResourceProvider`:

```python
from itl_controlplane_sdk import ResourceProvider, ResourceRequest, ResourceResponse

class MyProvider(ResourceProvider):
    def __init__(self):
        super().__init__("MyProvider")
        self.supported_resource_types = ["widgets", "gadgets"]
```

### 2. Scoped Resource Handler

Use scoped handlers for automatic duplicate detection and scope management:

```python
from itl_controlplane_sdk.providers import ScopedResourceHandler, UniquenessScope

class WidgetHandler(ScopedResourceHandler):
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION]
    RESOURCE_TYPE = "widgets"
```

### 3. Add Production Patterns

Use Big 3 mixins for timestamps, provisioning states, and validation:

```python
from itl_controlplane_sdk.providers import (
    TimestampedResourceHandler,
    ProvisioningStateHandler,
    ValidatedResourceHandler,
    ScopedResourceHandler
)
from pydantic import BaseModel, Field

class WidgetHandler(
    TimestampedResourceHandler,
    ProvisioningStateHandler,
    ValidatedResourceHandler,
    ScopedResourceHandler
):
    UNIQUENESS_SCOPE = [UniquenessScope.SUBSCRIPTION]
    RESOURCE_TYPE = "widgets"
    
    class ConfigSchema(BaseModel):
        size: str = Field(pattern="^(small|medium|large)$")
        replicas: int = Field(ge=1, le=10)
```

### 4. Register and Use

```python
from itl_controlplane_sdk import resource_registry

handler = WidgetHandler(storage)
resource_registry.register_handler("widgets", handler)

# Create a widget
resource_id, config = handler.create_resource(
    name="my-widget",
    data={"size": "medium", "replicas": 3},
    resource_type="widgets",
    scope_context={
        "subscription_id": "sub-123",
        "resource_group": "rg-prod"
    }
)
```

### 5. Add Identity Integration (Optional)

```python
from itl_controlplane_sdk.identity import get_identity_factory

factory = get_identity_factory()
identity_provider = factory.get_provider("keycloak", config={
    "server_url": "https://keycloak.example.com"
})

# Use in your provider
tenant = await identity_provider.get_tenant("tenant-001")
```

See the [examples/](./examples/) directory for complete working examples.

## CI/CD Pipeline

The repository includes a comprehensive CI/CD pipeline for automated testing and publishing:

- **Continuous Integration**: Automated testing on Python 3.8-3.12
- **Package Publishing**: Automatic PyPI releases for version tags
- **Security Scanning**: Dependency and code vulnerability checks
- **Provider Testing**: Validation of provider implementations
- **Automated Versioning**: Git tag-based version management (no manual editing!)
- **Quality Gates**: Code formatting, type checking, and test coverage validation

See [PIPELINE_SETUP.md](./PIPELINE_SETUP.md) for complete pipeline documentation and [AUTOMATED_VERSIONING.md](./AUTOMATED_VERSIONING.md) for version management details.

## Current Version

**Version**: 1.0.0

### Key Dependencies
- **Pydantic**: ≥2.0.0,<3.0.0 for data validation and serialization
- **pydantic-settings**: ≥2.0.0 for configuration management
- **typing-extensions**: ≥4.0.0 for enhanced type hints
- **Python**: ≥3.8 (tested on 3.8-3.12)

### Optional Dependencies
- **FastAPI**: ≥0.104.0 (for HTTP integration)
- **uvicorn**: ≥0.24.0 (for ASGI server)

### Recent Updates
- ✅ Scoped resource handlers with configurable uniqueness scopes
- ✅ Big 3 handler mixins (timestamps, provisioning states, validation)
- ✅ Identity provider framework with multi-tenancy support
- ✅ FastAPI integration module with middleware and health checks
- ✅ ITL Locations handler with dynamic region management
- ✅ Resource group handler with full Big 3 integration
- ✅ Comprehensive test suite and examples
- ✅ Enhanced type safety with Pydantic v2
- ✅ Production-ready error handling and logging
- ✅ Automated CI/CD pipeline with version management

## Documentation

### Core Documentation
- [Architecture Overview](./docs/ARCHITECTURE.md) - Detailed SDK architecture and design patterns
- [Modular Architecture](./docs/MODULAR_ARCHITECTURE.md) - Module organization and dependencies
- [Resource ID Strategy](./docs/RESOURCE_ID_STRATEGY.md) - Hybrid path + GUID resource identification

### Handler & Provider Guides
- [Scoped Resource Handler](./docs/SCOPED_RESOURCE_HANDLER.md) - Complete guide to scoped resources
- [Big 3 Handler Mixins](./BIG_3_SUMMARY.md) - Timestamps, provisioning states, validation
- [Big 3 Complete Guide](./BIG_3_COMPLETE_SUMMARY.md) - Detailed handler mixin documentation
- [Resource Group Integration](./RESOURCE_GROUP_BIG_3_INTEGRATION.md) - Resource group with Big 3 patterns

### Integration Guides
- [FastAPI Module Complete](./docs/FASTAPI_MODULE_COMPLETE.md) - FastAPI integration guide
- [FastAPI Quick Reference](./docs/FASTAPI_QUICK_REFERENCE.md) - FastAPI API reference
- [Identity Providers](./ARCHITECTURE_SUMMARY.md) - Identity provider framework overview

### Location & Infrastructure
- [ITL Locations](./ITL_LOCATIONS_SCHEMA.md) - Dynamic location management
- [Locations Handler Guide](./LOCATIONS_HANDLER_GUIDE.md) - Location handler implementation
- [Dynamic Locations](./DYNAMIC_LOCATIONS_COMPLETE.md) - Complete location system docs

### CI/CD & Operations
- [CI/CD Pipeline Setup](./docs/PIPELINE_SETUP.md) - Complete pipeline documentation
- [Automated Versioning](./docs/AUTOMATED_VERSIONING.md) - Git tag-based version management
- [Version Update Guide](./docs/VERSIONING_UPDATE.md) - Version update procedures
- [PyPI Setup Guide](./.github/PYPI_SETUP.md) - Package publishing configuration

### Quick References
- [Quick Reference](./QUICK_REFERENCE.md) - SDK API quick reference
- [Big 3 Quick Reference](./QUICK_REFERENCE_BIG_3.md) - Handler mixin quick reference
- [Architecture Summary](./ARCHITECTURE_SUMMARY.md) - Quick architecture overview
- [Scoped Resource Complete](./SCOPED_RESOURCE_HANDLER_COMPLETE.md) - Complete scoped handler reference

## Support and Contributing

For questions, issues, or contributions:

1. **Issues**: Report bugs or feature requests via GitHub Issues
2. **Development**: Follow the development setup above
3. **Testing**: Ensure all tests pass before submitting PRs
4. **Documentation**: Update documentation for any API changes
5. **Providers**: Use the common models and base classes for consistency

## License

This project is licensed under the terms specified in the LICENSE file.