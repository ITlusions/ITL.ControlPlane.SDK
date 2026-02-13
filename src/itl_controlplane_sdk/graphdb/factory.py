"""
Graph Database Factory for ITL ControlPlane SDK.

Factory function for creating graph database instances across different backends.
"""
import logging
from typing import Optional

from .interfaces import GraphDatabaseInterface
from .backends import InMemoryGraphDatabase, SQLiteGraphDatabase, PostgresGraphDatabase
from .models import NodeType, RelationshipType, GraphMetrics

logger = logging.getLogger(__name__)


def create_graph_database(
    database_type: str = "inmemory",
    **kwargs
) -> GraphDatabaseInterface:
    """
    Create a graph database instance.

    Supports multiple backends: in-memory, SQLite, PostgreSQL, and Neo4j.

    Args:
        database_type: ``"inmemory"``, ``"sqlite"``, ``"postgresql"``,
                       ``"postgres"``, or ``"neo4j"``.
        **kwargs: Forwarded to the backend constructor.

            - **sqlite**: ``path`` (default ``"graph.db"``)
            - **postgresql**: ``host``, ``port``, ``database``, ``user``,
              ``password``
            - **neo4j**: ``uri``, ``username``, ``password``

    Returns:
        GraphDatabaseInterface: Configured database instance.

    Raises:
        ValueError: If database_type is unsupported or required parameters missing.

    Example::

        # In-memory for development
        db = create_graph_database("inmemory")
        await db.connect()

        # SQLite for testing/single-instance
        db = create_graph_database("sqlite", path="/tmp/graph.db")
        await db.connect()

        # PostgreSQL for production
        db = create_graph_database(
            "postgresql",
            host="localhost",
            port=5432,
            database="controlplane",
            user="app",
            password="secret",
        )
        await db.connect()

        # Neo4j for enterprise
        db = create_graph_database(
            "neo4j",
            uri="bolt://localhost:7687",
            username="neo4j",
            password="password",
        )
        await db.connect()
    """
    db_type = database_type.lower()

    if db_type in ("inmemory", "memory"):
        logger.debug("Creating in-memory graph database")
        return InMemoryGraphDatabase()

    elif db_type == "sqlite":
        path = kwargs.get("path", "graph.db")
        logger.debug("Creating SQLite graph database at %s", path)
        return SQLiteGraphDatabase(path=path)

    elif db_type in ("postgresql", "postgres"):
        logger.debug("Creating PostgreSQL graph database")
        return PostgresGraphDatabase(**kwargs)

    elif db_type == "neo4j":
        required = ("uri", "username", "password")
        missing = [p for p in required if p not in kwargs]
        if missing:
            raise ValueError(f"Missing required Neo4j parameters: {missing}")
        logger.debug("Creating Neo4j graph database at %s", kwargs.get("uri"))
        try:
            from .backends.neo4j import Neo4jGraphDatabase  # type: ignore
            return Neo4jGraphDatabase(**kwargs)
        except ImportError:
            raise ImportError(
                "Neo4j backend not available. "
                "Install with: pip install itl-controlplane-sdk[graphdb-neo4j]"
            )

    else:
        raise ValueError(
            f"Unsupported database type: {database_type!r}. "
            f"Supported: inmemory, sqlite, postgresql, neo4j"
        )
