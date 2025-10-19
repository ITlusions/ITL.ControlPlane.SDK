# ITL ControlPlane SDK - Architecture Documentation

## Overview

The ITL ControlPlane SDK implements a clean 3-layer architecture that provides clear separation of concerns, making the system maintainable, testable, and extensible.

## 3-Layer Architecture

### Layer 1: API Layer (`src/api_layer/`)

The API layer provides RESTful endpoints following ARM (Azure Resource Manager) patterns and handles HTTP request/response processing.

#### Components:

**`server.py` - FastAPI Application Factory**
- **Purpose**: Creates and configures the FastAPI application
- **Responsibilities**: 
  - Application initialization and configuration
  - CORS middleware setup
  - Route registration
  - Global error handling
- **Key Functions**: `create_app()`

**`routes/` - API Route Handlers**
- **`health_routes.py`**: Health check and system status endpoints
- **`provider_routes.py`**: Provider information and capabilities endpoints  
- **`resource_routes.py`**: Core CRUD operations for resources
- **Responsibilities**:
  - HTTP request/response handling
  - Request validation and parsing
  - Delegating to SDK core for business logic

**`middleware/` - Request Processing**
- **`logging.py`**: Request/response logging and correlation IDs
- **Responsibilities**:
  - Request tracing and correlation
  - Performance monitoring
  - Error logging

**`schemas/` - API Data Models**
- **`api_models.py`**: Pydantic models for API requests/responses
- **Responsibilities**:
  - Input validation and serialization
  - API documentation generation
  - Type safety for HTTP layer

### Layer 2: SDK Core (`src/controlplane_sdk/`)

The core SDK layer provides the foundational framework for resource management and provider coordination.

#### Components:

**`models.py` - Core Data Models**
- **Purpose**: Defines the core data structures used throughout the system
- **Key Models**:
  - `ResourceRequest`: Standardized resource operation requests
  - `ResourceResponse`: Unified resource operation responses  
  - `ResourceListResponse`: Resource listing responses
  - `ProvisioningState`: Resource provisioning status enumeration
- **Responsibilities**:
  - Data model definitions
  - Validation rules
  - Serialization support

**`resource_provider.py` - Provider Base Class**
- **Purpose**: Abstract base class that all resource providers must implement
- **Key Classes**: `ResourceProvider`
- **Responsibilities**:
  - Define provider interface contract
  - Common validation logic
  - Resource ID generation
  - Error handling patterns
- **Methods**:
  - `create_or_update_resource()`: Resource creation/updates
  - `get_resource()`: Resource retrieval
  - `list_resources()`: Resource listing
  - `delete_resource()`: Resource deletion
  - `execute_action()`: Custom resource actions

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
  - Namespace-based routing
  - Provider capability discovery

### Layer 3: Provider Layer (`providers/`)

The provider layer contains concrete implementations of resource providers for specific services and technologies.

#### Provider Structure:

**`keycloak/` - Identity Provider**
- **`provider.py`**: Keycloak resource provider implementation
- **Supported Resources**:
  - Realms: Keycloak realm management
  - Users: User account management
  - Clients: OAuth2/OIDC client configuration
- **Capabilities**:
  - Realm creation and configuration
  - User lifecycle management
  - Client application setup

**`compute/` - Compute Provider**  
- **`vm_provider.py`**: Virtual machine resource provider
- **Supported Resources**:
  - Virtual Machines: VM lifecycle management
- **Capabilities**:
  - VM creation with configurable specifications
  - Power state management (start, stop, restart, deallocate)
  - Storage and network configuration
  - Resource monitoring and reporting

## Data Flow Architecture

```
HTTP Request
     ↓
API Layer (FastAPI Routes)
     ↓
SDK Core (Registry + Models)
     ↓  
Provider Layer (Concrete Implementation)
     ↓
External Services (Keycloak, Cloud APIs, etc.)
```

### Request Processing Flow:

1. **HTTP Request**: Client sends ARM-compatible REST request
2. **API Layer**: FastAPI routes parse and validate the request
3. **SDK Core**: Registry routes request to appropriate provider
4. **Provider Layer**: Concrete provider executes the operation
5. **Response**: Results flow back through the layers to client

## Design Principles

### Separation of Concerns
- **API Layer**: Only handles HTTP protocol concerns
- **SDK Core**: Business logic and resource management
- **Provider Layer**: Service-specific implementation details

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
- Configurable API server settings (host, port, CORS)
- Logging levels and output formatting

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
- **API Tests**: End-to-end HTTP request processing
- **Provider Integration**: Real service interactions
- **Cross-Provider Tests**: Multi-provider scenarios

### Contract Testing
- **Provider Interface**: Ensure all providers implement required methods
- **API Compatibility**: ARM pattern compliance
- **Error Handling**: Consistent error responses

This architecture provides a robust foundation for building cloud resource management systems with clear separation of concerns, extensibility, and maintainability.
- **Purpose**: FastAPI route definitions and request handling
- **Responsibilities**:
  - Define all API endpoints (info, plan, apply, destroy, jobs)
  - Request validation and response formatting
  - Error handling for operations
  - Background task coordination
- **Key Classes**: `ProviderRouter`
- **Endpoints**: `/info`, `/plan`, `/apply`, `/destroy`, `/jobs/{job_id}`

#### `health.py` - Health and Monitoring
- **Purpose**: Health checks, readiness probes, and system status endpoints
- **Responsibilities**:
  - Health endpoint implementation
  - Readiness checks with provider validation
  - Uptime tracking and system information
  - Provider capability reporting
- **Key Classes**: `HealthManager`
- **Endpoints**: `/health`, `/ready`

#### `metrics.py` - Prometheus Metrics
- **Purpose**: Prometheus metrics collection and reporting
- **Responsibilities**:
  - Request counting and in-flight tracking
  - Error counting by operation and type
  - Duration tracking for operations
  - Metrics response generation
- **Key Classes**: `MetricsManager`
- **Metrics**: Requests, in-flight, errors, duration

#### `registry.py` - Provider Registration
- **Purpose**: Self-registration with core control plane
- **Responsibilities**:
  - Background registration with retry logic
  - Provider manifest building
  - HTTP client management with timeouts
  - Registration status tracking
- **Key Classes**: `RegistryClient`
- **Features**: Background threading, retry mechanisms, error handling

#### `tasks.py` - Task and Job Management
- **Purpose**: Background task execution and job tracking
- **Responsibilities**:
  - Asynchronous task execution
  - Task status and result tracking
  - Task lifecycle management (pending, running, completed, failed)
  - Memory management with task cleanup
- **Key Classes**: `TaskManager`, `OperationExecutor`, `TaskResult`
- **Features**: UUID task IDs, background execution, result persistence

#### `exceptions.py` - Error Handling
- **Purpose**: Centralized exception handling and error responses
- **Responsibilities**:
  - Custom exception classes for different error types
  - Global exception handlers for FastAPI
  - Structured error responses with request IDs
  - Error logging and metrics integration
- **Key Classes**: `ErrorHandler`, `ProviderError`, `PlanError`, `ApplyError`, `DestroyError`, `ValidationError`

### Module Dependencies

```
server.py (Main Orchestrator)
├── config.py (Configuration)
├── routes.py (API Routes)
│   ├── tasks.py (Task Management)
│   └── exceptions.py (Error Handling)
├── health.py (Health Checks)
├── metrics.py (Prometheus Metrics)
├── registry.py (Provider Registration)
└── exceptions.py (Global Error Handling)
```

## Benefits of Separation

### 1. **Separation of Concerns**
- Each module has a single, well-defined responsibility
- Easier to understand and modify individual components
- Reduced coupling between different aspects of the system

### 2. **Improved Maintainability**
- Changes to metrics don't affect routing logic
- Configuration changes are centralized
- Error handling is consistent across all modules

### 3. **Better Testability**
- Individual modules can be unit tested in isolation
- Mock dependencies easily for focused testing
- Clear interfaces between components

### 4. **Enhanced Reusability**
- Components can be reused in other projects
- Metrics and health modules are framework-agnostic
- Configuration module is environment-aware

### 5. **Scalability**
- Easy to add new features to specific modules
- Background task system supports async operations
- Modular architecture supports horizontal scaling

## Configuration Example

```python
from controlplane_sdk import ProviderServer, config_manager

# Configure via environment or code
config_manager.update_config(
    provider_name="my-provider",
    host="0.0.0.0",
    port=8080,
    control_plane_url="http://control-plane:8080/api/v1/providers",
    metrics_enabled=True,
    log_level="INFO"
)

# Create server with provider implementation
server = ProviderServer(my_provider_impl)
app = server.create_fastapi_app()
```

## Usage Patterns

### 1. **Standard Server Creation**
```python
from controlplane_sdk import ProviderServer

server = ProviderServer(provider_impl, core_registry_url)
app = server.create_fastapi_app()
```

### 2. **Direct Component Usage**
```python
from controlplane_sdk import MetricsManager, TaskManager

# Use metrics independently
MetricsManager.increment_requests('plan')

# Use task manager independently
task_manager = TaskManager()
task_id = await task_manager.execute_task('apply', my_async_func)
```

### 3. **Custom Error Handling**
```python
from controlplane_sdk import PlanError, ValidationError

raise PlanError("Terraform plan failed", details={'exit_code': 1})
raise ValidationError("Invalid configuration", field='instance.name')
```

## File Structure

```
src/controlplane_sdk/
├── __init__.py          # Package exports and API
├── server.py            # Main ProviderServer orchestrator
├── config.py            # Configuration management
├── routes.py            # FastAPI route definitions
├── health.py            # Health and readiness endpoints
├── metrics.py           # Prometheus metrics collection
├── registry.py          # Provider registration with control plane
├── tasks.py             # Background task and job management
├── exceptions.py        # Error handling and custom exceptions
├── terraform_engine.py  # (Existing) Terraform execution engine
└── loader.py            # (Existing) Provider discovery and loading
```

## Migration Guide

### For Existing Users
The main `ProviderServer` interface remains unchanged:
```python
# This still works exactly the same
server = ProviderServer(provider_impl, registry_url)
app = server.create_fastapi_app()
```

### For Advanced Users
New modular components are available:
```python
from controlplane_sdk import (
    ServerConfig, MetricsManager, TaskManager, 
    ProviderRouter, HealthManager, RegistryClient
)

# Use individual components as needed
config = ServerConfig()
task_manager = TaskManager()
router = ProviderRouter(provider_impl)
```

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
python example/keycloak_provider.py

# Run as a server
python example/server_example.py
```

## Future Enhancements

1. **Plugin System**: Module architecture supports easy plugin integration
2. **Caching Layer**: Add caching module for plan/state caching
3. **Observability**: Enhanced tracing and logging modules
4. **Security**: Authentication and authorization modules
5. **Testing**: Test utilities and mock implementations

This modular architecture provides a solid foundation for the ITL.ControlPanel.SDK to grow and evolve while maintaining clean code organization and developer experience.