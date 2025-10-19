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

The core SDK follows a simple, focused architecture with four main components:

#### Core Components:

**`models.py` - Core Data Models**
- **Purpose**: Defines the core data structures used throughout the system
- **Key Models**:
  - `ResourceRequest`: Standardized resource operation requests
  - `ResourceResponse`: Unified resource operation responses  
  - `ResourceListResponse`: Resource listing responses
  - `ProvisioningState`: Resource provisioning status enumeration
- **Responsibilities**:
  - Data model definitions with Pydantic validation
  - Serialization support
  - Type safety across the SDK

**`resource_provider.py` - Provider Base Class**
- **Purpose**: Abstract base class that all resource providers must implement
- **Key Classes**: `ResourceProvider`
- **Methods**:
  - `create_or_update_resource()`: Resource creation/updates
  - `get_resource()`: Resource retrieval
  - `list_resources()`: Resource listing
  - `delete_resource()`: Resource deletion
- **Responsibilities**:
  - Define provider interface contract
  - Common validation logic
  - Resource ID generation
  - Error handling patterns

**`registry.py` - Provider Registry**
- **Purpose**: Central registry for managing and routing to resource providers
- **Key Classes**: `ResourceProviderRegistry`
- **Responsibilities**:
  - Provider registration and discovery
  - Request routing to appropriate providers
  - Provider namespace management
  - Global resource operations coordination
- **Features**:
  - Multi-provider support
  - Namespace-based routing (e.g., "ITL.Identity", "ITL.Compute")
  - Provider capability discovery

**`__init__.py` - Package Exports**
- **Purpose**: Defines the public API of the SDK
- **Exports**:
  - `ResourceProviderRegistry`: Main registry class
  - `ResourceProvider`: Base provider class  
  - Data models from `models.py`
- **Usage**: Enables clean imports like `from itl_controlplane_sdk import ResourceProviderRegistry`

### Provider Layer (`providers/`)

The provider layer contains concrete implementations of resource providers for specific services and technologies. Providers can be deployed either:

1. **Embedded**: Directly imported and used within applications
2. **Containerized**: Deployed as standalone services

#### Current Providers:

**`keycloak/` - Identity Provider**
- **Purpose**: Keycloak realm and user management
- **Namespace**: `ITL.Identity`
- **Resource Types**: `realms`, `users`, `groups`
- **Implementation**: Python-based with Keycloak admin API integration

**`compute/` - Infrastructure Provider** 
- **Purpose**: Compute resource management
- **Namespace**: `ITL.Compute`
- **Resource Types**: `instances`, `networks`, `storage`
- **Implementation**: Provider framework for various compute platforms

### System Flow

```
Client Application
     ↓
ITL ControlPlane SDK Core
     ↓ 
Resource Provider Registry
     ↓
Provider Layer (Concrete Implementation)
     ↓
External Services (Keycloak, Cloud APIs, etc.)
```

## Component Relationships

### Core Dependencies:

```
itl_controlplane_sdk/
├── models.py          → Pydantic data structures
├── registry.py        → Provider coordination
├── resource_provider.py → Abstract interfaces
└── __init__.py        → Public API exports

providers/
├── keycloak/          → Identity management
└── compute/           → Infrastructure management
```

### Integration Patterns:

**1. Direct Integration**
```python
from itl_controlplane_sdk import ResourceProviderRegistry
from providers.keycloak.provider import KeycloakProvider

registry = ResourceProviderRegistry()
registry.register_provider("ITL.Identity", "realms", KeycloakProvider())
```

**2. Containerized Integration**  
- Providers deployed as microservices
- Communication via HTTP/gRPC
- Independent scaling and management

### Request Processing Flow:

1. **Client Integration**: Application imports and uses SDK components
2. **SDK Core**: Registry routes requests to appropriate provider
3. **Provider Layer**: Concrete provider executes the operation
4. **Response**: Results returned through SDK interface

## Design Principles

### Separation of Concerns
- **SDK Core**: Business logic and resource management
- **Provider Layer**: Service-specific implementation details
- **Client Layer**: Application-specific usage and integration

### Extensibility
- **Provider Interface**: Common interface allows easy addition of new providers
- **Registry Pattern**: Dynamic provider registration and discovery
- **Modular Design**: Each layer can be modified independently

### Consistency
- **Standardized Models**: Common data structures across all providers
- **ARM Compatibility**: Following Azure Resource Manager patterns
- **Error Handling**: Consistent error responses and logging

### Type Safety
- **Pydantic Models**: Full type validation and serialization
- **Abstract Base Classes**: Enforced provider interface contracts
- **Static Typing**: Enhanced IDE support and error prevention

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