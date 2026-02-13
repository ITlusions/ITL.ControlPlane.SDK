"""
SQL-based Graph Database Backend for ITL ControlPlane SDK.

Provides persistent storage for graph nodes and relationships using
SQL databases.  Ships with two connection adapters:

- **SQLiteAdapter** — zero-dependency, file-based (dev / single-instance)
- **PostgresAdapter** — production-grade, requires ``psycopg2``

Both adapters expose the same interface so ``SQLGraphDatabase`` doesn't
need to know which one it talks to.

Usage::

    from itl_controlplane_sdk.graphdb import create_graph_database

    # SQLite (zero-infra)
    db = create_graph_database("sqlite", path="/data/graph.db")

    # PostgreSQL (production)
    db = create_graph_database("postgresql",
        host="localhost", port=5432,
        database="controlplane",
        user="app", password="secret",
    )

    await db.connect()
"""
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Sequence, Tuple

from ..models import (
    GraphNode,
    GraphRelationship,
    GraphQuery,
    GraphQueryResult,
    NodeType,
    RelationshipType,
    GraphMetrics,
)
from ..interfaces import GraphDatabaseInterface

logger = logging.getLogger(__name__)


# ===================================================================
# Serialization helpers (shared by all SQL backends)
# ===================================================================

def _node_to_dict(node: GraphNode) -> Dict[str, Any]:
    """Serialize a GraphNode to a JSON-safe dict."""
    return {
        "id": node.id,
        "node_type": node.node_type.value,
        "name": node.name,
        "properties": node.properties,
        "labels": list(node.labels),
        "created_time": node.created_time.isoformat(),
        "modified_time": node.modified_time.isoformat(),
    }


def _dict_to_node(data: Dict[str, Any]) -> GraphNode:
    """Deserialize a dict back to a GraphNode."""
    return GraphNode(
        id=data["id"],
        node_type=NodeType(data["node_type"]),
        name=data["name"],
        properties=data.get("properties", {}),
        labels=set(data.get("labels", [])),
        created_time=datetime.fromisoformat(data["created_time"]),
        modified_time=datetime.fromisoformat(data["modified_time"]),
    )


def _rel_to_dict(rel: GraphRelationship) -> Dict[str, Any]:
    """Serialize a GraphRelationship to a JSON-safe dict."""
    return {
        "id": rel.id,
        "source_id": rel.source_id,
        "target_id": rel.target_id,
        "relationship_type": rel.relationship_type.value,
        "properties": rel.properties,
        "created_time": rel.created_time.isoformat(),
    }


def _dict_to_rel(data: Dict[str, Any]) -> GraphRelationship:
    """Deserialize a dict back to a GraphRelationship."""
    return GraphRelationship(
        id=data["id"],
        source_id=data["source_id"],
        target_id=data["target_id"],
        relationship_type=RelationshipType(data["relationship_type"]),
        properties=data.get("properties", {}),
        created_time=datetime.fromisoformat(data["created_time"]),
    )


# ===================================================================
# SQL Connection Adapter — abstraction over SQLite / PostgreSQL
# ===================================================================

class SQLConnectionAdapter(ABC):
    """
    Thin adapter that hides the differences between database drivers.

    Every adapter must support:
    - ``connect()`` / ``close()``
    - ``execute(sql, params)`` → cursor
    - ``fetchone(sql, params)`` → Optional row
    - ``fetchall(sql, params)`` → list of rows
    - ``commit()``
    - ``placeholder`` — the parameter marker (``?`` or ``%s``)
    - ``upsert_prefix`` — how to do INSERT-or-UPDATE
    """

    @property
    @abstractmethod
    def placeholder(self) -> str:
        """Parameter placeholder: ``?`` for SQLite, ``%s`` for PostgreSQL."""

    @abstractmethod
    def connect(self) -> None:
        """Open the database connection."""

    @abstractmethod
    def close(self) -> None:
        """Close the database connection."""

    @abstractmethod
    def execute(self, sql: str, params: Sequence = ()) -> Any:
        """Execute a statement (INSERT / UPDATE / DELETE)."""

    @abstractmethod
    def executescript(self, sql: str) -> None:
        """Execute multiple statements (DDL)."""

    @abstractmethod
    def fetchone(self, sql: str, params: Sequence = ()) -> Optional[Tuple]:
        """Fetch a single row."""

    @abstractmethod
    def fetchall(self, sql: str, params: Sequence = ()) -> List[Tuple]:
        """Fetch all rows."""

    @abstractmethod
    def commit(self) -> None:
        """Commit the current transaction."""

    def upsert_sql(
        self,
        table: str,
        columns: List[str],
        conflict_column: str = "id",
        update_columns: Optional[List[str]] = None,
    ) -> str:
        """
        Build a portable INSERT ... ON CONFLICT ... UPDATE statement.

        Works on both SQLite ≥ 3.24 and PostgreSQL ≥ 9.5.
        """
        ph = self.placeholder
        placeholders = ", ".join([ph] * len(columns))
        col_list = ", ".join(columns)

        if update_columns:
            set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_columns)
            return (
                f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
                f"ON CONFLICT ({conflict_column}) DO UPDATE SET {set_clause}"
            )
        return (
            f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
            f"ON CONFLICT ({conflict_column}) DO NOTHING"
        )

    def sql(self, template: str) -> str:
        """Replace ``?`` placeholders with the driver's native placeholder."""
        if self.placeholder == "?":
            return template
        return template.replace("?", self.placeholder)


# ===================================================================
# SQLite Adapter
# ===================================================================

class SQLiteAdapter(SQLConnectionAdapter):
    """Adapter for Python's built-in ``sqlite3`` module."""

    def __init__(self, path: str = "graph.db"):
        self.path = path
        self._conn = None

    @property
    def placeholder(self) -> str:
        return "?"

    def connect(self) -> None:
        import sqlite3
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def execute(self, sql: str, params: Sequence = ()) -> Any:
        assert self._conn
        return self._conn.execute(sql, params)

    def executescript(self, sql: str) -> None:
        assert self._conn
        self._conn.executescript(sql)

    def fetchone(self, sql: str, params: Sequence = ()) -> Optional[Tuple]:
        assert self._conn
        return self._conn.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: Sequence = ()) -> List[Tuple]:
        assert self._conn
        return self._conn.execute(sql, params).fetchall()

    def commit(self) -> None:
        assert self._conn
        self._conn.commit()


# ===================================================================
# PostgreSQL Adapter
# ===================================================================

class PostgresAdapter(SQLConnectionAdapter):
    """
    Adapter for PostgreSQL using ``psycopg2``.

    Install::

        pip install itl-controlplane-sdk[graphdb-postgres]
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "controlplane",
        user: str = "postgres",
        password: str = "",
        **extra,
    ):
        self.dsn_params = {
            "host": host,
            "port": port,
            "dbname": database,
            "user": user,
            "password": password,
            **extra,
        }
        self._conn = None

    @property
    def placeholder(self) -> str:
        return "%s"

    def connect(self) -> None:
        try:
            import psycopg2  # type: ignore[import-untyped]
        except ImportError:
            raise ImportError(
                "psycopg2 is required for PostgreSQL. "
                "Install with: pip install itl-controlplane-sdk[graphdb-postgres]"
            )
        self._conn = psycopg2.connect(**self.dsn_params)
        self._conn.autocommit = False

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def execute(self, sql: str, params: Sequence = ()) -> Any:
        assert self._conn
        cur = self._conn.cursor()
        cur.execute(sql, params)
        return cur

    def executescript(self, sql: str) -> None:
        """PostgreSQL doesn't have executescript — execute statements one by one."""
        assert self._conn
        cur = self._conn.cursor()
        # Split on semicolons but skip empty statements
        for stmt in sql.split(";"):
            stmt = stmt.strip()
            if stmt:
                cur.execute(stmt)
        self._conn.commit()

    def fetchone(self, sql: str, params: Sequence = ()) -> Optional[Tuple]:
        assert self._conn
        cur = self._conn.cursor()
        cur.execute(sql, params)
        return cur.fetchone()

    def fetchall(self, sql: str, params: Sequence = ()) -> List[Tuple]:
        assert self._conn
        cur = self._conn.cursor()
        cur.execute(sql, params)
        return cur.fetchall()

    def commit(self) -> None:
        assert self._conn
        self._conn.commit()


# ===================================================================
# Schema (portable across SQLite & PostgreSQL)
# ===================================================================

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS nodes (
    id          TEXT PRIMARY KEY,
    node_type   TEXT NOT NULL,
    name        TEXT NOT NULL,
    data        TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    modified_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_nodes_name ON nodes(name);

CREATE TABLE IF NOT EXISTS relationships (
    id                  TEXT PRIMARY KEY,
    source_id           TEXT NOT NULL,
    target_id           TEXT NOT NULL,
    relationship_type   TEXT NOT NULL,
    data                TEXT NOT NULL,
    created_at          TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rel_source ON relationships(source_id);
CREATE INDEX IF NOT EXISTS idx_rel_target ON relationships(target_id);
CREATE INDEX IF NOT EXISTS idx_rel_type   ON relationships(relationship_type)
"""


# ===================================================================
# SQL Graph Database — uses any SQLConnectionAdapter
# ===================================================================

class SQLGraphDatabase(GraphDatabaseInterface):
    """
    SQL-backed graph database that works with any ``SQLConnectionAdapter``.

    Stores nodes and relationships in two tables with JSON ``data``
    columns.  The adapter handles driver differences (SQLite vs
    PostgreSQL) so this class contains only pure SQL logic.

    Args:
        adapter: A ``SQLConnectionAdapter`` instance (SQLiteAdapter or
                 PostgresAdapter).
    """

    def __init__(self, adapter: SQLConnectionAdapter):
        self._adapter = adapter
        self.connected = False

    @property
    def backend_name(self) -> str:
        return type(self._adapter).__name__.replace("Adapter", "")

    # -- lifecycle ----------------------------------------------------------

    async def connect(self) -> bool:
        try:
            self._adapter.connect()
            self._adapter.executescript(_SCHEMA_SQL)
            self._adapter.commit()
            self.connected = True
            logger.info("Connected to %s graph database", self.backend_name)
            return True
        except Exception as e:
            logger.error("Failed to connect to %s: %s", self.backend_name, e)
            return False

    async def disconnect(self) -> None:
        self._adapter.close()
        self.connected = False
        logger.info("Disconnected from %s graph database", self.backend_name)

    # -- Node CRUD ----------------------------------------------------------

    async def create_node(self, node: GraphNode) -> GraphNode:
        a = self._adapter
        row = a.fetchone(a.sql("SELECT 1 FROM nodes WHERE id = ?"), (node.id,))
        if row:
            raise ValueError(f"Node with ID {node.id} already exists")

        now = datetime.utcnow()
        node.created_time = now
        node.modified_time = now
        data = json.dumps(_node_to_dict(node))

        a.execute(
            a.sql(
                "INSERT INTO nodes (id, node_type, name, data, created_at, modified_at) "
                "VALUES (?, ?, ?, ?, ?, ?)"
            ),
            (node.id, node.node_type.value, node.name, data, now.isoformat(), now.isoformat()),
        )
        a.commit()
        logger.debug("Created node: %s (%s)", node.id, node.node_type.value)
        return node

    async def update_node(self, node: GraphNode) -> GraphNode:
        a = self._adapter
        row = a.fetchone(a.sql("SELECT 1 FROM nodes WHERE id = ?"), (node.id,))
        if not row:
            raise ValueError(f"Node with ID {node.id} not found")

        now = datetime.utcnow()
        node.modified_time = now
        data = json.dumps(_node_to_dict(node))

        a.execute(
            a.sql(
                "UPDATE nodes SET node_type = ?, name = ?, data = ?, modified_at = ? "
                "WHERE id = ?"
            ),
            (node.node_type.value, node.name, data, now.isoformat(), node.id),
        )
        a.commit()
        logger.debug("Updated node: %s", node.id)
        return node

    async def delete_node(self, node_id: str) -> bool:
        a = self._adapter
        row = a.fetchone(a.sql("SELECT 1 FROM nodes WHERE id = ?"), (node_id,))
        if not row:
            return False

        # Cascade-delete relationships
        rel_rows = a.fetchall(
            a.sql("SELECT id FROM relationships WHERE source_id = ? OR target_id = ?"),
            (node_id, node_id),
        )
        for (rel_id,) in rel_rows:
            a.execute(a.sql("DELETE FROM relationships WHERE id = ?"), (rel_id,))

        a.execute(a.sql("DELETE FROM nodes WHERE id = ?"), (node_id,))
        a.commit()
        logger.debug("Deleted node: %s", node_id)
        return True

    async def get_node(self, node_id: str) -> Optional[GraphNode]:
        row = self._adapter.fetchone(
            self._adapter.sql("SELECT data FROM nodes WHERE id = ?"), (node_id,)
        )
        if not row:
            return None
        return _dict_to_node(json.loads(row[0]))

    # -- Relationship CRUD --------------------------------------------------

    async def create_relationship(self, relationship: GraphRelationship) -> GraphRelationship:
        a = self._adapter
        # Verify endpoints
        for endpoint, label in [
            (relationship.source_id, "Source"),
            (relationship.target_id, "Target"),
        ]:
            if not a.fetchone(a.sql("SELECT 1 FROM nodes WHERE id = ?"), (endpoint,)):
                raise ValueError(f"{label} node {endpoint} not found")

        now = datetime.utcnow()
        relationship.created_time = now
        data = json.dumps(_rel_to_dict(relationship))

        upsert = a.upsert_sql(
            "relationships",
            ["id", "source_id", "target_id", "relationship_type", "data", "created_at"],
            conflict_column="id",
            update_columns=["source_id", "target_id", "relationship_type", "data", "created_at"],
        )
        a.execute(
            upsert,
            (
                relationship.id,
                relationship.source_id,
                relationship.target_id,
                relationship.relationship_type.value,
                data,
                now.isoformat(),
            ),
        )
        a.commit()
        logger.debug(
            "Created relationship: %s -> %s (%s)",
            relationship.source_id,
            relationship.target_id,
            relationship.relationship_type.value,
        )
        return relationship

    async def delete_relationship(self, relationship_id: str) -> bool:
        a = self._adapter
        row = a.fetchone(a.sql("SELECT 1 FROM relationships WHERE id = ?"), (relationship_id,))
        if not row:
            return False
        a.execute(a.sql("DELETE FROM relationships WHERE id = ?"), (relationship_id,))
        a.commit()
        logger.debug("Deleted relationship: %s", relationship_id)
        return True

    # -- Querying -----------------------------------------------------------

    async def query(self, query: GraphQuery) -> GraphQueryResult:
        nodes: List[GraphNode] = []
        if "nodes" in query.query.lower() and "type" in query.parameters:
            nodes = await self.find_nodes(node_type=NodeType(query.parameters["type"]))
        return GraphQueryResult(
            nodes=nodes,
            raw_result={"query": query.query, "parameters": query.parameters},
        )

    async def find_nodes(
        self,
        node_type: Optional[NodeType] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> List[GraphNode]:
        a = self._adapter
        if node_type:
            rows = a.fetchall(
                a.sql("SELECT data FROM nodes WHERE node_type = ?"),
                (node_type.value,),
            )
        else:
            rows = a.fetchall("SELECT data FROM nodes")

        nodes = [_dict_to_node(json.loads(r[0])) for r in rows]

        if properties:
            nodes = [
                n for n in nodes
                if all(n.properties.get(k) == v for k, v in properties.items())
            ]
        return nodes

    async def get_relationships(
        self,
        node_id: str,
        relationship_type: Optional[RelationshipType] = None,
        direction: str = "both",
    ) -> List[GraphRelationship]:
        a = self._adapter
        if direction == "outgoing":
            sql = a.sql("SELECT data FROM relationships WHERE source_id = ?")
            params: list = [node_id]
        elif direction == "incoming":
            sql = a.sql("SELECT data FROM relationships WHERE target_id = ?")
            params = [node_id]
        else:
            sql = a.sql("SELECT data FROM relationships WHERE source_id = ? OR target_id = ?")
            params = [node_id, node_id]

        if relationship_type:
            sql += a.sql(" AND relationship_type = ?")
            params.append(relationship_type.value)

        rows = a.fetchall(sql, params)
        return [_dict_to_rel(json.loads(r[0])) for r in rows]

    async def get_metrics(self) -> GraphMetrics:
        a = self._adapter
        total_nodes = a.fetchone("SELECT COUNT(*) FROM nodes")[0]  # type: ignore[index]
        total_rels = a.fetchone("SELECT COUNT(*) FROM relationships")[0]  # type: ignore[index]

        node_counts: Dict[str, int] = {}
        for row in a.fetchall("SELECT node_type, COUNT(*) FROM nodes GROUP BY node_type"):
            node_counts[row[0]] = row[1]

        rel_counts: Dict[str, int] = {}
        for row in a.fetchall(
            "SELECT relationship_type, COUNT(*) FROM relationships GROUP BY relationship_type"
        ):
            rel_counts[row[0]] = row[1]

        return GraphMetrics(
            total_nodes=total_nodes,
            total_relationships=total_rels,
            node_counts=node_counts,
            relationship_counts=rel_counts,
        )


# ===================================================================
# Backward-compatible alias
# ===================================================================

class SQLiteGraphDatabase(SQLGraphDatabase):
    """
    Convenience subclass — creates a ``SQLGraphDatabase`` with a
    ``SQLiteAdapter``.  Keeps backward compatibility with existing code.
    """

    def __init__(self, path: str = "graph.db"):
        super().__init__(adapter=SQLiteAdapter(path=path))


class PostgresGraphDatabase(SQLGraphDatabase):
    """
    Convenience subclass — creates a ``SQLGraphDatabase`` with a
    ``PostgresAdapter``.
    """

    def __init__(self, **kwargs):
        super().__init__(adapter=PostgresAdapter(**kwargs))
