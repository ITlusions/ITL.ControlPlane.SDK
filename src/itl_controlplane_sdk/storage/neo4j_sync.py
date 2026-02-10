"""
Neo4j Sync Service for ITL ControlPlane.

Provides a dual-write sync mechanism: when resources are created/updated
in PostgreSQL (via SQLAlchemy), changes are automatically replicated to
Neo4j for graph visualization and relationship queries.

This is the 'B' in Option B — PostgreSQL remains the primary store,
Neo4j is the graph visualization layer.

Usage::

    from itl_controlplane_sdk.storage.neo4j_sync import Neo4jSyncService

    sync = Neo4jSyncService(
        uri="bolt://neo4j:7687",
        username="neo4j",
        password="devpassword",
    )
    await sync.connect()

    # Sync a node
    await sync.sync_node(
        node_type="subscriptions",
        node_id="/subscriptions/prod-sub",
        properties={"display_name": "Production", "state": "Enabled"},
        relationships=[{
            "type": "BELONGS_TO",
            "target_type": "management_groups",
            "target_id": "/providers/ITL.Management/managementGroups/platform",
        }],
    )

    # Used by repositories — they call sync automatically when configured.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Table name → Neo4j label mapping
_TABLE_TO_LABEL = {
    "management_groups": "ManagementGroup",
    "subscriptions": "Subscription",
    "resource_groups": "ResourceGroup",
    "locations": "Location",
    "extended_locations": "ExtendedLocation",
    "policies": "Policy",
    "tags": "Tag",
    "deployments": "Deployment",
}


class Neo4jSyncService:
    """
    Async Neo4j sync service for dual-write from PostgreSQL.

    Creates/updates nodes and relationships in Neo4j whenever resources
    change in the primary PostgreSQL database. Uses the async Neo4j driver.

    The service is **fire-and-forget** by default — sync failures are
    logged but don't block the primary PostgreSQL write. This ensures
    the CRUD API remains fast and reliable even if Neo4j is temporarily
    unavailable.
    """

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        username: str = "neo4j",
        password: str = "",
        database: str = "neo4j",
    ):
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self.driver = None
        self._connected = False

    async def connect(self) -> bool:
        """Connect to Neo4j."""
        try:
            from neo4j import AsyncGraphDatabase
            self.driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password),
            )
            # Verify connection
            async with self.driver.session(database=self.database) as session:
                result = await session.run("RETURN 1 AS test")
                await result.single()
            
            # Create constraints/indexes for all resource types
            await self._create_schema()
            
            self._connected = True
            logger.info("Neo4j sync connected: %s", self.uri)
            return True
        except ImportError:
            logger.warning(
                "neo4j driver not installed — Neo4j sync disabled. "
                "Install with: pip install neo4j>=5.0.0"
            )
            return False
        except Exception as e:
            logger.warning("Neo4j sync connection failed: %s — sync disabled", e)
            return False

    async def disconnect(self):
        """Disconnect from Neo4j."""
        if self.driver:
            await self.driver.close()
            self._connected = False
            logger.info("Neo4j sync disconnected")

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def _create_schema(self):
        """Create Neo4j constraints and indexes for resource types."""
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:ManagementGroup) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Subscription) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:ResourceGroup) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Location) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:ExtendedLocation) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Policy) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Tag) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Deployment) REQUIRE n.id IS UNIQUE",
        ]
        try:
            async with self.driver.session(database=self.database) as session:
                for cypher in constraints:
                    await session.run(cypher)
            logger.info("Neo4j schema constraints created")
        except Exception as e:
            logger.warning("Failed to create Neo4j schema: %s", e)

    async def sync_node(
        self,
        node_type: str,
        node_id: str,
        properties: Dict[str, Any],
        relationships: Optional[List[dict]] = None,
    ):
        """
        Sync a resource node to Neo4j (MERGE — upsert).

        Args:
            node_type: Table name (e.g. "subscriptions", "management_groups")
            node_id: The primary key ID of the resource
            properties: Dict of properties to store on the node
            relationships: Optional list of relationships to create, each with:
                - type: Relationship type (e.g. "BELONGS_TO", "CONTAINS")
                - target_type: Target table name
                - target_id: Target resource ID
        """
        if not self._connected:
            return

        label = _TABLE_TO_LABEL.get(node_type, node_type.title().replace("_", ""))

        # Filter out non-serializable values
        safe_props = {}
        for k, v in properties.items():
            if isinstance(v, (str, int, float, bool)):
                safe_props[k] = v
            elif isinstance(v, list):
                # Neo4j supports lists of primitives
                if all(isinstance(i, (str, int, float, bool)) for i in v):
                    safe_props[k] = v
            elif v is None:
                pass  # Skip None values
            else:
                # Convert complex objects to string
                safe_props[k] = str(v)

        safe_props["id"] = node_id

        try:
            async with self.driver.session(database=self.database) as session:
                # MERGE the node
                cypher = (
                    f"MERGE (n:{label} {{id: $id}}) "
                    f"SET n += $props "
                    f"RETURN n"
                )
                await session.run(cypher, id=node_id, props=safe_props)

                # Create relationships
                if relationships:
                    for rel in relationships:
                        await self._sync_single_relationship(
                            session,
                            source_label=label,
                            source_id=node_id,
                            target_type=rel["target_type"],
                            target_id=rel["target_id"],
                            rel_type=rel["type"],
                            properties=rel.get("properties", {}),
                        )

            logger.debug("Synced %s to Neo4j: %s", label, node_id)
        except Exception as e:
            logger.warning("Neo4j sync failed for %s/%s: %s", node_type, node_id, e)

    async def _sync_single_relationship(
        self,
        session,
        source_label: str,
        source_id: str,
        target_type: str,
        target_id: str,
        rel_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ):
        """Create/update a single relationship between two nodes."""
        target_label = _TABLE_TO_LABEL.get(
            target_type, target_type.title().replace("_", "")
        )

        cypher = (
            f"MATCH (s:{source_label} {{id: $source_id}}) "
            f"MERGE (t:{target_label} {{id: $target_id}}) "
            f"MERGE (s)-[r:{rel_type}]->(t) "
        )
        if properties:
            cypher += "SET r += $props "
        cypher += "RETURN r"

        params = {
            "source_id": source_id,
            "target_id": target_id,
        }
        if properties:
            params["props"] = properties

        await session.run(cypher, **params)

    async def sync_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ):
        """
        Create/update a relationship in Neo4j.
        
        This is a simpler API that doesn't require knowing node labels.
        Uses a generic approach with MATCH on id property.
        """
        if not self._connected:
            return

        try:
            async with self.driver.session(database=self.database) as session:
                # Match by id property (works regardless of label)
                cypher = (
                    f"MATCH (s {{id: $source_id}}) "
                    f"MATCH (t {{id: $target_id}}) "
                    f"MERGE (s)-[r:{relationship_type}]->(t) "
                )
                if properties:
                    cypher += "SET r += $props "
                cypher += "RETURN r"

                params = {
                    "source_id": source_id,
                    "target_id": target_id,
                }
                if properties:
                    params["props"] = properties

                await session.run(cypher, **params)
                logger.debug(
                    "Synced relationship to Neo4j: %s -[%s]-> %s",
                    source_id, relationship_type, target_id,
                )
        except Exception as e:
            logger.warning(
                "Neo4j relationship sync failed: %s -[%s]-> %s: %s",
                source_id, relationship_type, target_id, e,
            )

    async def delete_node(self, node_id: str, node_type: str = ""):
        """Delete a node and its relationships from Neo4j."""
        if not self._connected:
            return

        try:
            async with self.driver.session(database=self.database) as session:
                # DETACH DELETE removes node and all connected relationships
                cypher = "MATCH (n {id: $id}) DETACH DELETE n"
                await session.run(cypher, id=node_id)
                logger.debug("Deleted node from Neo4j: %s", node_id)
        except Exception as e:
            logger.warning("Neo4j delete failed for %s: %s", node_id, e)

    async def delete_relationship(self, rel_id: str):
        """Delete a specific relationship from Neo4j."""
        if not self._connected:
            return

        try:
            async with self.driver.session(database=self.database) as session:
                # Parse rel_id: "source->TYPE->target"
                parts = rel_id.split("->")
                if len(parts) == 3:
                    source_id, rel_type, target_id = parts
                    cypher = (
                        f"MATCH (s {{id: $source_id}})-[r:{rel_type}]->(t {{id: $target_id}}) "
                        f"DELETE r"
                    )
                    await session.run(
                        cypher, source_id=source_id, target_id=target_id
                    )
                    logger.debug("Deleted relationship from Neo4j: %s", rel_id)
        except Exception as e:
            logger.warning("Neo4j relationship delete failed: %s", e)

    async def full_sync(self, session_factory, batch_size: int = 100):
        """
        Full sync: read all resources from PostgreSQL and sync to Neo4j.
        
        Useful for initial population or recovery after Neo4j downtime.
        
        Args:
            session_factory: SQLAlchemy async_sessionmaker
            batch_size: Number of records to process per batch
        """
        if not self._connected:
            logger.warning("Neo4j not connected — full sync skipped")
            return

        from .models import (
            ManagementGroupModel, SubscriptionModel, ResourceGroupModel,
            LocationModel, ExtendedLocationModel, PolicyModel,
            TagModel, DeploymentModel, ResourceRelationshipModel,
        )
        from sqlalchemy import select

        model_classes = [
            ManagementGroupModel, LocationModel, ExtendedLocationModel,
            SubscriptionModel, ResourceGroupModel,
            PolicyModel, TagModel, DeploymentModel,
        ]

        total = 0
        async with session_factory() as db_session:
            for model_cls in model_classes:
                table_name = model_cls.__tablename__
                stmt = select(model_cls)
                result = await db_session.execute(stmt)
                rows = result.scalars().all()

                for row in rows:
                    props = row.to_dict() if hasattr(row, "to_dict") else {"id": row.id, "name": row.name}
                    await self.sync_node(
                        node_type=table_name,
                        node_id=row.id,
                        properties=props,
                    )
                    total += 1

                logger.info("Full sync: %d %s nodes synced", len(rows), table_name)

            # Sync relationships
            rel_stmt = select(ResourceRelationshipModel)
            rel_result = await db_session.execute(rel_stmt)
            rels = rel_result.scalars().all()
            for rel in rels:
                await self.sync_relationship(
                    source_id=rel.source_id,
                    target_id=rel.target_id,
                    relationship_type=rel.relationship_type,
                    properties=rel.properties,
                )

            logger.info(
                "Full sync complete: %d nodes, %d relationships",
                total, len(rels),
            )

    async def get_stats(self) -> Dict[str, Any]:
        """Get Neo4j node/relationship counts."""
        if not self._connected:
            return {"connected": False}

        try:
            async with self.driver.session(database=self.database) as session:
                # Node counts by label
                result = await session.run(
                    "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count "
                    "ORDER BY count DESC"
                )
                node_counts = {}
                total_nodes = 0
                async for record in result:
                    label = record["label"]
                    count = record["count"]
                    node_counts[label] = count
                    total_nodes += count

                # Relationship counts
                result = await session.run(
                    "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count "
                    "ORDER BY count DESC"
                )
                rel_counts = {}
                total_rels = 0
                async for record in result:
                    rel_type = record["type"]
                    count = record["count"]
                    rel_counts[rel_type] = count
                    total_rels += count

                return {
                    "connected": True,
                    "total_nodes": total_nodes,
                    "total_relationships": total_rels,
                    "node_counts": node_counts,
                    "relationship_counts": rel_counts,
                }
        except Exception as e:
            return {"connected": True, "error": str(e)}
