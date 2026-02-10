"""
ResourceStore — dict-like persistent wrapper around GraphDB.

Provides a write-through cache so resource providers can use these as
drop-in replacements for plain Python dicts, while data is transparently
persisted to PostgreSQL, SQLite, or an in-memory graph database.

Lazy-loading:
    - Writes always go to both cache AND database.
    - Reads check cache first; on miss, fetch from DB.
    - Full iteration (items/keys/values) triggers a bulk-load on first call.
    - Startup is instant — no bulk-loading required unless explicitly requested.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from itl_controlplane_sdk.graphdb import (
    GraphDatabaseInterface,
    GraphNode,
    NodeType,
)

logger = logging.getLogger(__name__)


class ResourceStore:
    """
    Dict-like persistent store for a single resource type.

    Uses a **lazy-loading write-through cache**:

    - Writes always go to both cache AND database.
    - Reads check cache first; on miss, fetch from DB (lazy).
    - ``items()`` / ``keys()`` / ``values()`` load the full set on
      first call (needed for list endpoints), but that only happens
      when someone actually lists all resources of this type.

    This means startup is instant — no bulk-loading required.

    Example::

        store = ResourceStore(db, NodeType.SUBSCRIPTION)
        store["my-sub"] = {"display_name": "My Sub"}   # writes to cache + DB
        sub = store["my-sub"]                           # reads from cache
        found = await store.contains_async("my-sub")    # cache → DB fallback
    """

    def __init__(self, db: GraphDatabaseInterface, node_type: NodeType):
        self._db = db
        self._node_type = node_type
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._full_loaded = False  # True once we've fetched ALL from DB

    async def load(self) -> None:
        """
        Pre-warm the cache with all records.

        Optional — only needed for resource types that are always listed
        at startup (e.g. locations).
        """
        nodes = await self._db.find_nodes(node_type=self._node_type)
        self._cache = {n.name: n.properties for n in nodes}
        self._full_loaded = True
        logger.debug(
            "Pre-loaded %d %s records from DB",
            len(self._cache),
            self._node_type.value,
        )

    async def ensure_loaded(self) -> None:
        """Lazy-load all records on first list/iteration call."""
        if not self._full_loaded:
            logger.info(
                "Lazy-loading %s from DB (first list call)...",
                self._node_type.value,
            )
            await self.load()
        else:
            logger.debug(
                "Store %s already loaded (%d items)",
                self._node_type.value,
                len(self._cache),
            )

    # -- Sync dict-like interface (cache only, instant) --------------------

    def __contains__(self, key: str) -> bool:
        # Check cache first. For a cache miss we can't do async here,
        # so callers that need a guaranteed answer should use contains_async().
        return key in self._cache

    async def contains_async(self, key: str) -> bool:
        """Check cache, then fall back to DB lookup."""
        if key in self._cache:
            return True
        node = await self._fetch_one(key)
        return node is not None

    def __getitem__(self, key: str) -> Any:
        return self._cache[key]

    async def get_async(self, key: str) -> Optional[Any]:
        """Get from cache, fallback to DB on miss."""
        if key in self._cache:
            return self._cache[key]
        return await self._fetch_one(key)

    def __setitem__(self, key: str, value: Any) -> None:
        self._cache[key] = value
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._persist(key, value))
        except RuntimeError:
            pass

    def __delitem__(self, key: str) -> None:
        if key in self._cache:
            del self._cache[key]
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._delete(key))
            except RuntimeError:
                pass

    def get(self, key: str, default: Any = None) -> Any:
        return self._cache.get(key, default)

    def keys(self):
        return self._cache.keys()

    def values(self):
        return self._cache.values()

    def items(self):
        return self._cache.items()

    def __len__(self) -> int:
        return len(self._cache)

    def __bool__(self) -> bool:
        """Always truthy — even an empty store is a valid store object."""
        return True

    def __iter__(self):
        return iter(self._cache)

    # -- Explicit async methods (preferred) --------------------------------

    async def put(self, key: str, value: Any) -> None:
        """Set a value and persist it to the database."""
        self._cache[key] = value
        await self._persist(key, value)

    async def remove(self, key: str) -> bool:
        """Remove a value and delete it from the database."""
        if key not in self._cache:
            return False
        del self._cache[key]
        await self._delete(key)
        return True

    # -- Internal ----------------------------------------------------------

    async def _fetch_one(self, key: str) -> Optional[Dict[str, Any]]:
        """Fetch a single record from the DB and cache it."""
        node_id = f"{self._node_type.value}:{key}"
        try:
            node = await self._db.get_node(node_id)
            if node:
                self._cache[key] = node.properties
                return node.properties
        except Exception as e:
            logger.error(
                "Failed to fetch %s/%s: %s", self._node_type.value, key, e
            )
        return None

    async def _persist(self, key: str, value: Any) -> None:
        """Create or update a node in the graph DB."""
        node_id = f"{self._node_type.value}:{key}"
        try:
            existing = await self._db.get_node(node_id)
            if existing:
                existing.properties = (
                    value if isinstance(value, dict) else {"value": value}
                )
                existing.name = key
                await self._db.update_node(existing)
            else:
                node = GraphNode(
                    id=node_id,
                    node_type=self._node_type,
                    name=key,
                    properties=(
                        value if isinstance(value, dict) else {"value": value}
                    ),
                )
                await self._db.create_node(node)
        except Exception as e:
            logger.error(
                "Failed to persist %s/%s: %s", self._node_type.value, key, e
            )

    async def _delete(self, key: str) -> None:
        """Delete a node from the graph DB."""
        node_id = f"{self._node_type.value}:{key}"
        try:
            await self._db.delete_node(node_id)
        except Exception as e:
            logger.error(
                "Failed to delete %s/%s: %s", self._node_type.value, key, e
            )


class TupleResourceStore(ResourceStore):
    """
    Variant of :class:`ResourceStore` for resources stored as
    ``(resource_id, config_dict)`` tuples (e.g. resource groups).

    The tuple is unpacked/repacked transparently — the database stores
    the ``resource_id`` as a private ``_resource_id`` property.
    """

    async def load(self) -> None:
        nodes = await self._db.find_nodes(node_type=self._node_type)
        self._cache = {}
        for n in nodes:
            rid = n.properties.get("_resource_id", n.id)
            props = {
                k: v for k, v in n.properties.items() if not k.startswith("_")
            }
            self._cache[n.name] = (rid, props)
        self._full_loaded = True
        logger.debug(
            "Pre-loaded %d %s records from DB",
            len(self._cache),
            self._node_type.value,
        )

    async def _fetch_one(self, key: str) -> Optional[Any]:
        """Fetch a single resource group from the DB and cache it."""
        node_id = f"{self._node_type.value}:{key}"
        try:
            node = await self._db.get_node(node_id)
            if node:
                rid = node.properties.get("_resource_id", node.id)
                props = {
                    k: v
                    for k, v in node.properties.items()
                    if not k.startswith("_")
                }
                value = (rid, props)
                self._cache[key] = value
                return value
        except Exception as e:
            logger.error(
                "Failed to fetch %s/%s: %s", self._node_type.value, key, e
            )
        return None

    async def _persist(self, key: str, value: Any) -> None:
        node_id = f"{self._node_type.value}:{key}"
        if isinstance(value, tuple) and len(value) == 2:
            resource_id, config = value
            props = dict(config) if isinstance(config, dict) else {"value": config}
            props["_resource_id"] = resource_id
        else:
            props = value if isinstance(value, dict) else {"value": value}

        try:
            existing = await self._db.get_node(node_id)
            if existing:
                existing.properties = props
                existing.name = key
                await self._db.update_node(existing)
            else:
                node = GraphNode(
                    id=node_id,
                    node_type=self._node_type,
                    name=key,
                    properties=props,
                )
                await self._db.create_node(node)
        except Exception as e:
            logger.error(
                "Failed to persist %s/%s: %s", self._node_type.value, key, e
            )
