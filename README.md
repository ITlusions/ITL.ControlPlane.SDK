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

Install only the modules you need:

```bash
# Core + providers (default, no optional dependencies)
pip install itl-controlplane-sdk

# With identity framework (tenant/organization management)
pip install itl-controlplane-sdk[identity]

# With FastAPI integration (app factory, middleware)
pip install itl-controlplane-sdk[fastapi]

# With Pulumi IaC helpers
pip install itl-controlplane-sdk[pulumi]

# Everything
pip install itl-controlplane-sdk[all]
```

For development:
```bash
git clone https://github.com/ITlusions/ITL.ControlPlane.SDK.git
cd ITL.ControlPlane.SDK
pip install -e ".[all,dev]"
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
from itl_controlplane_sdk.api import create_app
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
│   └── itl_controlplane_sdk/
│       ├── __init__.py                    # Package exports
│       ├── core/
│       │   ├── __init__.py
│       │   ├── models.py                  # Resource request/response models, ProvisioningState
│       │   └── exceptions.py              # SDK exceptions
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── base.py                    # ResourceProvider abstract base class
│       │   ├── registry.py                # ResourceProviderRegistry (thread-safe)
│       │   ├── resource_ids.py            # ResourceIdentity, generate/parse resource IDs
│       │   ├── scoped_resources.py        # ScopedResourceHandler, UniquenessScope
│       │   ├── resource_handlers.py       # Big 3 mixins (Validated, Provisioning, Timestamped)
│       │   ├── resource_group_handler.py  # ResourceGroupHandler reference implementation
│       │   ├── locations.py               # Location management base
│       │   └── locations.py (unified)           # LocationsHandler (27 regions)
│       ├── identity/
│       │   ├── __init__.py
│       │   ├── identity_provider_base.py  # IdentityProvider abstract base class
│       │   ├── identity_provider_factory.py # IdentityProviderFactory (singleton, registry)
│       │   ├── tenant.py                  # TenantSpec, Tenant, TenantStatus, TenantResponse
│       │   ├── organization.py            # OrganizationSpec, CustomDomain, TenantAdminUser
│       │   └── exceptions.py              # Identity exceptions
│       ├── fastapi/
│       │   ├── __init__.py
│       │   ├── app_factory.py             # AppFactory with configurable middleware
│       │   ├── config.py                  # FastAPIConfig (development/production presets)
│       │   ├── middleware/
│       │   │   ├── __init__.py
│       │   │   ├── error_handling.py      # APIError, setup_exception_handlers
│       │   │   └── logging.py             # LoggingMiddleware with timing
│       │   └── routes/
│       │       ├── __init__.py
│       │       └── health.py              # /health and /ready endpoints
│       ├── pulumi/
│       │   ├── __init__.py
│       │   ├── deployment.py              # Pulumi deployment orchestration
│       │   ├── resource_mapper.py         # SDK-to-Pulumi resource mapping
│       │   └── stack.py                   # Stack management
│       ├── services/
│       │   ├── __init__.py
│       │   └── base.py                    # Base service patterns
│       └── routes/
│           └── metadata.py                # Metadata routes
│
├── examples/
│   ├── README.md                          # Complete index and learning paths
│   ├── core/
│   │   ├── quickstart.py                  # Basic registry + CRUD (start here)
│   │   └── intermediate/
│   │       ├── resource_id_example.py     # ARM IDs, GUIDs, parsing, ResourceIdentity
│   │       └── registry_example.py        # Multi-provider registration, discovery
│   ├── compute/
│   │   ├── intermediate/
│   │   │   └── big_3_examples.py          # VirtualMachineHandler (Big 3 mixins)
│   │   └── advanced/
│   │       └── scoped_resource_examples.py # VM scoping patterns
│   ├── storage/
│   │   ├── intermediate/
│   │   │   ├── big_3_examples.py          # StorageAccountHandler (global scope)
│   │   │   └── storage_account_example.py # Global vs RG scope comparison
│   │   └── advanced/
│   │       └── scoped_resource_examples.py # Global scoping patterns
│   ├── network/
│   │   ├── intermediate/
│   │   │   └── big_3_examples.py          # NetworkInterfaceHandler (RG scope)
│   │   └── advanced/
│   │       └── scoped_resource_examples.py # Network scoping patterns
│   ├── management/
│   │   ├── intermediate/
│   │   │   ├── big_3_examples.py          # PolicyHandler, DatabaseHandler
│   │   │   └── resource_group_handler_example.py # ResourceGroupHandler (Big 3 ref)
│   │   └── advanced/
│   │       └── scoped_resource_examples.py # ManagementGroupHandler
│   ├── providers/
│   │   └── intermediate/
│   │       └── custom_provider_example.py # Custom ResourceProvider with actions
│   ├── identity/
│   │   ├── beginner/
│   │   │   ├── tenant_example.py          # TenantSpec, lifecycle, multi-tenant
│   │   │   └── organization_example.py    # Organizations, domains, admin users
│   │   └── intermediate/
│   │       └── identity_provider_factory_example.py # Factory, singleton, switching
│   ├── fastapi/
│   │   ├── beginner/
│   │   │   └── app_factory_example.py     # AppFactory, config presets, CORS
│   │   └── intermediate/
│   │       └── middleware_example.py      # APIError, LoggingMiddleware, error handling
│   ├── deployment/
│   │   └── intermediate/
│   │       └── pulumi_deployment_example.py # Pulumi multi-env IaC
│   └── tests/
│       ├── unit/
│       │   └── test_locations.py (unified)      # Location validation (27 regions)
│       └── integration/
│           └── test_resource_group_big_3.py # Handler testing patterns
│
├── pyproject.toml
└── README.md
```

## Architecture

The SDK follows a clean, modular architecture with clear separation of concerns.
Modules are loaded lazily so consumers only pay the import cost for what they use.

```
+-------------------------------------------------+
|            itl_controlplane_sdk                  |
|                                                  |
|  Eager (always loaded)     Lazy (on first use)   |
|  ┌──────────┐              ┌──────────────────┐  |
|  │  core    │              │  identity        │  |
|  │  --------│              │  fastapi         │  |
|  │  models  │              │  services        │  |
|  │  except. │              │  pulumi          │  |
|  └──────────┘              └──────────────────┘  |
|  ┌──────────┐                                    |
|  │ providers│                                    |
|  └──────────┘                                    |
+-------------------------------------------------+
```

### Core Layer (eager)
- **Models**: Pydantic-based data models for requests, responses, and resource metadata with full validation
- **Exceptions**: Hierarchical exception types for error handling
- **Constants**: Shared constants for resource types, locations, and provider namespaces

### Provider Layer (eager)
- **Registry**: Thread-safe centralized registration and management of resource providers
- **Base Classes**: Abstract base classes (`ResourceProvider`, `ScopedResourceHandler`) for implementations
- **Resource IDs**: Utilities for generating and parsing hierarchical resource IDs
- **Scoped Resources**: Configurable scope-based uniqueness and duplicate detection
- **Handler Mixins**: Production-ready patterns (timestamps, provisioning states, validation)

### Identity Layer (lazy - `pip install itl-controlplane-sdk[identity]`)
- **Identity Providers**: Pluggable identity provider framework
- **Factory Pattern**: Centralized provider registration and instantiation
- **Tenant Management**: Multi-tenant support with organization hierarchies
- **Domain Management**: Custom domain support and verification
- **Exceptions**: Self-contained exception hierarchy (`ConfigurationError`, `TenantError`, etc.)

### FastAPI Layer (lazy - `pip install itl-controlplane-sdk[fastapi]`)
- **App Factory**: FastAPI application factory with configurable middleware
- **Middleware**: Error handling, logging, and request correlation
- **Routes**: Built-in health check and metadata endpoints
- **Configuration**: Environment-based configuration management

### Pulumi Layer (lazy - `pip install itl-controlplane-sdk[pulumi]`)
- **Stack Management**: Pulumi stack configuration and orchestration
- **Resource Mapper**: SDK-to-Pulumi resource mapping
- **Deployment**: Multi-environment deployment orchestration

### Service Layer (lazy)
- **Base Services**: Application-layer patterns for business logic
- **Resource Services**: High-level resource management APIs

### Design Principles
- **Modular Installs**: Granular extras (`[identity]`, `[fastapi]`, `[pulumi]`, `[all]`) so consumers install only what they need
- **Lazy Loading**: Optional modules load on first attribute access via `__getattr__`, keeping base import fast
- **Separation of Concerns**: Clear boundaries between layers
- **Dependency Inversion**: Core SDK has no dependencies on FastAPI, identity backends, or Pulumi
- **Type Safety**: Comprehensive type hints and runtime validation; `TYPE_CHECKING` block ensures IDE support for lazy imports
- **Async-First**: Native async/await support throughout
- **Extensibility**: Easy to extend with custom providers and handlers
- **Backward Compatibility**: `from itl_controlplane_sdk import Tenant` still works (lazy-loaded transparently)

## ITL ControlPlane Ecosystem

The SDK is the foundation of the ITL ControlPlane ecosystem — a modular, Azure ARM-compatible cloud management platform. All components depend on this SDK for shared models, providers, storage, and FastAPI patterns.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                               User Interfaces                                    │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────────┐  │
│  │   Admin Portal      │  │  Customer Portal    │  │   Dashboard (Dev)       │  │
│  │   Port 8091         │  │  Port 8090          │  │   Port 8080             │  │
│  │   Full Infra Access │  │  No Infra Access    │  │   Combined (legacy)     │  │
│  └─────────┬───────────┘  └─────────┬───────────┘  └───────────┬─────────────┘  │
└────────────┼───────────────────────┼───────────────────────────┼────────────────┘
             │                       │                           │
             └───────────────────────┴───────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────────────┐
│                           ITL.ControlPlane.Api                                   │
│             API Gateway — Lightweight Proxy, ARM Routing, JWT Validation         │
│                                  Port 8080                                       │
└────────────┬────────────────────────┬────────────────────────┬──────────────────┘
             │                        │                        │
     ┌───────▼───────┐        ┌───────▼───────┐        ┌───────▼───────┐
     │ Core Provider │        │  IAM Provider │        │Compute Provider│
     │   Port 8000   │        │   Port 8001   │        │   Port 8003   │
     │  Subscriptions│        │    Realms     │        │     VMs       │
     │  ResourceGroups│       │    Users      │        │   Disks       │
     │  Deployments  │        │   Clients     │        │   Images      │
     │  Locations    │        │Organizations  │        │               │
     └───────┬───────┘        └───────┬───────┘        └───────┬───────┘
             │                        │                        │
     ┌───────┴────────────────────────┴────────────────────────┴───────┐
     │                    ITL.ControlPanel.SDK                          │
     │  Models · Providers · Storage · FastAPI · Identity · Exceptions  │
     └───────────────────────────────────┬─────────────────────────────┘
                                         │
┌────────────────────────────────────────▼────────────────────────────────────────┐
│                           Supporting Services                                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌────────────┐  │
│  │   PostgreSQL    │  │    Keycloak     │  │     Neo4j       │  │  RabbitMQ  │  │
│  │   Storage       │  │    Identity     │  │   Graph Sync    │  │  Events    │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  └────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Component Repositories

#### 📦 Core SDK

| Repository | Purpose | Port |
|------------|---------|------|
| **ITL.ControlPanel.SDK** | Shared library — models, providers, storage, FastAPI, identity, exceptions | N/A (library) |

This SDK provides:
- `ResourceProvider` base class for building resource providers
- `AppFactory` for consistent FastAPI application creation
- `SQLAlchemyStorageEngine` for PostgreSQL persistence
- Pydantic v2 models with ARM-compatible resource shapes
- Exception hierarchy mapped to HTTP status codes
- Identity provider framework (Keycloak, Azure AD)

---

#### 🚪 API Gateway

| Repository | Purpose | Port |
|------------|---------|------|
| **ITL.ControlPlane.Api** | API Gateway — ARM-style routing, provider discovery, JWT validation | 8080 |

The gateway:
- Routes `/subscriptions/.../providers/ITL.{Domain}/...` requests to resource providers
- Manages provider registration and health monitoring
- Exposes `/providers/register` for dynamic provider onboarding
- Provides unified OpenAPI spec across all providers

---

#### 🔧 Resource Providers

| Repository | Namespace | Resources | Port |
|------------|-----------|-----------|------|
| **ITL.ControlPlane.ResourceProvider.Core** | `ITL.Core` | subscriptions, resourceGroups, managementGroups, deployments, locations, tags, policies, tenants | 8000 |
| **ITL.ControlPlane.ResourceProvider.IAM** | `ITL.IAM` | realms, users, clients, organizations, tenants | 8001 |
| **ITL.ControlPlane.ResourceProvider.Compute** | `ITL.Compute` | virtualMachines, disks, images, availabilitySets | 8003 |

Each provider:
- Subclasses `ResourceProvider` from the SDK
- Registers at startup with the API Gateway
- Implements CRUD operations for its resource types
- Uses SDK storage engine or custom backends

---

#### 🖥️ User Interfaces

| Repository | Audience | Features | Port |
|------------|----------|----------|------|
| **ITL.ControlPlane.Admin** | Platform Operators | Full infrastructure access, Docker/K8s monitoring, container management | 8091 |
| **ITL.ControlPlane.Portal** | Customers | Self-service resources, NO infrastructure access, secure by design | 8090 |
| **ITL.ControlPlane.Dashboard** | Developers | Combined portal (legacy), full access, development/testing | 8080 |

Portal separation follows:
- Admin Portal = Internal SRE tools (full infrastructure visibility)
- Customer Portal = Self-service resource management only, no infrastructure access
- Dashboard = Development/testing environment

---

#### 🗄️ Supporting Infrastructure

| Repository | Purpose |
|------------|---------|
| **ITL.ControlPlane.GraphDB** | Neo4j graph database integration for resource relationships and metadata sync |
| **ITLAuth** | Keycloak deployment and configuration for OIDC/OAuth2 authentication |

---

#### 📝 Partner & Template Projects

| Repository | Purpose |
|------------|---------|
| **ITL.ControlPlane.ResourceProvider** | Template/example for partners building custom resource providers |

Partners use this as a starting point to build their own resource providers following SDK patterns.

---

#### 📦 Client SDK (Public Distribution)

| Repository | License | Purpose |
|------------|---------|---------|
| **ITL.ControlPanel.SDK.Client** | MIT | Public Python client for customers consuming the ControlPlane API |

```bash
pip install itl-controlplane-client
```

The Client SDK provides:
- **Pydantic models** for API responses (Resource, Subscription, ResourceGroup, Location, etc.)
- **Async HTTP client** (`ControlPlaneClient`) with typed operations
- **Auth helpers** (OIDCAuth for Keycloak, BearerAuth, APIKeyAuth)
- **No internal implementation** — only models and HTTP operations

##### Two-Tier SDK Strategy

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              CONSUMERS                                   │
├─────────────────────────────────┬───────────────────────────────────────┤
│        ITL / PARTNERS           │              CUSTOMERS                │
│   (Build Resource Providers)    │      (Use ControlPlane API)           │
└───────────────┬─────────────────┴──────────────────┬────────────────────┘
                │                                    │
                ▼                                    ▼
┌───────────────────────────────┐    ┌───────────────────────────────────┐
│   itl-controlplane-sdk        │    │   itl-controlplane-client         │
│   (Apache 2.0 / Internal)     │    │   (MIT / Public PyPI)             │
├───────────────────────────────┤    ├───────────────────────────────────┤
│ ✓ Full provider base classes  │    │ ✓ Pydantic response models        │
│ ✓ Storage engines (SQLAlchemy)│    │ ✓ Async HTTP client               │
│ ✓ FastAPI integration         │    │ ✓ Auth helpers (OIDC/Bearer/Key)  │
│ ✓ Identity providers          │    │ ✓ Typed operations                │
│ ✓ Message broker integration  │    │ ✗ No provider implementation      │
│ ✓ Core models & exceptions    │    │ ✗ No storage/database access      │
└───────────────────────────────┘    └───────────────────────────────────┘
```

**Why two SDKs?**
- **Security**: Customers cannot access internal implementation details
- **Simplicity**: Client SDK is lightweight (~50KB vs ~2MB full SDK)
- **Independence**: Client SDK has no dependency on internal SDK
- **Licensing**: MIT for maximum customer adoption, Apache 2.0 for patent protection internally

---

### Dependency Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CUSTOMER APPLICATIONS                         │
│                   (uses itl-controlplane-client)                     │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTPS / REST
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          API GATEWAY                                 │
│                   ITL.ControlPlane.Api (8080)                        │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ Internal routing
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       RESOURCE PROVIDERS                             │
│        Core (8000) · IAM (8001) · Compute (8003) · Partners          │
│                   (uses itl-controlplane-sdk)                        │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
           PostgreSQL       Keycloak        Neo4j
```

**Key principles**:
- All providers depend on the SDK, never on each other directly
- Provider-to-provider communication goes through API Gateway or message broker
- Customers use Client SDK to interact with the platform via API Gateway
- Internal SDK is never exposed to customers

---

### Quick Reference: Resource Provider Development

To build a new resource provider:

1. **Install SDK**: `pip install itl-controlplane-sdk[fastapi,persistence-sqlalchemy]`
2. **Subclass `ResourceProvider`**: Implement CRUD methods
3. **Use `AppFactory`**: Create FastAPI app with standard middleware
4. **Register with Gateway**: POST to `/providers/register` on startup
5. **Deploy**: Docker container with Helm chart

See [.github/agents/ITLResourceProvider.agent.md](.github/agents/ITLResourceProvider.agent.md) for complete patterns and examples.

---

### Related Ecosystem Projects

| Project | Purpose |
|---------|---------|
| **ITL.Talos.HardenedOS** | Hardened Talos Linux images for secure clusters |

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

# Install all modules + development dependencies
pip install -e ".[all,dev]"

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

### Optional Dependencies (extras)
| Extra | Dependencies | Description |
|-------|-------------|-------------|
| `[identity]` | email-validator ≥2.0.0 | Identity provider framework, tenant/org models |
| `[fastapi]` | FastAPI ≥0.104.0, uvicorn ≥0.24.0, starlette ≥0.27.0 | HTTP integration with app factory |
| `[pulumi]` | pulumi ≥3.0.0, pulumi-kubernetes ≥4.0.0 | Infrastructure-as-Code helpers |
| `[all]` | All of the above | Install everything |

### Recent Updates
- **Modular architecture with lazy loading**: Optional modules (identity, fastapi, pulumi, services) load on first use via `__getattr__`
- **Granular install extras**: `pip install itl-controlplane-sdk[identity]`, `[fastapi]`, `[pulumi]`, `[all]`
- **Self-contained identity exceptions**: 18 exception classes defined locally in `identity/exceptions.py` (no broken cross-repo imports)
- **10 new working examples** across core, identity, providers, fastapi, storage, and management
- **Comprehensive examples index** with 6 learning paths in `examples/README.md`
- Scoped resource handlers with configurable uniqueness scopes
- Big 3 handler mixins (timestamps, provisioning states, validation)
- Identity provider framework with multi-tenancy support
- FastAPI integration module with middleware and health checks
- ITL Locations handler with dynamic region management
- Resource group handler with full Big 3 integration
- Enhanced type safety with Pydantic v2
- Production-ready error handling and logging
- Automated CI/CD pipeline with version management

## Documentation

**Phase 2 Complete:** Documentation has been consolidated from 26 scattered files into 9 comprehensive, well-organized guides. [See consolidation details »](./docs/99-Archive/CONSOLIDATION_MANIFEST.md)

### Foundation (01-04)
1. [**Architecture Complete**](./docs/02-ARCHITECTURE.md) - Complete system architecture, components, and design principles
2. [**Core Concepts**](./docs/03-CORE_CONCEPTS.md) - Scoped handlers, resource ID strategy, and modular architecture (foundation concepts)
3. [**Resource Groups**](./docs/04-RESOURCE_GROUPS.md) - Complete resource group implementation with creation flow and extensibility patterns

### Handler Patterns (05-07)
4. [**Handler Mixins**](./docs/06-HANDLER_MIXINS.md) - TimestampedResourceHandler, ProvisioningStateHandler, ValidatedResourceHandler (Big 3)
5. [**Location Validation**](./docs/07-LOCATION_VALIDATION.md) - Location handler, validation, and 30+ Azure regions + 24 ITL custom locations
6. [**API Endpoints**](./docs/08-API_ENDPOINTS.md) - FastAPI integration, AppFactory, middleware, and HTTP routing

### Advanced Features (08-09)
7. [**Async Patterns**](./docs/09-ASYNC_PATTERNS.md) - Service Bus integration, async provider modes, and message queuing
8. [**Worker Roles**](./docs/11-WORKER_ROLES.md) - Job queue, worker lifecycle, async offloading, and scaling patterns
9. [**CI/CD Pipelines**](./docs/14-CI_CD_PIPELINES.md) - GitHub Actions workflows, automated versioning, and publishing

### Quick References & Tools
- [**Quick Reference**](./docs/14-QUICK_REFERENCE.md) - Handler API quick lookup
- [**Getting Started Guide**](./docs/00-GETTING-STARTED/) - Onboarding and setup

### Additional Resources
- [**Archive & Consolidation Details**](./docs/99-Archive/README.md) - Explains document consolidation and where to find old content
- [**PyPI Setup Guide**](./.github/PYPI_SETUP.md) - Package publishing configuration
- [**Examples Directory**](./examples/) - Working code examples and usage patterns

## Versioning and Releases

This project uses **semantic versioning** with **automatic releases on merge** to main/develop.

> **Automatic Releases**: When you merge to `main` or `develop`, versions are automatically bumped and released to PyPI. No manual tagging needed!

### Quick Start

Check current version:
```bash
python scripts/version.py --get-version
```

### How It Works

1. **Push to `develop`** → Auto-bumps patch version (`1.0.0` → `1.0.1`) → Auto-released to PyPI
2. **Push to `main`** → Auto-bumps minor version (`1.0.1` → `1.1.0`) → Auto-released to PyPI
3. **Push to `feature/*`** → Dev version only (Test PyPI, no release)

See [AUTO_RELEASE_WORKFLOW.md](AUTO_RELEASE_WORKFLOW.md) for detailed flow.

### Documentation

- **[AUTO_RELEASE_WORKFLOW.md](AUTO_RELEASE_WORKFLOW.md)** - **START HERE** - How automatic releases work
- **[VERSIONING_QUICKSTART.md](VERSIONING_QUICKSTART.md)** - Quick reference guide
- **[VERSIONING.md](VERSIONING.md)** - Complete branching strategy and versioning guide
- **[RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md)** - Pre-release verification checklist (for manual releases)
- **[COMMANDS_CHEATSHEET.md](COMMANDS_CHEATSHEET.md)** - Git and version tool commands

### Branch Behavior

| Branch | Auto-Release | Version Format | PyPI | Notes |
|--------|---|---|---|---|
| `main` | Yes (Minor bump) | → `1.1.0` | Prod | Feature release |
| `develop` | Yes (Patch bump) | → `1.0.1` | Prod | Bug fix release |
| `feature/*` | No | `1.0.1.dev+feature...` | Test | Feature development |
| Tag `v1.0.0` | Manual | `1.0.0` | Prod | Manual release |

### Version Management Tools

- **Version Script**: [scripts/version.py](scripts/version.py) - Core semantic versioning tool
- **PowerShell Wrapper**: [scripts/version.ps1](scripts/version.ps1) - Windows convenience script
- **Bash Wrapper**: [scripts/version.sh](scripts/version.sh) - Linux/macOS convenience script

### CI/CD Pipeline

All pushes trigger automated workflows:

```
Push to main/develop
  ↓ Test & Build (1-2 min)
  ↓ Auto-Tag Job (bumps version, creates git tag)
  ↓ Release Workflow (triggered by tag)
  ↓ Publish to PyPI + Create GitHub Release (2 min)
  DONE (total: 3-5 minutes)
```

**No manual steps needed for releases!**

## Support and Contributing

For questions, issues, or contributions:

1. **Issues**: Report bugs or feature requests via GitHub Issues
2. **Development**: Follow the development setup above
3. **Testing**: Ensure all tests pass before submitting PRs
4. **Documentation**: Update documentation for any API changes
5. **Providers**: Use the common models and base classes for consistency

## License

This project is licensed under the terms specified in the LICENSE file.

