"""
Provider Mode Manager for ITL ControlPlane SDK.

Manages provider mode switching and lifecycle (API, ServiceBus, Hybrid).
"""

import logging
import asyncio
import os
from typing import Optional, Callable, Any
from enum import Enum

from .generic import GenericServiceBusProvider
from itl_controlplane_sdk.providers import ResourceProvider

logger = logging.getLogger(__name__)


class ProviderMode(Enum):
    """Provider execution mode."""
    API = "api"                    # HTTP server only
    SERVICEBUS = "servicebus"      # Message consumer only
    HYBRID = "hybrid"              # Both HTTP + message consumer


async def run_generic_servicebus_provider(
    provider: ResourceProvider,
    provider_namespace: str,
    rabbitmq_url: str = "amqp://guest:guest@localhost/",
):
    """
    Utility function to run a generic service bus provider

    Args:
        provider: Any ResourceProvider instance
        provider_namespace: Provider namespace
        rabbitmq_url: RabbitMQ connection URL

    Example:
        ```python
        from itl_controlplane_sdk.messaging.servicebus import run_generic_servicebus_provider

        await run_generic_servicebus_provider(
            provider=compute_provider,
            provider_namespace="ITL.Compute",
            rabbitmq_url="amqp://localhost/"
        )
        ```
    """
    bus = GenericServiceBusProvider(
        provider=provider,
        provider_namespace=provider_namespace,
        rabbitmq_url=rabbitmq_url,
    )
    await bus.run()


class ProviderModeManager:
    """
    Manages provider mode switching and lifecycle
    
    Simplifies setting up API/ServiceBus/Hybrid mode for any provider.
    
    Example:
        ```python
        from itl_controlplane_sdk.providers import ComputeProvider
        from itl_controlplane_sdk.messaging.servicebus import ProviderModeManager
        
        provider = ComputeProvider(engine=storage_engine)
        manager = ProviderModeManager(
            provider=provider,
            provider_namespace="ITL.Compute",
            app=fastapi_app  # For API mode
        )
        
        manager.run()  # Runs in configured mode
        ```
    """
    
    def __init__(
        self,
        provider: ResourceProvider,
        provider_namespace: str,
        app: Any = None,  # FastAPI app for API mode
        rabbitmq_url: str = "amqp://guest:guest@localhost/",
        mode: Optional[str] = None,
    ):
        """
        Initialize provider mode manager
        
        Args:
            provider: ResourceProvider instance
            provider_namespace: Provider namespace (e.g., "ITL.Compute")
            app: FastAPI application (required for API/Hybrid mode)
            rabbitmq_url: RabbitMQ URL
            mode: Override mode from environment ("api", "servicebus", "hybrid")
        """
        self.provider = provider
        self.provider_namespace = provider_namespace
        self.app = app
        self.rabbitmq_url = rabbitmq_url
        
        # Get mode from parameter or environment
        mode_str = mode or os.getenv("PROVIDER_MODE", "api").lower()
        
        try:
            self.mode = ProviderMode(mode_str)
        except ValueError:
            raise ValueError(
                f"Invalid mode: {mode_str!r}. Must be 'api', 'servicebus', or 'hybrid'"
            )
        
        logger.info(f"[{provider_namespace}] Provider mode: {self.mode.value}")
    
    async def initialize_storage(self, init_func: Callable):
        """Initialize storage and audit system"""
        logger.info(f"[{self.provider_namespace}] Initializing storage...")
        await init_func()
    
    async def run_api_mode(
        self,
        host: str = "0.0.0.0",
        port: int = 8000,
        **kwargs
    ):
        """Run in API mode (HTTP server)"""
        import uvicorn
        
        if not self.app:
            raise ValueError("FastAPI app required for API mode")
        
        logger.info(f"[{self.provider_namespace}] Starting in API mode on {host}:{port}")
        
        uvicorn.run(self.app, host=host, port=port, **kwargs)
    
    async def run_servicebus_mode(self):
        """Run in ServiceBus mode (message consumer)"""
        bus = GenericServiceBusProvider(
            provider=self.provider,
            provider_namespace=self.provider_namespace,
            rabbitmq_url=self.rabbitmq_url,
        )
        
        await bus.run()
    
    async def run_hybrid_mode(
        self,
        host: str = "0.0.0.0",
        port: int = 8000,
        **kwargs
    ):
        """Run in Hybrid mode (both API and message consumer)"""
        import uvicorn
        from concurrent.futures import ThreadPoolExecutor
        
        if not self.app:
            raise ValueError("FastAPI app required for Hybrid mode")
        
        logger.info(f"[{self.provider_namespace}] Starting in HYBRID mode on {host}:{port}")
        
        loop = asyncio.get_event_loop()
        
        with ThreadPoolExecutor(max_workers=1) as api_executor:
            # Start API server in background
            api_task = loop.run_in_executor(
                api_executor,
                lambda: uvicorn.run(self.app, host=host, port=port, log_level="info")
            )
            
            bus = GenericServiceBusProvider(
                provider=self.provider,
                provider_namespace=self.provider_namespace,
                rabbitmq_url=self.rabbitmq_url,
            )
            
            try:
                # Run message consumer (blocking)
                await bus.run()
            finally:
                api_task.cancel()
                try:
                    await api_task
                except asyncio.CancelledError:
                    pass
    
    async def run(
        self,
        host: str = "0.0.0.0",
        port: int = 8000,
        init_func: Optional[Callable] = None,
        **kwargs
    ):
        """
        Run provider in configured mode
        
        Args:
            host: HTTP server host (API/Hybrid mode)
            port: HTTP server port (API/Hybrid mode)
            init_func: Async function to initialize storage
            **kwargs: Additional arguments for uvicorn
        """
        # Initialize storage if provided
        if init_func:
            await self.initialize_storage(init_func)
        
        # Run in configured mode
        if self.mode == ProviderMode.API:
            await self.run_api_mode(host=host, port=port, **kwargs)
        elif self.mode == ProviderMode.SERVICEBUS:
            await self.run_servicebus_mode()
        elif self.mode == ProviderMode.HYBRID:
            await self.run_hybrid_mode(host=host, port=port, **kwargs)
