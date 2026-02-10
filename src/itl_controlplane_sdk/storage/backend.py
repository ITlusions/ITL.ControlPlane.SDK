"""
StorageBackend — factory + lifecycle for persistent storage.

Reads configuration from environment variables, creates a graph database
connection (PostgreSQL, SQLite, or in-memory), and exposes per-resource-type
:class:`ResourceStore` instances that any provider can use as dict
replacements.

Environment variables:
    STORAGE_BACKEND   — "postgresql", "sqlite", or "inmemory" (default)
    DATABASE_HOST     — PostgreSQL host (default: localhost)
    DATABASE_PORT     — PostgreSQL port (default: 5432)
    DATABASE_NAME     — PostgreSQL database name (default: controlplane)
    DATABASE_USER     — PostgreSQL user (default: postgres)
    DATABASE_PASSWORD — PostgreSQL password (default: "")
    DATABASE_PATH     — SQLite file path (default: /data/graph.db)

Example::

    from itl_controlplane_sdk.storage import StorageBackend
    from itl_controlplane_sdk.graphdb import NodeType

    storage = StorageBackend()
    # Register stores for the resource types your provider needs
    storage.register_store("subscriptions", NodeType.SUBSCRIPTION)
    storage.register_store("locations", NodeType.LOCATION, preload=True)

    connected = await storage.initialize()
"""

import os
import logging
from typing import Any, Dict, List, Optional

from itl_controlplane_sdk.graphdb import (
    create_graph_database,
    GraphDatabaseInterface,
    NodeType,
)
from .resource_store import ResourceStore, TupleResourceStore

logger = logging.getLogger(__name__)


class StorageBackend:
    """
    Central storage backend for any resource provider.

    Creates a graph database connection and exposes per-resource-type
    :class:`ResourceStore` instances. Providers register the stores they
    need via :meth:`register_store` before calling :meth:`initialize`.

    Lifecycle::

        storage = StorageBackend()
        storage.register_store("subscriptions", NodeType.SUBSCRIPTION)
        storage.register_store("locations", NodeType.LOCATION, preload=True)

        await storage.initialize()      # connect + create stores + preload
        # ... app runs ...
        await storage.shutdown()        # disconnect
    """

    def __init__(self):
        self.db: Optional[GraphDatabaseInterface] = None
        self._store_registry: List[Dict[str, Any]] = []
        self._stores: Dict[str, ResourceStore] = {}

    def register_store(
        self,
        name: str,
        node_type: NodeType,
        *,
        preload: bool = False,
        tuple_store: bool = False,
    ) -> None:
        """
        Register a resource store to be created during :meth:`initialize`.

        Args:
            name: Attribute name (e.g. "subscriptions") — accessible as
                  ``storage.subscriptions`` after initialize.
            node_type: The :class:`NodeType` for this store.
            preload: If True, bulk-load all records at startup (useful for
                     small reference data like locations).
            tuple_store: If True, use :class:`TupleResourceStore` (for
                         resources stored as (resource_id, config) tuples).
        """
        self._store_registry.append(
            {
                "name": name,
                "node_type": node_type,
                "preload": preload,
                "tuple_store": tuple_store,
            }
        )

    def __getattr__(self, name: str) -> Any:
        """Allow attribute-style access to registered stores."""
        if name.startswith("_") or name in ("db",):
            raise AttributeError(name)
        stores = self.__dict__.get("_stores", {})
        if name in stores:
            return stores[name]
        raise AttributeError(
            f"'{type(self).__name__}' has no store '{name}'. "
            f"Available stores: {list(stores.keys())}"
        )

    async def initialize(self) -> bool:
        """
        Read config from environment, connect to the database, create
        stores, and pre-load any stores marked with ``preload=True``.

        Returns:
            True if connection succeeded, False otherwise.
        """
        backend = os.getenv("STORAGE_BACKEND", "inmemory").lower()

        kwargs: Dict[str, Any] = {}
        if backend in ("postgresql", "postgres"):
            kwargs = {
                "host": os.getenv("DATABASE_HOST", "localhost"),
                "port": int(os.getenv("DATABASE_PORT", "5432")),
                "database": os.getenv("DATABASE_NAME", "controlplane"),
                "user": os.getenv("DATABASE_USER", "postgres"),
                "password": os.getenv("DATABASE_PASSWORD", ""),
            }
        elif backend == "sqlite":
            kwargs = {"path": os.getenv("DATABASE_PATH", "/data/graph.db")}

        self.db = create_graph_database(backend, **kwargs)
        connected = await self.db.connect()

        if not connected:
            logger.error("Failed to connect to %s storage backend", backend)
            return False

        logger.info("Connected to storage backend: %s", backend)

        # Create stores from registry
        preload_count = 0
        for entry in self._store_registry:
            cls = TupleResourceStore if entry["tuple_store"] else ResourceStore
            store = cls(self.db, entry["node_type"])
            self._stores[entry["name"]] = store

            if entry["preload"]:
                await store.load()
                preload_count += len(store)

        logger.info(
            "Storage ready — %d stores created, %d records pre-loaded, "
            "other stores lazy-loaded on demand",
            len(self._stores),
            preload_count,
        )

        try:
            metrics = await self.db.get_metrics()
            logger.info(
                "Database contains %d nodes, %d relationships",
                metrics.total_nodes,
                metrics.total_relationships,
            )
        except Exception:
            pass  # Metrics are informational, not critical

        return True

    async def shutdown(self) -> None:
        """Close the database connection."""
        if self.db:
            await self.db.disconnect()
            logger.info("Storage backend disconnected")

    @property
    def backend_type(self) -> str:
        """Return the backend type name."""
        if self.db:
            return type(self.db).__name__
        return "not-initialized"

    @property
    def store_names(self) -> list:
        """Return the names of all registered stores."""
        return list(self._stores.keys())
