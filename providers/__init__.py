"""
Provider Implementations for ITL ControlPlane SDK

This package contains concrete implementations of resource providers.

Providers can be used in two ways:
1. Integrated: Import and use directly with the main SDK
2. Isolated: Run as standalone services (see keycloak-provider/ and vm-provider/)
"""

# Integrated providers (original structure)
from .keycloak import KeycloakProvider
from .compute import VirtualMachineProvider

# Isolated providers are available as standalone services in:
# - keycloak-provider/: Standalone Keycloak identity provider
# - vm-provider/: Standalone virtual machine provider

__all__ = [
    'KeycloakProvider',
    'VirtualMachineProvider'
]

# Provider registry information
INTEGRATED_PROVIDERS = {
    'ITL.Identity': {
        'realms': KeycloakProvider,
        'users': KeycloakProvider, 
        'clients': KeycloakProvider
    },
    'ITL.Compute': {
        'virtualMachines': VirtualMachineProvider
    }
}

ISOLATED_PROVIDERS = {
    'keycloak-provider': {
        'namespace': 'ITL.Identity',
        'resources': ['realms', 'users', 'clients'],
        'default_port': 8001,
        'path': './keycloak-provider'
    },
    'vm-provider': {
        'namespace': 'ITL.Compute', 
        'resources': ['virtualMachines'],
        'default_port': 8002,
        'path': './vm-provider'
    }
}