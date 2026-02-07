"""
Identity Provider Factory Example

Demonstrates the pluggable identity provider pattern:
1. Registering identity provider implementations
2. Creating providers from configuration
3. Singleton pattern (create_or_get)
4. Security best practices for secrets handling
5. Multi-provider switching (Keycloak, Azure AD)
6. Using convenience functions

The factory allows switching between identity systems
(Keycloak, Azure AD, Okta) without changing control plane code.
"""

import os
from typing import Dict, Any, List, Optional

from itl_controlplane_sdk.identity.identity_provider_base import IdentityProvider
from itl_controlplane_sdk.identity.identity_provider_factory import (
    IdentityProviderFactory,
    get_factory,
    register_provider,
    create_provider,
    get_or_create_provider,
)


# ============================================================================
# STEP 1: Define custom identity provider implementations
# ============================================================================

class MockKeycloakProvider(IdentityProvider):
    """
    Mock Keycloak identity provider for demonstration.
    
    In production, this would use python-keycloak to talk to
    a real Keycloak server.
    """

    def __init__(self, provider_name: str, config: Dict[str, Any]):
        super().__init__(provider_name, config)
        self.server_url = config.get("server_url", "http://localhost:8080")
        self.realm = config.get("realm", "master")
        self._connected = True
        print(f"   Keycloak connected: {self.server_url} (realm: {self.realm})")

    async def create_realm(self, realm_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new Keycloak realm."""
        return {"realm": realm_spec.get("name"), "enabled": True, "provider": "keycloak"}

    async def delete_realm(self, realm_name: str) -> bool:
        """Delete a Keycloak realm."""
        return True

    async def create_user(self, realm: str, user_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Create a user in a realm."""
        return {"username": user_spec.get("username"), "realm": realm, "provider": "keycloak"}

    async def shutdown(self) -> None:
        """Clean up connections."""
        self._connected = False
        print(f"   Keycloak disconnected")


class MockAzureADProvider(IdentityProvider):
    """
    Mock Azure AD identity provider for demonstration.
    
    In production, this would use microsoft-graph-sdk.
    """

    def __init__(self, provider_name: str, config: Dict[str, Any]):
        super().__init__(provider_name, config)
        self.tenant_id = config.get("tenant_id", "default-tenant")
        self._connected = True
        print(f"   Azure AD connected: tenant={self.tenant_id}")

    async def create_realm(self, realm_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Create (simulated via Azure AD app registration)."""
        return {"tenant": self.tenant_id, "app": realm_spec.get("name"), "provider": "azure_ad"}

    async def delete_realm(self, realm_name: str) -> bool:
        return True

    async def create_user(self, realm: str, user_spec: Dict[str, Any]) -> Dict[str, Any]:
        return {"username": user_spec.get("username"), "tenant": self.tenant_id, "provider": "azure_ad"}

    async def shutdown(self) -> None:
        self._connected = False
        print(f"   Azure AD disconnected")


# ============================================================================
# EXAMPLE 1: Basic factory registration and usage
# ============================================================================

def example_1_basic_factory():
    """Register providers and create instances."""
    print("=" * 60)
    print("EXAMPLE 1: Basic Factory Usage")
    print("=" * 60)

    factory = IdentityProviderFactory()

    # Register provider implementations
    factory.register("keycloak", MockKeycloakProvider)
    factory.register("azure_ad", MockAzureADProvider)

    print(f"\nRegistered providers: {factory.get_registered_providers()}")

    # Create a Keycloak provider
    print(f"\nCreating Keycloak provider:")
    keycloak = factory.create("keycloak", {
        "server_url": "https://auth.mycompany.com",
        "realm": "production",
        "client_id": "control-plane",
    })
    print(f"   Provider name: {keycloak.provider_name}")
    print(f"   Server URL:    {keycloak.server_url}")

    # Create an Azure AD provider
    print(f"\nCreating Azure AD provider:")
    azure = factory.create("azure_ad", {
        "tenant_id": "550e8400-e29b-41d4-a716",
        "client_id": "app-registration-001",
    })
    print(f"   Provider name: {azure.provider_name}")
    print(f"   Tenant ID:     {azure.tenant_id}")

    # Both implement the same interface!
    print(f"\nSame interface, different backends:")
    print(f"   Keycloak type: {type(keycloak).__name__}")
    print(f"   Azure AD type: {type(azure).__name__}")
    print(f"   Both are IdentityProvider: {isinstance(keycloak, IdentityProvider) and isinstance(azure, IdentityProvider)}")


# ============================================================================
# EXAMPLE 2: Singleton pattern (create_or_get)
# ============================================================================

def example_2_singleton():
    """Demonstrate singleton caching of provider instances."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Singleton Pattern")
    print("=" * 60)

    factory = IdentityProviderFactory()
    factory.register("keycloak", MockKeycloakProvider)

    config = {
        "server_url": "https://auth.prod.com",
        "realm": "production",
    }

    # First call: creates new instance
    print(f"\nFirst call (creates new):")
    provider1 = factory.create_or_get("keycloak", config)
    print(f"   Instance ID: {id(provider1)}")

    # Second call: returns cached instance
    print(f"\nSecond call (returns cached):")
    provider2 = factory.create_or_get("keycloak", config)
    print(f"   Instance ID: {id(provider2)}")
    print(f"   Same instance: {provider1 is provider2}")

    # Check if instance exists without creating
    existing = factory.get_instance("keycloak")
    missing = factory.get_instance("okta")
    print(f"\nGet existing: {existing is not None}")
    print(f"Get missing:  {missing is None}")


# ============================================================================
# EXAMPLE 3: Security - secrets handling
# ============================================================================

def example_3_security():
    """Show secure vs insecure configuration patterns."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Security Best Practices")
    print("=" * 60)

    factory = IdentityProviderFactory()
    factory.register("keycloak", MockKeycloakProvider)

    # SAFE: Load secrets from environment variables
    print(f"\nSAFE: Secrets from environment variables")
    safe_config = {
        "server_url": os.getenv("KEYCLOAK_URL", "https://auth.example.com"),
        "realm": os.getenv("KEYCLOAK_REALM", "production"),
        "client_id": os.getenv("KEYCLOAK_CLIENT_ID", "control-plane"),
        "client_secret": os.getenv("KEYCLOAK_CLIENT_SECRET", "<from-env>"),
    }
    print(f"   server_url:     {safe_config['server_url']}")
    print(f"   client_secret:  {'*' * 12} (from env)")
    provider = factory.create("keycloak", safe_config)

    # UNSAFE: Hardcoded secrets (DO NOT DO THIS)
    print(f"\nUNSAFE patterns (never do this):")
    print(f'   client_secret: "super-secret-key"     ← WRONG: hardcoded')
    print(f'   password: "admin123"                   ← WRONG: in source code')
    print(f'   api_key: "sk-1234567890abcdef"         ← WRONG: in config file')

    # SAFE alternatives
    print(f"\nSAFE alternatives:")
    print(f"   os.getenv('SECRET_KEY')                ← Environment variable")
    print(f"   boto3.client('secretsmanager')         ← AWS Secrets Manager")
    print(f"   SecretClient(vault_url, credential)    ← Azure Key Vault")
    print(f"   hvac.Client(url='http://vault:8200')   ← HashiCorp Vault")


# ============================================================================
# EXAMPLE 4: Provider switching (environment-based)
# ============================================================================

def example_4_provider_switching():
    """Switch between providers based on environment configuration."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Provider Switching")
    print("=" * 60)

    factory = IdentityProviderFactory()
    factory.register("keycloak", MockKeycloakProvider)
    factory.register("azure_ad", MockAzureADProvider)

    # Simulate environment-based selection
    environments = {
        "development": {
            "provider": "keycloak",
            "config": {"server_url": "http://localhost:8080", "realm": "dev"},
        },
        "staging": {
            "provider": "keycloak",
            "config": {"server_url": "https://auth.staging.com", "realm": "staging"},
        },
        "production": {
            "provider": "azure_ad",
            "config": {"tenant_id": "prod-tenant-uuid", "client_id": "prod-app"},
        },
    }

    print(f"\nProvider per environment:")
    for env_name, env_config in environments.items():
        provider_type = env_config["provider"]
        config = env_config["config"]

        print(f"\n   {env_name}:")
        provider = factory.create(provider_type, config)
        print(f"      Provider:  {provider_type}")
        print(f"      Instance:  {type(provider).__name__}")

    # The control plane code stays the same regardless of provider!
    print(f"\nKey benefit:")
    print(f"   → Same control plane code works with any provider")
    print(f"   → Switch by changing config, not code")
    print(f"   → Factory handles instantiation and validation")


# ============================================================================
# EXAMPLE 5: Convenience functions (module-level)
# ============================================================================

def example_5_convenience_functions():
    """Use module-level convenience functions for quick setup."""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Convenience Functions")
    print("=" * 60)

    # Register with global factory
    register_provider("keycloak", MockKeycloakProvider)
    register_provider("azure_ad", MockAzureADProvider)

    # Get global factory
    factory = get_factory()
    print(f"\nGlobal factory providers: {factory.get_registered_providers()}")

    # Create provider via convenience function
    print(f"\nCreate via convenience function:")
    provider = create_provider("keycloak", {
        "server_url": "https://auth.example.com",
        "realm": "demo",
    })
    print(f"   Type: {type(provider).__name__}")

    # Get or create singleton
    print(f"\nGet-or-create (singleton):")
    p1 = get_or_create_provider("keycloak", {"server_url": "https://auth.example.com", "realm": "demo"})
    p2 = get_or_create_provider("keycloak", {"server_url": "https://auth.example.com", "realm": "demo"})
    print(f"   Same instance: {p1 is p2}")

    # Error handling: unknown provider
    print(f"\n Error handling:")
    try:
        create_provider("unknown_provider", {})
    except Exception as e:
        print(f"   Unknown provider: {e}")

    # Error handling: invalid provider class
    try:
        register_provider("bad", str)  # str is not an IdentityProvider subclass
    except Exception as e:
        print(f"   Invalid class: {e}")


if __name__ == "__main__":
    example_1_basic_factory()
    example_2_singleton()
    example_3_security()
    example_4_provider_switching()
    example_5_convenience_functions()
    print("\nAll Identity Provider Factory examples completed!")
