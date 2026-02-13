"""
Base Provider Server for ITL ControlPlane Resource Providers

Provides common lifecycle management patterns for resource providers:
- Configuration validation and logging
- Audit system initialization
- Graceful shutdown handling
- API Gateway registration

Subclasses should implement:
- __init__() : Initialize engine, provider, registry, app attributes
- create_app() : Build FastAPI application
- run() : Entry point (see CoreProviderServer for example)
"""

import os
import asyncio
import logging
from typing import Callable, Optional

import httpx

logger = logging.getLogger(__name__)


class BaseProviderServer:
    """Base class for ITL ControlPlane Resource Providers.
    
    Provides reusable lifecycle management methods for consistent provider behavior.
    
    Subclasses must define:
    - self.engine (SQLAlchemyStorageEngine)
    - self.app (FastAPI)
    - self.audit_publisher (Optional[AuditEventPublisher])
    """
    
    def _validate_and_log_config(self, host: str, port: int, provider_mode: str) -> None:
        """Validate provider mode and log configuration.
        
        Args:
            host: Server host (e.g., "0.0.0.0")
            port: Server port (e.g., 8000)
            provider_mode: One of "api", "servicebus", or "hybrid"
        
        Raises:
            ValueError: If provider_mode is invalid
        """
        logger.info(f"Provider mode: {provider_mode}")
        
        if provider_mode not in {"api", "servicebus", "hybrid"}:
            raise ValueError(f"Invalid PROVIDER_MODE: {provider_mode}")
        
        if provider_mode in {"api", "hybrid"}:
            logger.info(f"API endpoint: {host}:{port}")
    
    async def _initialize_audit_system(self) -> None:
        """Initialize audit event adapters and publisher.
        
        Supports SQL and RabbitMQ adapters based on environment configuration.
        
        Environment variables:
        - RABBITMQ_URL: If set, adds RabbitMQ audit adapter
        
        Non-fatal: Logs warning if audit system fails to initialize.
        
        Requires:
        - self.engine (SQLAlchemyStorageEngine)
        - SQLAuditEventAdapter, RabbitMQAuditEventAdapter, etc. imported in subclass
        """
        # Import here to avoid circular dependencies
        from itl_controlplane_sdk.storage.audit import (
            SQLAuditEventAdapter,
            RabbitMQAuditEventAdapter,
            CompositeAuditEventAdapter,
            AuditEventPublisher,
        )
        
        logger.info("Initializing audit system...")
        try:
            sql_adapter = SQLAuditEventAdapter(self.engine)
            adapters = [sql_adapter]
            
            if os.getenv("RABBITMQ_URL"):
                rmq_adapter = RabbitMQAuditEventAdapter(
                    rabbitmq_url=os.getenv("RABBITMQ_URL")
                )
                adapters.append(rmq_adapter)
                logger.info("✓ RabbitMQ audit adapter configured")
            
            composite = CompositeAuditEventAdapter(adapters)
            self.audit_publisher = AuditEventPublisher(composite)
            logger.info("✓ Audit event publisher initialized")
        except Exception as e:
            logger.warning(f"Could not initialize audit system: {e}")
    
    def _create_shutdown_handler(self) -> Callable:
        """Create a shutdown event handler for graceful cleanup.
        
        Returns:
            An async callable suitable for FastAPI on_event('shutdown').
            Shuts down audit publisher and storage engine.
        
        Requires:
        - self.engine (SQLAlchemyStorageEngine)
        - self.audit_publisher (Optional[AuditEventPublisher])
        """
        async def _shutdown():
            if self.audit_publisher:
                await self.audit_publisher.shutdown()
            await self.engine.shutdown()
        
        return _shutdown
    
    async def _register_with_gateway(
        self, api_url: str, provider_base_url: str, provider_name: str, 
        provider_namespace: str, resource_types: list, version: str = "1.0.0"
    ) -> bool:
        """Register this provider with the API Gateway.
        
        Waits for gateway availability, then POSTs provider metadata.
        
        Args:
            api_url: Base URL of API Gateway (e.g., http://api-gateway:8080)
            provider_base_url: Base URL of this provider (e.g., http://provider:8000)
            provider_name: Display name (e.g., "ITL Core Provider")
            provider_namespace: Namespace (e.g., "ITL.Core")
            resource_types: List of resource type names (e.g., ["subscriptions", "resourcegroups"])
            version: Provider version string (default "1.0.0")
        
        Environment variables:
        - API_GATEWAY_MAX_RETRIES: Max attempts to contact gateway (default 30)
        - API_GATEWAY_RETRY_INTERVAL: Seconds between retries (default 2)
        
        Returns:
            True if registration succeeded, False otherwise (non-fatal).
        """
        max_retries = int(os.getenv("API_GATEWAY_MAX_RETRIES", "30"))
        retry_interval = int(os.getenv("API_GATEWAY_RETRY_INTERVAL", "2"))
        
        logger.info(f"Waiting for API Gateway at {api_url}...")
        
        # Wait for gateway to be available
        for attempt in range(1, max_retries + 1):
            try:
                response = httpx.get(f"{api_url}/health", timeout=5)
                if response.status_code == 200:
                    logger.info("✓ API Gateway is available")
                    break
            except Exception:
                pass
            
            if attempt < max_retries:
                logger.info(f"  Attempt {attempt}/{max_retries} - Retrying in {retry_interval}s...")
                await asyncio.sleep(retry_interval)
        else:
            logger.warning(f"API Gateway not available after {max_retries} attempts")
            return False
        
        # Register with gateway
        try:
            payload = {
                "name": provider_name,
                "namespace": provider_namespace,
                "base_url": provider_base_url,
                "resource_types": resource_types,
                "version": version,
                "health_endpoint": "/health",
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{api_url}/providers/register",
                    json=payload,
                    timeout=10
                )
            
            if response.status_code in {200, 201}:
                logger.info("✓ Registered with API Gateway")
                return True
            else:
                logger.warning(f"API Gateway registration returned {response.status_code}")
                return False
        except Exception as e:
            logger.warning(f"Error registering with API Gateway: {e}")
            return False
