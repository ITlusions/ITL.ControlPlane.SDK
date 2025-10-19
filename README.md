# ITL ControlPlane SDK

The core SDK framework for ITL ControlPlane, providing resource management capabilities without dependencies on external metadata systems.

## Features

- **Resource Provider Registry**: Core framework for registering and managing resource providers
- **Resource Provider Base Classes**: Abstract base classes for implementing custom resource providers  
- **Data Models**: Comprehensive data models for resources, requests, and responses
- **Clean Architecture**: Independent component with minimal dependencies
- **Provider Isolation**: Support for containerized provider deployments

## Installation

```bash
pip install itl-controlplane-sdk
```

For development:
```bash
git clone <repository-url>
cd ITL.ControlPlane.SDK
pip install -e .
```

## Quick Start

```python
from itl_controlplane_sdk import ResourceProviderRegistry, ResourceProvider

# Initialize the registry
registry = ResourceProviderRegistry()

# Create a custom provider
class MyResourceProvider(ResourceProvider):
    def __init__(self):
        super().__init__("MyProvider")
    
    async def create_or_update_resource(self, request):
        # Implementation here
        pass
    
    async def get_resource(self, resource_id):
        # Implementation here  
        pass
    
    async def delete_resource(self, resource_id):
        # Implementation here
        pass
    
    async def list_resources(self, resource_group):
        # Implementation here
        pass

# Register the provider
provider = MyResourceProvider()
registry.register_provider("myprovider", "myresourcetype", provider)
```

## Project Structure

```
ITL.ControlPlane.SDK/
├── src/
│   └── itl_controlplane_sdk/        # Core SDK package
│       ├── __init__.py              # Package exports
│       ├── models.py                # Data models
│       ├── registry.py              # Provider registry
│       └── resource_provider.py     # Base provider class
├── providers/                       # Isolated provider implementations
│   ├── keycloak/                    # Keycloak identity provider
│   └── compute/                     # Compute resource providers
├── examples/                        # Usage examples
└── docs/                           # Documentation
```

## Architecture

The SDK follows a clean architecture with clear separation of concerns:

- **Registry**: Central registration and management of resource providers
- **Providers**: Base classes and interfaces for implementing resource providers  
- **Models**: Data models for requests, responses, and resource metadata
- **Isolation**: Support for standalone provider deployments

## Related Components

This SDK is designed to work with other ITL ControlPlane components:

- **ITL.ControlPlane.API**: REST API layer providing HTTP endpoints
- **ITL.ControlPlane.GraphDB**: Graph database for metadata storage and analytics

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run validation tests
python test_sdk.py

# Format code
black src/

# Type checking  
mypy src/
```

## CI/CD Pipeline

The repository includes a comprehensive CI/CD pipeline for automated testing and publishing:

- **Continuous Integration**: Automated testing on Python 3.8-3.12
- **Package Publishing**: Automatic PyPI releases for version tags
- **Security Scanning**: Dependency and code vulnerability checks
- **Provider Testing**: Validation of provider implementations
- **Automated Versioning**: Git tag-based version management (no manual editing!)

See [PIPELINE_SETUP.md](./PIPELINE_SETUP.md) for complete pipeline documentation and [AUTOMATED_VERSIONING.md](./AUTOMATED_VERSIONING.md) for version management details.

## Documentation

- [Provider Isolation Guide](./PROVIDER_ISOLATION.md) - Deploying providers as standalone services
- [Graph Database Configuration](./GRAPH_DATABASE_CONFIG.md) - Metadata storage integration
- [Architecture Documentation](./ARCHITECTURE.md) - Detailed architecture overview

## License

This project is licensed under the terms specified in the LICENSE file.