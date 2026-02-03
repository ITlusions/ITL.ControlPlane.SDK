"""
Identity Provider Factory - pluggable provider selection.

Allows switching between identity providers (Keycloak, Azure AD, Okta, etc.)
without changing control plane code.

Design:
- IdentityProviderFactory: Creates provider instances based on configuration
- Provider registration: Register new providers dynamically
- Environment-based selection: IDENTITY_PROVIDER env var chooses implementation
- Dependency injection: Registry holds singleton provider instance

SECURITY: Secrets Management
This factory creates identity providers that typically require authentication.
It is CRITICAL to never pass client secrets, API keys, or passwords in plain text
through the config dictionary. Use only secure sources:

1. Environment variables (recommended):
   config = {
       "type": "keycloak",
       "server_url": "http://localhost:8080",
       "client_secret": os.getenv("KEYCLOAK_CLIENT_SECRET")
   }

2. AWS Secrets Manager:
   client = boto3.client("secretsmanager")
   secret = client.get_secret_value(SecretId="keycloak-client-secret")
   config = {..., "client_secret": secret["SecretString"]}

3. Azure Key Vault:
   from azure.identity import DefaultAzureCredential
   from azure.keyvault.secrets import SecretClient
   client = SecretClient(vault_url=vault_url, credential=DefaultAzureCredential())
   config = {..., "client_secret": client.get_secret("keycloak-client-secret").value}

4. HashiCorp Vault:
   import hvac
   client = hvac.Client(url="http://vault:8200")
   config = {..., "client_secret": client.secrets.kv.v2.read_secret_version(path="keycloak")}

NEVER commit secrets to version control or pass hardcoded values.
"""

from typing import Any, Dict, Optional, Type
import logging

from itl_controlplane_sdk.core.exceptions import ResourceProviderError
from itl_controlplane_sdk.identity.identity_provider_base import IdentityProvider

logger = logging.getLogger(__name__)

# Create convenience alias for ConfigurationError
ConfigurationError = ResourceProviderError


class IdentityProviderFactory:
    """
    Factory for creating and managing identity provider instances.

    Supports:
    - Dynamic provider registration
    - Factory method for creating instances
    - Validation of configuration
    - Singleton pattern (one provider per environment)

    SECURITY WARNING - Secrets in Configuration:
    Never pass client_secret, api_key, or password in plain text to config dict.
    These MUST come from secure sources only:

    - Environment variables: os.getenv('KEYCLOAK_CLIENT_SECRET')
    - AWS Secrets Manager: aws_secretsmanager.get_secret_value()
    - Azure Key Vault: azure.identity.SecretClient()
    - HashiCorp Vault: hvac.Client()

    If config contains secrets, they must be loaded from secure sources at runtime,
    not hardcoded or embedded in deployment manifests.

    Example Usage (SAFE - secrets from environment):
        factory = IdentityProviderFactory()
        factory.register("keycloak", KeycloakIdentityProvider)

        config = {
            "type": "keycloak",
            "server_url": os.getenv("KEYCLOAK_URL"),
            "realm": os.getenv("KEYCLOAK_REALM"),
            "client_id": os.getenv("KEYCLOAK_CLIENT_ID"),
            "client_secret": os.getenv("KEYCLOAK_CLIENT_SECRET")  # From env, never hardcoded
        }
        provider = factory.create(config["type"], config)

    Example Usage (UNSAFE - DO NOT USE):
        # NEVER DO THIS:
        config = {
            "type": "keycloak",
            "server_url": "http://localhost:8080",
            "client_secret": "super-secret-key-12345"  # WRONG! Hardcoded secret
        }
        provider = factory.create(config)  # SECURITY RISK
    """

    def __init__(self):
        """Initialize factory."""
        self._providers: Dict[str, Type[IdentityProvider]] = {}
        self._instances: Dict[str, IdentityProvider] = {}

    def register(
        self, provider_type: str, provider_class: Type[IdentityProvider]
    ) -> None:
        """
        Register a provider implementation.

        Args:
            provider_type: Provider type identifier (e.g., "keycloak")
            provider_class: Provider class (must extend IdentityProvider)

        Raises:
            ConfigurationError: Invalid provider class
        """
        if not issubclass(provider_class, IdentityProvider):
            raise ConfigurationError(
                f"Provider class must extend IdentityProvider: {provider_class.__name__}",
                context={"provider_type": provider_type},
            )
        self._providers[provider_type.lower()] = provider_class

    def get_registered_providers(self) -> list:
        """Get list of registered provider types."""
        return list(self._providers.keys())

    def create(
        self, provider_type: str, config: Dict[str, Any]
    ) -> IdentityProvider:
        """
        Create provider instance.

        Creates a new provider instance configured with the provided config dict.
        Does NOT create singleton - use create_or_get() for that.

        SECURITY: Validate that secrets in config come from secure sources
        (environment variables or secrets manager), never hardcoded strings.

        Args:
            provider_type: Provider type (must be registered)
            config: Provider configuration

        Returns:
            Provider instance

        Raises:
            ConfigurationError: Provider type not registered or config invalid
        """
        provider_type = provider_type.lower()

        # SECURITY CHECK: Log warning if config contains potential secrets
        secret_keys = {'client_secret', 'api_key', 'password', 'token', 'secret'}
        found_secrets = [k for k in config.keys() if k.lower() in secret_keys]
        if found_secrets:
            logger.warning(
                "Provider config contains potential secrets. Ensure they come from "
                "secure sources (env vars or secrets manager), not hardcoded values.",
                extra={
                    'provider_type': provider_type,
                    'secret_keys': found_secrets,
                    'recommendation': 'Load secrets at runtime via os.getenv() or '
                                     'AWS/Azure/Vault APIs, never hardcode'
                }
            )

        if provider_type not in self._providers:
            available = ", ".join(self.get_registered_providers())
            raise ConfigurationError(
                f"Unknown identity provider: {provider_type}. Available: {available}",
                context={
                    "provider_type": provider_type,
                    "available_providers": self.get_registered_providers(),
                },
            )

        provider_class = self._providers[provider_type]
        try:
            provider = provider_class(provider_type, config)
            return provider
        except Exception as e:
            raise ConfigurationError(
                f"Failed to instantiate provider {provider_type}: {str(e)}",
                context={"provider_type": provider_type},
                original_error=e,
            )

    def create_or_get(
        self, provider_type: str, config: Dict[str, Any]
    ) -> IdentityProvider:
        """
        Get or create singleton provider instance.

        Caches instances by provider type. If provider already created with
        same type, returns cached instance.

        Args:
            provider_type: Provider type
            config: Provider configuration

        Returns:
            Provider instance (singleton per type)

        Raises:
            ConfigurationError: Provider creation failed
        """
        provider_type = provider_type.lower()

        if provider_type in self._instances:
            return self._instances[provider_type]

        provider = self.create(provider_type, config)
        self._instances[provider_type] = provider
        return provider

    def get_instance(self, provider_type: str) -> Optional[IdentityProvider]:
        """
        Get cached provider instance if it exists.

        Args:
            provider_type: Provider type

        Returns:
            Provider instance or None if not created yet
        """
        return self._instances.get(provider_type.lower())

    async def shutdown_all(self) -> None:
        """Shutdown all cached provider instances."""
        for provider in self._instances.values():
            try:
                await provider.shutdown()
            except Exception as e:
                # Log but don't fail on shutdown errors
                logger.error(f"Error shutting down provider: {e}")


# Global factory instance
_factory = IdentityProviderFactory()


def get_factory() -> IdentityProviderFactory:
    """Get global factory instance."""
    return _factory


def register_provider(
    provider_type: str, provider_class: Type[IdentityProvider]
) -> None:
    """
    Register a provider with global factory.

    Convenience function for module-level registration.

    Example:
        from itl_controlplane_sdk.identity import register_provider
        from keycloak_identity_provider import KeycloakIdentityProvider

        register_provider("keycloak", KeycloakIdentityProvider)
    """
    _factory.register(provider_type, provider_class)


def create_provider(
    provider_type: str, config: Dict[str, Any]
) -> IdentityProvider:
    """
    Create provider from global factory.

    Convenience function for creating new instances.
    """
    return _factory.create(provider_type, config)


def get_or_create_provider(
    provider_type: str, config: Dict[str, Any]
) -> IdentityProvider:
    """
    Get or create singleton provider from global factory.

    Convenience function.
    """
    return _factory.create_or_get(provider_type, config)
