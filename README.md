# ITL ControlPlane SDK

The core SDK framework for ITL ControlPlane, providing resource management capabilities without dependencies on external metadata systems.

## Features

- **Resource Provider Registry**: Core framework for registering and managing resource providers
- **Resource Provider Base Classes**: Abstract base classes for implementing custom resource providers  
- **Data Models**: Comprehensive data models for resources, requests, and responses using Pydantic
- **Clean Architecture**: Independent component with minimal dependencies
- **Provider Isolation**: Support for containerized and standalone provider deployments
- **Async Support**: Built-in support for asynchronous resource operations
- **Type Safety**: Full type hints and validation using Pydantic models
- **Core Models**: Shared models for common resource types and configurations
- **Hybrid Resource IDs**: Both human-readable path-based IDs and globally unique GUIDs for maximum flexibility

## Installation

```bash
pip install itl-controlplane-sdk
```

For development:
```bash
git clone https://github.com/ITlusions/ITL.ControlPlane.SDK.git
cd ITL.ControlPlane.SDK
pip install -e .
```

## Quick Start

```python
from itl_controlplane_sdk import (
    ResourceProviderRegistry, 
    ResourceProvider, 
    ResourceRequest,
    ResourceResponse,
    ProvisioningState,
    generate_resource_id
)

# Initialize the registry
registry = ResourceProviderRegistry()

# Create a custom provider
class MyResourceProvider(ResourceProvider):
    def __init__(self):
        super().__init__("MyProvider")
        self.supported_resource_types = ["myresourcetype"]
    
    async def create_or_update_resource(self, request: ResourceRequest) -> ResourceResponse:
        # Generate a proper resource ID
        resource_id = generate_resource_id(
            subscription_id=request.subscription_id,
            resource_group=request.resource_group,
            provider_namespace=request.provider_namespace,
            resource_type=request.resource_type,
            resource_name=request.resource_name
        )
        
        # Create response with both path-based ID and auto-generated GUID
        return ResourceResponse(
            id=resource_id,
            name=request.resource_name,
            type=f"{request.provider_namespace}/{request.resource_type}",
            location=request.location,
            properties=request.body.get("properties", {}),
            provisioning_state=ProvisioningState.SUCCEEDED
            # resource_guid is automatically generated for global uniqueness!
        )
    
    async def get_resource(self, resource_type: str, resource_name: str) -> ResourceResponse:
        # Implementation here  
        pass
    
    async def delete_resource(self, resource_type: str, resource_name: str) -> bool:
        # Implementation here
        return True
    
    async def list_resources(self, resource_type: str, **filters) -> list:
        # Implementation here
        return []

# Register the provider
provider = MyResourceProvider()
registry.register_provider("MyProvider", provider)
```

## Project Structure

```
ITL.ControlPlane.SDK/
├── src/
│   └── itl_controlplane_sdk/        # Core SDK package
│       ├── __init__.py              # Package exports
│       ├── models.py                # Pydantic data models
│       ├── registry.py              # Provider registry
│       ├── resource_provider.py     # Base provider class
│       ├── base/                    # Base classes and utilities
│       └── common/                  # Common utilities and shared models
│           └── models/              # Shared model definitions
│               └── core/            # Core resource models
│                   ├── base.py      # Base resource classes
│                   ├── config.py    # Configuration models
│                   ├── resources.py # Resource data classes
│                   └── __init__.py  # Model exports
├── examples/                        # Usage examples
│   └── quickstart.py               # Getting started example
├── .github/                        # CI/CD workflows
│   ├── workflows/                  # GitHub Actions
│   └── PYPI_SETUP.md              # PyPI configuration guide
├── test_sdk.py                     # SDK validation tests
├── pyproject.toml                  # Package configuration
├── ARCHITECTURE.md                 # Architecture documentation
├── PIPELINE_SETUP.md              # CI/CD pipeline setup
├── AUTOMATED_VERSIONING.md        # Versioning documentation
└── VERSIONING_UPDATE.md           # Version update guide
```

## Architecture

The SDK follows a clean architecture with clear separation of concerns:

- **Registry**: Central registration and management of resource providers with thread-safe operations
- **Providers**: Abstract base classes and interfaces for implementing resource providers  
- **Models**: Pydantic-based data models for requests, responses, and resource metadata with full validation
- **Base Classes**: Common base classes and utilities for provider implementations
- **Common Models**: Shared model definitions for core resources (ResourceGroup, Deployment, etc.)
- **Isolation**: Support for standalone provider deployments with independent lifecycles
- **Type Safety**: Comprehensive type hints and runtime validation

## Related Components

This SDK is part of the ITL ControlPlane ecosystem. Other components have been separated into independent repositories for focused development:

- **ITL.ControlPlane.API**: REST API layer (separate repository)
- **ITL.ControlPlane.GraphDB**: Graph database for metadata storage (separate repository)
- **ITL.ControlPlane.ResourceProvider.Core**: Core resource provider for Azure-like resources
- **ITL.ControlPlane.ResourceProvider.IAM**: Identity and access management provider (Keycloak)
- **ITL.ControlPlane.ResourceProvider.Compute**: Compute resource provider for VMs and containers

## Provider Examples

The ITL ControlPlane ecosystem includes several reference provider implementations:

- **Core Provider**: Manages resource groups, subscriptions, deployments, and policies
- **IAM Provider**: Integrates with Keycloak for identity and access management  
- **Compute Provider**: Manages virtual machines and compute resources

These providers demonstrate best practices for using the SDK's common models and base classes.

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

To create a new resource provider:

1. **Inherit from ResourceProvider**: Extend the base `ResourceProvider` class
2. **Implement required methods**: `create_or_update_resource`, `get_resource`, `delete_resource`, `list_resources`
3. **Define resource types**: Set `supported_resource_types` in your provider
4. **Use common models**: Leverage shared models from `itl_controlplane_sdk.common.models.core`
5. **Register with registry**: Use `ResourceProviderRegistry.register_provider()`
6. **Add validation**: Use Pydantic models for request/response validation

See the [examples/quickstart.py](./examples/quickstart.py) for a complete example.

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
- **Pydantic**: ≥2.0.0 for data validation and serialization
- **typing-extensions**: ≥4.0.0 for enhanced type hints
- **Python**: ≥3.8 (tested on 3.8-3.12)

### Recent Updates
- Enhanced type safety with comprehensive Pydantic models
- Added shared common models for core resources
- Improved provider registration and management
- Added base classes and common utilities for provider development
- Streamlined async operations with proper type hints
- Updated documentation and examples with real-world usage patterns

## Documentation

- [Architecture Documentation](./ARCHITECTURE.md) - Detailed architecture overview
- [Resource ID Strategy](./RESOURCE_ID_STRATEGY.md) - Hybrid path + GUID approach for resource identification
- [CI/CD Pipeline Setup](./PIPELINE_SETUP.md) - Complete pipeline documentation
- [Automated Versioning](./AUTOMATED_VERSIONING.md) - Git tag-based version management
- [Versioning Update Guide](./VERSIONING_UPDATE.md) - Version update procedures
- [PyPI Setup Guide](./.github/PYPI_SETUP.md) - Package publishing configuration

## Support and Contributing

For questions, issues, or contributions:

1. **Issues**: Report bugs or feature requests via GitHub Issues
2. **Development**: Follow the development setup above
3. **Testing**: Ensure all tests pass before submitting PRs
4. **Documentation**: Update documentation for any API changes
5. **Providers**: Use the common models and base classes for consistency

## License

This project is licensed under the terms specified in the LICENSE file.