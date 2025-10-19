"""
Keycloak Provider for ITL ControlPlane SDK

This provider manages Keycloak resources using the ITL ControlPlane SDK framework.
It supports managing realms, users, clients, and other Keycloak resources.
"""
import logging
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from ...src.controlplane_sdk.resource_provider import ResourceProvider
from ...src.controlplane_sdk.models import ResourceRequest, ResourceResponse, ResourceListResponse, ProvisioningState

logger = logging.getLogger(__name__)

@dataclass
class KeycloakRealm:
    """Keycloak realm configuration"""
    name: str
    display_name: str
    enabled: bool = True
    login_theme: str = "keycloak"
    
@dataclass 
class KeycloakUser:
    """Keycloak user configuration"""
    username: str
    email: str
    first_name: str
    last_name: str
    enabled: bool = True

class KeycloakProvider(ResourceProvider):
    """
    Keycloak Resource Provider implementation using the ITL ControlPlane SDK
    
    Supports managing:
    - Realms
    - Users
    - Clients
    - Roles
    """
    
    def __init__(self):
        super().__init__("ITL.Identity")
        self.supported_resource_types = ["realms", "users", "clients", "roles"]
        
        # Keycloak connection settings
        self.keycloak_url = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
        self.keycloak_client_id = os.getenv("KEYCLOAK_CLIENT_ID", "admin-cli")
        self.keycloak_username = os.getenv("KEYCLOAK_USERNAME", "admin") 
        self.keycloak_password = os.getenv("KEYCLOAK_PASSWORD", "admin")
        self.keycloak_realm = os.getenv("KEYCLOAK_REALM", "master")
        
        # In-memory storage for demo (replace with actual Keycloak API calls)
        self.realms: Dict[str, KeycloakRealm] = {}
        self.users: Dict[str, KeycloakUser] = {}
        
        logger.info(f"Initialized Keycloak provider for {self.keycloak_url}")
    
    async def create_or_update_resource(self, request: ResourceRequest) -> ResourceResponse:
        """Create or update a Keycloak resource"""
        resource_type = request.resource_type
        resource_name = request.resource_name
        properties = request.body.get("properties", {})
        
        logger.info(f"Creating/updating {resource_type}: {resource_name}")
        
        if resource_type == "realms":
            return await self._create_or_update_realm(request, properties)
        elif resource_type == "users":
            return await self._create_or_update_user(request, properties)
        elif resource_type == "clients":
            return await self._create_or_update_client(request, properties)
        else:
            raise ValueError(f"Unsupported resource type: {resource_type}")
    
    async def get_resource(self, request: ResourceRequest) -> ResourceResponse:
        """Get a specific Keycloak resource"""
        resource_type = request.resource_type
        resource_name = request.resource_name
        
        logger.info(f"Getting {resource_type}: {resource_name}")
        
        if resource_type == "realms":
            return await self._get_realm(request)
        elif resource_type == "users":
            return await self._get_user(request)
        elif resource_type == "clients":
            return await self._get_client(request)
        else:
            raise ValueError(f"Unsupported resource type: {resource_type}")
    
    async def delete_resource(self, request: ResourceRequest) -> ResourceResponse:
        """Delete a Keycloak resource"""
        resource_type = request.resource_type
        resource_name = request.resource_name
        
        logger.info(f"Deleting {resource_type}: {resource_name}")
        
        if resource_type == "realms":
            return await self._delete_realm(request)
        elif resource_type == "users":
            return await self._delete_user(request)
        elif resource_type == "clients":
            return await self._delete_client(request)
        else:
            raise ValueError(f"Unsupported resource type: {resource_type}")
    
    async def list_resources(self, request: ResourceRequest) -> ResourceListResponse:
        """List Keycloak resources"""
        resource_type = request.resource_type
        
        logger.info(f"Listing {resource_type}")
        
        if resource_type == "realms":
            return await self._list_realms(request)
        elif resource_type == "users":
            return await self._list_users(request)
        elif resource_type == "clients":
            return await self._list_clients(request)
        else:
            raise ValueError(f"Unsupported resource type: {resource_type}")
    
    async def execute_action(self, request: ResourceRequest) -> ResourceResponse:
        """Execute custom actions on Keycloak resources"""
        action = request.action
        resource_type = request.resource_type
        resource_name = request.resource_name
        
        logger.info(f"Executing action '{action}' on {resource_type}: {resource_name}")
        
        if resource_type == "users" and action == "resetPassword":
            return await self._reset_user_password(request)
        elif resource_type == "realms" and action == "export":
            return await self._export_realm(request)
        else:
            raise NotImplementedError(f"Action '{action}' not supported for {resource_type}")
    
    # Realm operations
    async def _create_or_update_realm(self, request: ResourceRequest, properties: Dict[str, Any]) -> ResourceResponse:
        """Create or update a Keycloak realm"""
        realm_name = request.resource_name
        
        realm = KeycloakRealm(
            name=realm_name,
            display_name=properties.get("displayName", realm_name),
            enabled=properties.get("enabled", True),
            login_theme=properties.get("loginTheme", "keycloak")
        )
        
        # Store in memory (replace with actual Keycloak API call)
        self.realms[realm_name] = realm
        
        resource_id = self.generate_resource_id(
            request.subscription_id, request.resource_group, "realms", realm_name
        )
        
        return ResourceResponse(
            id=resource_id,
            name=realm_name,
            type=f"{self.provider_namespace}/realms",
            location=request.location,
            properties={
                "displayName": realm.display_name,
                "enabled": realm.enabled,
                "loginTheme": realm.login_theme,
                "provisioningState": ProvisioningState.SUCCEEDED.value
            }
        )
    
    async def _get_realm(self, request: ResourceRequest) -> ResourceResponse:
        """Get a Keycloak realm"""
        realm_name = request.resource_name
        
        if realm_name not in self.realms:
            raise ValueError(f"Realm '{realm_name}' not found")
        
        realm = self.realms[realm_name]
        resource_id = self.generate_resource_id(
            request.subscription_id, request.resource_group, "realms", realm_name
        )
        
        return ResourceResponse(
            id=resource_id,
            name=realm_name,
            type=f"{self.provider_namespace}/realms",
            location=request.location,
            properties={
                "displayName": realm.display_name,
                "enabled": realm.enabled,
                "loginTheme": realm.login_theme,
                "provisioningState": ProvisioningState.SUCCEEDED.value
            }
        )
    
    async def _delete_realm(self, request: ResourceRequest) -> ResourceResponse:
        """Delete a Keycloak realm"""
        realm_name = request.resource_name
        
        if realm_name not in self.realms:
            raise ValueError(f"Realm '{realm_name}' not found")
        
        # Remove from memory (replace with actual Keycloak API call)
        del self.realms[realm_name]
        
        resource_id = self.generate_resource_id(
            request.subscription_id, request.resource_group, "realms", realm_name
        )
        
        return ResourceResponse(
            id=resource_id,
            name=realm_name,
            type=f"{self.provider_namespace}/realms",
            location=request.location,
            properties={
                "provisioningState": "Deleted"
            }
        )
    
    async def _list_realms(self, request: ResourceRequest) -> ResourceListResponse:
        """List all Keycloak realms"""
        realm_responses = []
        
        for realm_name, realm in self.realms.items():
            resource_id = self.generate_resource_id(
                request.subscription_id, request.resource_group, "realms", realm_name
            )
            
            realm_responses.append(ResourceResponse(
                id=resource_id,
                name=realm_name,
                type=f"{self.provider_namespace}/realms",
                location=request.location,
                properties={
                    "displayName": realm.display_name,
                    "enabled": realm.enabled,
                    "loginTheme": realm.login_theme,
                    "provisioningState": ProvisioningState.SUCCEEDED.value
                }
            ))
        
        return ResourceListResponse(value=realm_responses)
    
    # User operations (similar structure)
    async def _create_or_update_user(self, request: ResourceRequest, properties: Dict[str, Any]) -> ResourceResponse:
        """Create or update a Keycloak user"""
        user_name = request.resource_name
        
        user = KeycloakUser(
            username=user_name,
            email=properties.get("email", f"{user_name}@example.com"),
            first_name=properties.get("firstName", ""),
            last_name=properties.get("lastName", ""),
            enabled=properties.get("enabled", True)
        )
        
        # Store in memory (replace with actual Keycloak API call)
        self.users[user_name] = user
        
        resource_id = self.generate_resource_id(
            request.subscription_id, request.resource_group, "users", user_name
        )
        
        return ResourceResponse(
            id=resource_id,
            name=user_name,
            type=f"{self.provider_namespace}/users",
            location=request.location,
            properties={
                "email": user.email,
                "firstName": user.first_name,
                "lastName": user.last_name,
                "enabled": user.enabled,
                "provisioningState": ProvisioningState.SUCCEEDED.value
            }
        )
    
    async def _get_user(self, request: ResourceRequest) -> ResourceResponse:
        """Get a Keycloak user"""
        user_name = request.resource_name
        
        if user_name not in self.users:
            raise ValueError(f"User '{user_name}' not found")
        
        user = self.users[user_name]
        resource_id = self.generate_resource_id(
            request.subscription_id, request.resource_group, "users", user_name
        )
        
        return ResourceResponse(
            id=resource_id,
            name=user_name,
            type=f"{self.provider_namespace}/users",
            location=request.location,
            properties={
                "email": user.email,
                "firstName": user.first_name,
                "lastName": user.last_name,
                "enabled": user.enabled,
                "provisioningState": ProvisioningState.SUCCEEDED.value
            }
        )
    
    async def _delete_user(self, request: ResourceRequest) -> ResourceResponse:
        """Delete a Keycloak user"""
        user_name = request.resource_name
        
        if user_name not in self.users:
            raise ValueError(f"User '{user_name}' not found")
        
        # Remove from memory (replace with actual Keycloak API call)
        del self.users[user_name]
        
        resource_id = self.generate_resource_id(
            request.subscription_id, request.resource_group, "users", user_name
        )
        
        return ResourceResponse(
            id=resource_id,
            name=user_name,
            type=f"{self.provider_namespace}/users",
            location=request.location,
            properties={
                "provisioningState": "Deleted"
            }
        )
    
    async def _list_users(self, request: ResourceRequest) -> ResourceListResponse:
        """List all Keycloak users"""
        user_responses = []
        
        for user_name, user in self.users.items():
            resource_id = self.generate_resource_id(
                request.subscription_id, request.resource_group, "users", user_name
            )
            
            user_responses.append(ResourceResponse(
                id=resource_id,
                name=user_name,
                type=f"{self.provider_namespace}/users",
                location=request.location,
                properties={
                    "email": user.email,
                    "firstName": user.first_name,
                    "lastName": user.last_name,
                    "enabled": user.enabled,
                    "provisioningState": ProvisioningState.SUCCEEDED.value
                }
            ))
        
        return ResourceListResponse(value=user_responses)
    
    # Client operations (simplified for brevity)
    async def _create_or_update_client(self, request: ResourceRequest, properties: Dict[str, Any]) -> ResourceResponse:
        """Create or update a Keycloak client"""
        client_name = request.resource_name
        
        resource_id = self.generate_resource_id(
            request.subscription_id, request.resource_group, "clients", client_name
        )
        
        return ResourceResponse(
            id=resource_id,
            name=client_name,
            type=f"{self.provider_namespace}/clients",
            location=request.location,
            properties={
                "clientId": properties.get("clientId", client_name),
                "enabled": properties.get("enabled", True),
                "provisioningState": ProvisioningState.SUCCEEDED.value
            }
        )
    
    async def _get_client(self, request: ResourceRequest) -> ResourceResponse:
        """Get a Keycloak client"""
        client_name = request.resource_name
        
        resource_id = self.generate_resource_id(
            request.subscription_id, request.resource_group, "clients", client_name
        )
        
        return ResourceResponse(
            id=resource_id,
            name=client_name,
            type=f"{self.provider_namespace}/clients",
            location=request.location,
            properties={
                "clientId": client_name,
                "enabled": True,
                "provisioningState": ProvisioningState.SUCCEEDED.value
            }
        )
    
    async def _delete_client(self, request: ResourceRequest) -> ResourceResponse:
        """Delete a Keycloak client"""
        client_name = request.resource_name
        
        resource_id = self.generate_resource_id(
            request.subscription_id, request.resource_group, "clients", client_name
        )
        
        return ResourceResponse(
            id=resource_id,
            name=client_name,
            type=f"{self.provider_namespace}/clients",
            location=request.location,
            properties={
                "provisioningState": "Deleted"
            }
        )
    
    async def _list_clients(self, request: ResourceRequest) -> ResourceListResponse:
        """List all Keycloak clients"""
        # Return empty list for now
        return ResourceListResponse(value=[])
    
    # Custom actions
    async def _reset_user_password(self, request: ResourceRequest) -> ResourceResponse:
        """Reset a user's password"""
        user_name = request.resource_name
        new_password = request.body.get("password", "newPassword123")
        
        # In a real implementation, this would call Keycloak API
        logger.info(f"Resetting password for user: {user_name}")
        
        resource_id = self.generate_resource_id(
            request.subscription_id, request.resource_group, "users", user_name
        )
        
        return ResourceResponse(
            id=resource_id,
            name=user_name,
            type=f"{self.provider_namespace}/users",
            location=request.location,
            properties={
                "action": "resetPassword",
                "status": "completed",
                "provisioningState": ProvisioningState.SUCCEEDED.value
            }
        )
    
    async def _export_realm(self, request: ResourceRequest) -> ResourceResponse:
        """Export realm configuration"""
        realm_name = request.resource_name
        
        # In a real implementation, this would export the realm
        logger.info(f"Exporting realm: {realm_name}")
        
        resource_id = self.generate_resource_id(
            request.subscription_id, request.resource_group, "realms", realm_name
        )
        
        return ResourceResponse(
            id=resource_id,
            name=realm_name,
            type=f"{self.provider_namespace}/realms",
            location=request.location,
            properties={
                "action": "export",
                "exportData": {"realm": realm_name, "exported": True},
                "provisioningState": ProvisioningState.SUCCEEDED.value
            }
        )