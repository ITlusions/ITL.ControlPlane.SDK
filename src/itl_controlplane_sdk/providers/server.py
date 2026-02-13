"""
ProviderServer — base class for standalone resource provider servers.

Eliminates boilerplate that every provider repeats: creating a FastAPI
app via ``AppFactory``, wiring storage lifecycle (startup/shutdown),
registering providers in the ``ResourceProviderRegistry``, and running
uvicorn.

Subclasses only need to implement :meth:`register_providers` and
optionally :meth:`add_routes`.

Example::

    from itl_controlplane_sdk.providers.server import ProviderServer

    class CoreProviderServer(ProviderServer):
        namespace = "ITL.Core"
        title = "ITL Core Provider API"
        version = "1.0.0"
        resource_types = [
            "resourcegroups", "subscriptions", "locations", ...
        ]

        def register_providers(self, registry, provider):
            for rt in self.resource_types:
                registry.register_provider(self.namespace, rt, provider)

        def add_routes(self, app, provider):
            setup_resourcegroups_routes(app, provider)
            # ...
"""

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ProviderServer:
    """
    Base class for standalone resource provider servers.

    Provides:

    - FastAPI app creation via ``AppFactory``
    - Optional ``StorageBackend`` lifecycle (startup/shutdown)
    - Optional ``MessageBrokerManager`` lifecycle
    - ``ResourceProviderRegistry`` wiring
    - Uvicorn runner

    Subclasses must implement:

    - :meth:`create_provider` — create the provider instance
    - :meth:`register_providers` — register provider with registry
    - :meth:`add_routes` — add HTTP routes to the FastAPI app
    """

    # Override in subclass
    namespace: str = "ITL.Unknown"
    title: str = "ITL Provider API"
    version: str = "1.0.0"
    resource_types: List[str] = []

    def __init__(self):
        self.provider = None
        self.storage = None
        self.broker = None
        self.registry = None
        self.app = None

    def create_provider(self, storage=None, **kwargs):
        """
        Create the resource provider instance.

        Override in subclass. Receives the initialized storage backend
        (may be None if storage is disabled).

        Returns:
            A :class:`ResourceProvider` instance.
        """
        raise NotImplementedError("Subclasses must implement create_provider()")

    def register_providers(self, registry, provider) -> None:
        """
        Register the provider's resource types with the registry.

        Default implementation registers all ``resource_types`` under
        ``namespace``. Override for custom registration logic.
        """
        for rt in self.resource_types:
            registry.register_provider(self.namespace, rt, provider)

    def add_routes(self, app, provider) -> None:
        """
        Add HTTP routes to the FastAPI app.

        Override in subclass to add provider-specific routes.
        """
        pass

    def create_app(self):
        """
        Create the FastAPI application with middleware, lifecycle hooks,
        provider registration, and routes.

        Returns:
            A configured ``FastAPI`` application.
        """
        from itl_controlplane_sdk.api import AppFactory
        from itl_controlplane_sdk.providers import ResourceProviderRegistry

        self.registry = ResourceProviderRegistry()

        # Create provider without storage first
        self.provider = self.create_provider()
        self.register_providers(self.registry, self.provider)

        # Build FastAPI app via AppFactory
        factory = AppFactory(self.title, self.version)
        app = factory.create_app(cors_origins=["*"])

        server = self

        @app.on_event("startup")
        async def _startup():
            """Initialize storage and messaging on startup."""
            # --- Storage ---
            backend_type = os.getenv("STORAGE_BACKEND", "inmemory")
            if backend_type != "inmemory":
                try:
                    from itl_controlplane_sdk.persistence import StorageBackend

                    server.storage = StorageBackend()
                    server._configure_stores(server.storage)
                    connected = await server.storage.initialize()
                    if connected:
                        # Re-create provider with persistent storage
                        server.provider = server.create_provider(
                            storage=server.storage
                        )
                        server.register_providers(
                            server.registry, server.provider
                        )
                        logger.info(
                            "Persistent storage ready (%s)",
                            server.storage.backend_type,
                        )
                    else:
                        logger.warning(
                            "Storage backend failed — running in-memory"
                        )
                except ImportError:
                    logger.warning(
                        "Storage module not available — running in-memory"
                    )

            # --- Messaging ---
            broker_enabled = (
                os.getenv("MESSAGE_BROKER_ENABLED", "false").lower() == "true"
            )
            if broker_enabled:
                try:
                    from itl_controlplane_sdk.messaging import (
                        MessageBrokerManager,
                    )

                    server.broker = MessageBrokerManager()
                    await server.broker.initialize()
                except ImportError:
                    logger.warning(
                        "Messaging module not available — events disabled"
                    )

        @app.on_event("shutdown")
        async def _shutdown():
            """Gracefully disconnect storage and messaging."""
            if server.storage:
                await server.storage.shutdown()
            if server.broker:
                await server.broker.shutdown()

        # Set registry on app state
        app.state.registry = self.registry

        # Let subclass add routes
        self.add_routes(app, self.provider)

        self.app = app
        return app

    def _configure_stores(self, storage) -> None:
        """
        Register stores on the storage backend.

        Override in subclass to register provider-specific stores.
        Called before ``storage.initialize()``.

        Example::

            def _configure_stores(self, storage):
                from itl_controlplane_sdk.graphdb import NodeType
                storage.register_store("subscriptions", NodeType.SUBSCRIPTION)
                storage.register_store("locations", NodeType.LOCATION, preload=True)
        """
        pass

    def run(self, host: str = "0.0.0.0", port: int = 8000, **kwargs):
        """Run the standalone server via uvicorn."""
        import uvicorn

        if not self.app:
            self.app = self.create_app()

        print(f"\n[OK] Starting {self.title} on {host}:{port}")
        print(f"[OK] API Documentation: http://{host}:{port}/docs")
        print(f"[OK] Health Check: http://{host}:{port}/health")

        if self.resource_types:
            types_str = ", ".join(self.resource_types)
            print(f"[OK] Registered resource types: {types_str}\n")

        uvicorn.run(self.app, host=host, port=port, **kwargs)
