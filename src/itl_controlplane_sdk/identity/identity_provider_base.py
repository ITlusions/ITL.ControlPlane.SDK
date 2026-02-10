"""
Production-grade Identity Provider abstraction for ITL Control Plane.

This abstraction layer allows multiple identity management systems (Keycloak, Azure AD, 
Okta, etc.) to be plugged in without changing control plane code.

Design:
- IdentityProvider: Abstract interface for all identity systems
- Specific implementations: KeycloakIdentityProvider, AzureADIdentityProvider, etc.
- Dependency injection: ProviderRegistry manages which implementation is active
- Consistent error handling: All providers throw same exception hierarchy
- Uniform contracts: All providers implement same methods

Example:
    # Use Keycloak
    identity_provider = KeycloakIdentityProvider(config)
    
    # Use Azure AD instead - same code!
    identity_provider = AzureADIdentityProvider(config)
    
    # Create realm (method signature is identical)
    realm = await identity_provider.create_realm(realm_spec)
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class IdentityProvider(ABC):
    """
    Abstract base class for identity management providers.

    An identity provider handles:
    - Tenant/Realm management (isolation boundaries)
    - User lifecycle (create, read, update, delete)
    - Role and permission management
    - Domain/namespace management
    - Authentication and authorization

    All identity providers must implement this contract to be compatible
    with the control plane. Implementations handle provider-specific details
    (API calls, data models, etc.) transparently to the control plane.

    Design Principles:
    - Provider-agnostic methods (same signature for all implementations)
    - Consistent error handling (ControlPlaneError hierarchy)
    - Async/await for all I/O operations
    - Idempotency (safe to retry)
    - Transaction support for multi-step operations
    - Audit trail support

    Example Usage:
        # Select provider at startup
        if config.identity_provider == "keycloak":
            provider = KeycloakIdentityProvider(config)
        elif config.identity_provider == "azure_ad":
            provider = AzureADIdentityProvider(config)
        else:
            raise ConfigurationError(f"Unknown provider: {config.identity_provider}")

        # Use same interface for all
        realm = await provider.create_realm(spec)
        user = await provider.create_user(realm_id, user_spec)
        await provider.assign_role(realm_id, user_id, role)
    """

    def __init__(self, provider_name: str, config: Dict[str, Any]):
        """
        Initialize identity provider.

        Args:
            provider_name: Human-readable name (e.g., "keycloak", "azure-ad")
            config: Provider-specific configuration dict
        """
        self.provider_name = provider_name
        self.config = config

    # ==================== REALM / TENANT MANAGEMENT ====================

    @abstractmethod
    async def create_realm(self, spec: Any) -> Dict[str, Any]:
        """
        Create a new realm (tenant isolation boundary).

        A realm is the highest-level isolation unit in the identity provider.
        Each organization's tenant maps to one realm.

        Args:
            spec: Realm specification (provider-agnostic model)

        Returns:
            Realm details dict with at minimum:
            {
                "realm_id": "<provider-specific-id>",
                "realm_name": "<name>",
                "status": "active",
                "created_at": datetime,
                ...additional provider fields...
            }

        Raises:
            ConfigurationError: Configuration invalid
            ValidationError: Spec invalid
            ProviderError: Creation failed
        """
        pass

    @abstractmethod
    async def get_realm(self, realm_id: str) -> Dict[str, Any]:
        """
        Retrieve realm details.

        Args:
            realm_id: Realm identifier (provider-specific format)

        Returns:
            Realm details dict

        Raises:
            RealmNotFoundError: Realm doesn't exist
            ProviderError: Retrieval failed
        """
        pass

    @abstractmethod
    async def list_realms(self) -> List[Dict[str, Any]]:
        """
        List all realms in provider.

        Returns:
            List of realm detail dicts
        """
        pass

    @abstractmethod
    async def delete_realm(self, realm_id: str) -> None:
        """
        Delete a realm (soft-delete recommended).

        Args:
            realm_id: Realm to delete

        Raises:
            RealmNotFoundError: Realm doesn't exist
            ProviderError: Deletion failed
        """
        pass

    @abstractmethod
    async def suspend_realm(self, realm_id: str) -> None:
        """
        Suspend a realm (disable but keep for audit).

        Args:
            realm_id: Realm to suspend
        """
        pass

    @abstractmethod
    async def resume_realm(self, realm_id: str) -> None:
        """
        Resume a suspended realm.

        Args:
            realm_id: Realm to resume
        """
        pass

    # ==================== USER MANAGEMENT ====================

    @abstractmethod
    async def create_user(
        self, realm_id: str, user_spec: Any
    ) -> Dict[str, Any]:
        """
        Create user in realm.

        Args:
            realm_id: Realm containing user
            user_spec: User specification (provider-agnostic model)

        Returns:
            User details dict with at minimum:
            {
                "user_id": "<provider-specific-id>",
                "username": "<username>",
                "email": "<email>",
                "status": "active",
                "created_at": datetime,
                ...additional provider fields...
            }

        Raises:
            ValidationError: Spec invalid
            UserCreationError: Creation failed
        """
        pass

    @abstractmethod
    async def get_user(self, realm_id: str, user_id: str) -> Dict[str, Any]:
        """
        Retrieve user details.

        Args:
            realm_id: Realm containing user
            user_id: User identifier

        Returns:
            User details dict

        Raises:
            UserNotFoundError: User doesn't exist
        """
        pass

    @abstractmethod
    async def list_users(
        self, realm_id: str, filter_spec: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        List users in realm.

        Args:
            realm_id: Realm to query
            filter_spec: Optional filters (e.g., {"status": "active"})

        Returns:
            List of user detail dicts
        """
        pass

    @abstractmethod
    async def delete_user(self, realm_id: str, user_id: str) -> None:
        """
        Delete user from realm.

        Args:
            realm_id: Realm containing user
            user_id: User to delete

        Raises:
            UserNotFoundError: User doesn't exist
        """
        pass

    @abstractmethod
    async def update_user(
        self, realm_id: str, user_id: str, update_spec: Any
    ) -> Dict[str, Any]:
        """
        Update user.

        Args:
            realm_id: Realm containing user
            user_id: User to update
            update_spec: Fields to update

        Returns:
            Updated user details
        """
        pass

    @abstractmethod
    async def set_user_password(
        self, realm_id: str, user_id: str, password: str, temporary: bool = False
    ) -> None:
        """
        Set user password.

        Args:
            realm_id: Realm containing user
            user_id: User to update
            password: New password
            temporary: If True, user must change on first login
        """
        pass

    # ==================== ROLE MANAGEMENT ====================

    @abstractmethod
    async def create_role(
        self, realm_id: str, role_spec: Any
    ) -> Dict[str, Any]:
        """
        Create role in realm.

        Args:
            realm_id: Realm for role
            role_spec: Role specification

        Returns:
            Role details dict
        """
        pass

    @abstractmethod
    async def get_role(self, realm_id: str, role_id: str) -> Dict[str, Any]:
        """
        Retrieve role details.

        Args:
            realm_id: Realm containing role
            role_id: Role identifier

        Returns:
            Role details dict
        """
        pass

    @abstractmethod
    async def list_roles(self, realm_id: str) -> List[Dict[str, Any]]:
        """
        List roles in realm.

        Args:
            realm_id: Realm to query

        Returns:
            List of role detail dicts
        """
        pass

    @abstractmethod
    async def delete_role(self, realm_id: str, role_id: str) -> None:
        """
        Delete role from realm.

        Args:
            realm_id: Realm containing role
            role_id: Role to delete
        """
        pass

    @abstractmethod
    async def assign_role(
        self, realm_id: str, user_id: str, role_id: str
    ) -> None:
        """
        Assign role to user.

        Args:
            realm_id: Realm context
            user_id: User to assign role to
            role_id: Role to assign
        """
        pass

    @abstractmethod
    async def revoke_role(
        self, realm_id: str, user_id: str, role_id: str
    ) -> None:
        """
        Revoke role from user.

        Args:
            realm_id: Realm context
            user_id: User to revoke role from
            role_id: Role to revoke
        """
        pass

    @abstractmethod
    async def get_user_roles(
        self, realm_id: str, user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get roles assigned to user.

        Args:
            realm_id: Realm context
            user_id: User to query

        Returns:
            List of role detail dicts for user
        """
        pass

    # ==================== GROUP / ORGANIZATION MANAGEMENT ====================

    @abstractmethod
    async def create_group(
        self, realm_id: str, group_spec: Any
    ) -> Dict[str, Any]:
        """
        Create group (organization concept) in realm.

        Args:
            realm_id: Realm for group
            group_spec: Group specification

        Returns:
            Group details dict
        """
        pass

    @abstractmethod
    async def get_group(self, realm_id: str, group_id: str) -> Dict[str, Any]:
        """
        Retrieve group details.

        Args:
            realm_id: Realm containing group
            group_id: Group identifier

        Returns:
            Group details dict
        """
        pass

    @abstractmethod
    async def list_groups(self, realm_id: str) -> List[Dict[str, Any]]:
        """
        List groups in realm.

        Args:
            realm_id: Realm to query

        Returns:
            List of group detail dicts
        """
        pass

    @abstractmethod
    async def delete_group(self, realm_id: str, group_id: str) -> None:
        """
        Delete group.

        Args:
            realm_id: Realm containing group
            group_id: Group to delete
        """
        pass

    @abstractmethod
    async def add_user_to_group(
        self, realm_id: str, user_id: str, group_id: str
    ) -> None:
        """
        Add user to group.

        Args:
            realm_id: Realm context
            user_id: User to add
            group_id: Group to add to
        """
        pass

    @abstractmethod
    async def remove_user_from_group(
        self, realm_id: str, user_id: str, group_id: str
    ) -> None:
        """
        Remove user from group.

        Args:
            realm_id: Realm context
            user_id: User to remove
            group_id: Group to remove from
        """
        pass

    # ==================== HEALTH & CONFIGURATION ====================

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check identity provider health.

        Returns:
            Health status dict with at minimum:
            {
                "status": "healthy|unhealthy",
                "provider": "<provider-name>",
                "details": {...}
            }

        Raises:
            ProviderError: Health check failed
        """
        pass

    @abstractmethod
    async def validate_configuration(self) -> None:
        """
        Validate provider configuration.

        Called at startup to ensure credentials, endpoints, etc. are valid.

        Raises:
            ConfigurationError: Configuration invalid
        """
        pass

    # ==================== LIFECYCLE ====================

    async def start(self) -> None:
        """
        Initialize provider (optional).

        Called at startup for connection pool creation, cache init, etc.

        Raises:
            ConfigurationError: Initialization failed
        """
        await self.validate_configuration()

    async def shutdown(self) -> None:
        """
        Cleanup provider resources (optional).

        Called on shutdown for connection pool cleanup, etc.
        """
        pass

    # ==================== UTILITY METHODS ====================

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)

    def get_config_required(self, key: str) -> Any:
        """Get configuration value (required)."""
        from .exceptions import ConfigurationError
        if key not in self.config:
            raise ConfigurationError(
                f"Missing required configuration: {key}",
                context={"provider": self.provider_name, "key": key},
            )
        return self.config[key]
