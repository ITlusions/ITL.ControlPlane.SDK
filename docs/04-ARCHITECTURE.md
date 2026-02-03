# ITL ControlPlane SDK - Architecture Documentation

## Overview

The ITL ControlPlane SDK implements a clean, focused architecture that provides resource management capabilities through a provider-based framework. This is the core SDK component that has been separated from the broader ITL ControlPlane system for independent development and distribution.

## Current Repository Scope

This repository contains **only the core SDK**, following the separation of components as requested:

- **ITL.ControlPlane.SDK** (this repo): Core framework and provider interfaces  
- **ITL.ControlPlane.API**: REST API layer (moved to separate repository)
- **ITL.ControlPlane.GraphDB**: Graph database metadata system (moved to separate repository)

## Core SDK Architecture

### Package Structure (`src/itl_controlplane_sdk/`)

The core SDK is organized into modular components with clear separation of concerns:

```
itl_controlplane_sdk/
├── core/                    (HTTP models, infrastructure, exceptions)
├── identity/                (Identity provider framework)
├── providers/               (Resource provider framework)
├── services/                (Application-layer service patterns)
├── fastapi/                 (HTTP routing utilities)
├── routes/                  (Route definitions)
└── __init__.py              (Unified public API - 70+ exports)
```

#### Core Module (`core/`)

**Purpose**: Foundation models and exceptions used throughout the system

**Components**:
- `models.py` - HTTP models, infrastructure models, enums, constants
  - ResourceRequest, ResourceResponse, ResourceListResponse
  - ResourceGroup, Subscription, Deployment, Location, etc. (8 infrastructure models)
  - ResourceState, DeploymentState enums
  - Constants (PROVIDER_NAMESPACE, RESOURCE_TYPE_*, DEFAULT_LOCATIONS)

- `exceptions.py` - Standard exception hierarchy
  - ResourceProviderError, ResourceNotFoundError, ResourceConflictError, ValidationError

**Exports**: 51 items available from main SDK

#### Providers Module (`providers/`)

**Purpose**: Resource provider framework and utilities

**Components**:
- `base.py` - ResourceProvider ABC
  - Abstract base class all providers must inherit from
  - Defines create_or_update_resource(), get_resource(), delete_resource(), etc.

- `registry.py` - ResourceProviderRegistry
  - Central registry for managing multiple providers
  - Routes requests to appropriate provider
  - Provider discovery and listing

- `resource_ids.py` - Resource ID utilities
  - generate_resource_id() - Create ARM-style IDs
  - parse_resource_id() - Extract components from IDs
  - ResourceIdentity class - Dual ID support (path + GUID)

**Exports**: 7 items (ResourceProvider, ResourceProviderRegistry, resource_registry, ResourceIdentity, generate_resource_id, parse_resource_id)

#### Identity Module (`identity/`)

**Purpose**: Pluggable identity provider framework

**Components**:
- `identity_provider_base.py` - IdentityProvider ABC
- `identity_provider_factory.py` - Factory pattern for provider creation
- `tenant.py` - Tenant and subscription models
- `organization.py` - Organization and domain models
- `exceptions.py` - Identity-specific exceptions

**Exports**: 26 items (IdentityProvider, factory, tenant/org models)

#### Services Module (`services/`)

**Purpose**: Application-layer service patterns and utilities

**Components**:
- `base.py` - BaseResourceService ABC
  - Reusable patterns for all provider services
  - Idempotency support (prevent duplicate operations)
  - Event publishing (pub/sub pattern)
  - Tenant isolation (multi-tenant safety)
  - Error recovery with retry queues
  - Graph database sync

**Exports**: BaseResourceService

#### FastAPI Module (`fastapi/`)

**Purpose**: HTTP routing utilities for APIs and providers

**Components**:
- `app_factory.py` - AppFactory for creating configured FastAPI apps
- `config.py` - FastAPIConfig with dev/prod profiles
- `models.py` - Common Pydantic response models
- `middleware/` - Logging, error handling, CORS
- `routes/health.py` - Standard health check endpoints

#### Main SDK Entry Point (`__init__.py`)

**Purpose**: Unified public API with 70+ exports

**Available Imports**:
```python
from itl_controlplane_sdk import (
    # Core models and exceptions (51 items)
    ResourceRequest, ResourceResponse, ResourceGroup, Subscription, 
    ProvisioningState, ResourceProviderError, ...
    
    # Providers (7 items)
    ResourceProvider, ResourceProviderRegistry, ResourceIdentity,
    generate_resource_id, parse_resource_id,
    
    # Services (1 item)
    BaseResourceService,
    
    # Identity (12 items)
    IdentityProvider, Tenant, Organization, ...
)
```

### Provider Layer (Resource Providers)

Resource providers implement the ResourceProvider ABC and are deployed as standalone services:

**Current Providers**:
- **Core Provider** - Manages subscriptions, resource groups, deployments, locations
- **Keycloak Provider** - Identity and realm management
- **Compute Provider** - Virtual machine and infrastructure management

All providers:
1. Import ResourceProvider from SDK: `from itl_controlplane_sdk.providers import ResourceProvider`
2. Implement required methods (create, get, delete operations)
3. Use SDK models for request/response handling
4. Leverage BaseResourceService for common patterns (idempotency, events, etc.)
     ↓
External Services (Keycloak, Cloud APIs, etc.)
```

## Component Relationships

### Dependency Hierarchy

```
External Services (Keycloak, Cloud APIs, etc.)
     ↑
Resource Providers (Core, Keycloak, Compute)
     ↑ (inherit from)
Providers Module (ResourceProvider ABC, Registry)
     ↑ (use)
Services Module (BaseResourceService patterns)
     ↑ (use models from)
Core Module (Models, Exceptions)
     ↑
Main SDK __init__.py (70+ unified exports)
```

### Module Dependencies

```
itl_controlplane_sdk/
├── core/                    (NO dependencies except pydantic)
│   ├── models.py
│   └── exceptions.py
│
├── identity/                (depends on: core)
│   ├── tenant.py
│   ├── organization.py
│   ├── identity_provider_base.py
│   ├── identity_provider_factory.py
│   └── exceptions.py
│
├── providers/               (depends on: core)
│   ├── base.py              (ResourceProvider ABC)
│   ├── registry.py          (uses ResourceProvider)
│   └── resource_ids.py
│
├── services/                (depends on: core, providers)
│   └── base.py              (BaseResourceService - reusable patterns)
│
├── fastapi/                 (depends on: core, optional)
│   ├── app_factory.py
│   ├── config.py
│   ├── middleware/
│   └── routes/
│
└── __init__.py              (imports and exports from all modules)
```

### Integration Patterns

**Pattern 1: Direct SDK Integration (Simplest)**
```python
from itl_controlplane_sdk.providers import ResourceProvider, ResourceProviderRegistry
from itl_controlplane_sdk import ResourceRequest, ResourceResponse

class MyProvider(ResourceProvider):
    async def create_or_update_resource(self, request: ResourceRequest) -> ResourceResponse:
        # Implementation
        pass

# Use registry to route requests
registry = ResourceProviderRegistry()
registry.register_provider("MyNamespace", "resource_type", MyProvider())
response = await registry.create_or_update_resource("MyNamespace", "resource_type", request)
```

**Pattern 2: Service-Based Integration (Recommended for Complex Providers)**
```python
from itl_controlplane_sdk import BaseResourceService, ResourceProvider
from itl_controlplane_sdk import ResourceRequest, ResourceResponse

class MyResourceService(BaseResourceService):
    async def create_resource(self, spec, idempotency_key, request_context):
        # Use parent's idempotency check
        existing = await self._check_idempotency(idempotency_key, spec)
        if existing:
            return existing
        
        # Provider-specific logic
        resource = await self.provider.create_my_resource(spec)
        
        # Use parent's helper methods
        await self._store_idempotency_result(idempotency_key, resource)
        await self._verify_tenant_isolation(spec.tenant_id, request_context['tenant_id'])
        await self._publish_event("resource.created", resource, request_context)
        await self._sync_to_graph_database(resource)
        
        return resource

class MyProvider(ResourceProvider):
    def __init__(self):
        super().__init__("MyNamespace")
        self.service = MyResourceService(provider=self)
```

**Pattern 3: FastAPI-Based Provider (Standalone Service)**
```python
from itl_controlplane_sdk.fastapi import AppFactory
from itl_controlplane_sdk.providers import ResourceProvider, ResourceProviderRegistry

# Create provider
provider = MyProvider()

# Create FastAPI app using factory
factory = AppFactory("My Provider", "1.0.0")
app = factory.create_app()  # Includes health checks, logging, error handling

# Register with registry
registry = ResourceProviderRegistry()
registry.register_provider("MyNamespace", "resource_type", provider)
app.state.registry = registry

# Now accessible via HTTP
@app.post("/resources")
async def create_resource(request: ResourceRequest):
    return await registry.create_or_update_resource("MyNamespace", "resource_type", request)
```

### Request Processing Flow

```
1. Client Application
   └─ Sends ResourceRequest to SDK/Provider
   
2. SDK Core (or FastAPI app)
   └─ ResourceRequest validated using Pydantic
   └─ Routes to appropriate provider via ResourceProviderRegistry
   
3. Provider Layer
   └─ ResourceProvider.create_or_update_resource() called
   └─ May use BaseResourceService for:
      - Idempotency checks
      - Event publishing
      - Tenant isolation
      - Graph DB sync
   
4. External System Integration
   └─ Provider calls actual service (Keycloak, Cloud API, etc.)
   
5. Response Processing
   └─ Provider returns ResourceResponse
   └─ SDK validates and returns to client
```

## Design Principles

### Separation of Concerns

The SDK is organized into distinct layers with clear responsibilities:

**Data Layer** (`core/`):
- Models: Pydantic dataclasses with validation
- Exceptions: Structured error hierarchy
- No business logic, pure data structures

**Provider Framework Layer** (`providers/`):
- ResourceProvider ABC: Interface for all providers
- ResourceProviderRegistry: Provider registration and routing
- Resource ID utilities: Identification strategies

**Service Layer** (`services/`):
- BaseResourceService: Reusable patterns
- Idempotency, event publishing, tenant isolation
- Error handling and recovery

**Application Layer** (`fastapi/`):
- AppFactory: FastAPI app creation with defaults
- Middleware: Logging, error handling, CORS
- Routes: Standard health checks

**External Integration Layer**:
- Individual providers (Core, Keycloak, Compute)
- Each provider handles one domain
- Independent deployment and scaling

### Modularity and Extensibility

**Adding a New Provider**:
```python
from itl_controlplane_sdk.providers import ResourceProvider
from itl_controlplane_sdk import ResourceRequest, ResourceResponse

class MyNewProvider(ResourceProvider):
    async def create_or_update_resource(self, request: ResourceRequest) -> ResourceResponse:
        # Implementation
        pass
```

**Extending Services**:
```python
from itl_controlplane_sdk import BaseResourceService

class MyService(BaseResourceService):
    async def my_operation(self, ...):
        # Use inherited idempotency, events, etc.
        existing = await self._check_idempotency(key, spec)
        # ... custom logic ...
```

**Custom Middleware or Routes**:
```python
from itl_controlplane_sdk.fastapi import AppFactory

factory = AppFactory("My App", "1.0.0")
app = factory.create_app(
    routers=[custom_router],
    add_health_routes=True,
    add_exception_handlers=True
)
```

### Consistency and Standards

**Standardized Request/Response**:
- All providers use ResourceRequest/ResourceResponse
- Consistent error response format
- ARM-compatible resource IDs

**Shared Patterns**:
- BaseResourceService provides idempotency, events, tenant isolation
- Common models ensure type safety
- Exception hierarchy for structured error handling

**Configuration and Deployment**:
- Environment-based configuration (development/production)
- Docker support via Dockerfile
- PyPI package distribution

### Type Safety and Validation

- **Pydantic Models**: Full validation on instantiation
- **Abstract Base Classes**: Enforced interface contracts
- **Static Typing**: Enhanced IDE support and type checking
- **Optional Dependencies**: fastapi support via optional install (`pip install itl-controlplane-sdk[fastapi]`)

## Configuration and Deployment

### Environment Configuration
- Provider-specific settings via environment variables
- Configurable logging levels and output formatting
- Namespace and resource type mappings

### Deployment Patterns
- **Single Process**: All providers in one application
- **Microservices**: Individual provider deployments
- **Hybrid**: Core SDK with remote provider calls

## Extension Guide

### Adding New Providers

1. **Create Provider Directory**: `providers/myservice/`
2. **Implement Provider Class**: Inherit from `ResourceProvider`
3. **Define Resource Models**: Service-specific data structures
4. **Register Provider**: Add to registry with namespace and resource types
5. **Add Tests**: Unit and integration tests for provider

### Adding New Resource Types

1. **Extend Provider**: Add new resource type to existing provider
2. **Update Models**: Add resource-specific properties
3. **Implement Methods**: CRUD operations for new resource type
4. **Update Registration**: Register new resource type in registry

## Testing Strategy

### Unit Testing
- **Provider Tests**: Individual provider functionality
- **Model Tests**: Data validation and serialization
- **Registry Tests**: Provider registration and routing

### Integration Testing  
- **SDK Integration**: Real provider interactions through SDK
- **Provider Integration**: Direct service interactions
- **Cross-Provider Tests**: Multi-provider scenarios

### Contract Testing
- **Provider Interface**: Ensure all providers implement required methods
- **SDK Compatibility**: Consistent interface patterns
- **Error Handling**: Consistent error responses

This architecture provides a robust foundation for building cloud resource management systems with clear separation of concerns, extensibility, and maintainability.

## Extension Guide

### Adding New Providers

1. **Create Provider Directory**: `providers/myservice/`
2. **Implement Provider Class**: Inherit from `ResourceProvider`
3. **Define Resource Models**: Service-specific data structures
4. **Register Provider**: Add to registry with namespace and resource types
5. **Add Tests**: Unit and integration tests for provider

### Adding New Resource Types

1. **Extend Provider**: Add new resource type to existing provider
2. **Update Models**: Add resource-specific properties
3. **Implement Methods**: CRUD operations for new resource type
4. **Update Registration**: Register new resource type in registry

## Keycloak Realm Provider Example

The SDK includes a comprehensive example that demonstrates building a production-ready Keycloak realm management provider:

### Features Demonstrated

1. **Realm Management**:
   - Create and configure Keycloak realms
   - Set display names, themes, and locale settings
   - Enable/disable realms and configure internationalization

2. **Configuration Validation**:
   - Validate realm configuration structure
   - Check required fields and data types
   - Provide meaningful error messages

3. **Terraform Integration**:
   - Generate Terraform configurations for realm deployment
   - Use mrparkers/keycloak provider for reliable realm management
   - Handle Terraform state and workspace management

4. **Async Operations**:
   - Non-blocking plan/apply/destroy operations
   - Progress tracking and status reporting
   - Proper error handling and cleanup

### Sample Configuration

```json
{
    "instance": {
        "realms": [
            {
                "name": "itl-dev",
                "display_name": "ITL Development",
                "enabled": true,
                "login_theme": "keycloak",
                "internationalization_enabled": true,
                "supported_locales": ["en", "nl"],
                "default_locale": "en"
            }
        ]
    }
}
```

### Running the Example

```bash
# Test the provider directly
python examples/keycloak_provider.py

# Run as a server (if available)
python examples/server_example.py
```

## Usage Examples

### Basic Provider Usage

```python
from itl_controlplane_sdk import ResourceProviderRegistry, ResourceRequest
from providers.keycloak.provider import KeycloakProvider

# Create registry and register provider
registry = ResourceProviderRegistry()
registry.register_provider("ITL.Identity", "realms", KeycloakProvider())

# Create a resource
request = ResourceRequest(
    resource_name="test-realm",
    resource_type="realms",
    properties={"display_name": "Test Realm", "enabled": True}
)

response = await registry.create_or_update_resource(
    namespace="ITL.Identity",
    resource_type="realms", 
    request=request
)
```

### Direct Provider Usage

```python
from providers.keycloak.provider import KeycloakProvider
from itl_controlplane_sdk import ResourceRequest

# Use provider directly
provider = KeycloakProvider()
request = ResourceRequest(
    resource_name="my-realm",
    resource_type="realms",
    properties={"display_name": "My Realm"}
)

response = await provider.create_or_update_resource(request)
```

## Future Enhancements

1. **Plugin System**: Enhanced module architecture for easy plugin integration
2. **Caching Layer**: Add caching support for plan/state management
3. **Observability**: Enhanced tracing and logging capabilities
4. **Security**: Authentication and authorization modules
5. **Testing**: Test utilities and mock implementations

This modular architecture provides a solid foundation for the ITL.ControlPanel.SDK to grow and evolve while maintaining clean code organization and developer experience.