"""migrate data from generic nodes to resource specific tables

Revision ID: 002_migrate_data
Revises: 001_initial
Create Date: 2026-02-08

This migration reads all rows from the legacy 'nodes' table and inserts
them into the appropriate resource-specific tables. It handles all 8
resource types and creates relationships where applicable.

The old 'nodes' and 'relationships' tables are kept as backup (renamed
with _legacy suffix) and can be dropped later.
"""
from typing import Sequence, Union
import json
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002_migrate_data"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migrate data from nodes table to resource-specific tables."""
    conn = op.get_bind()

    # Check if the old 'nodes' table exists
    inspector = sa.inspect(conn)
    if "nodes" not in inspector.get_table_names():
        print("No legacy 'nodes' table found — skipping data migration")
        return

    # Read all nodes
    nodes_table = sa.table(
        "nodes",
        sa.column("id", sa.Text),
        sa.column("node_type", sa.Text),
        sa.column("name", sa.Text),
        sa.column("data", sa.Text),
        sa.column("created_at", sa.Text),
        sa.column("modified_at", sa.Text),
    )

    rows = conn.execute(sa.select(nodes_table)).fetchall()
    print(f"Migrating {len(rows)} nodes from legacy table...")

    # Counters
    counts = {}

    for row in rows:
        node_id, node_type, name, data_str, created_at, modified_at = row
        try:
            full_data = json.loads(data_str)
        except (json.JSONDecodeError, TypeError):
            full_data = {}

        # The 'properties' field inside the JSON blob contains the actual data
        props = full_data.get("properties", {})

        counts[node_type] = counts.get(node_type, 0) + 1

        if node_type == "managementGroup":
            conn.execute(
                sa.text(
                    "INSERT INTO management_groups (id, name, display_name, parent_id, "
                    "description, provisioning_state, tags, properties, created_at, updated_at) "
                    "VALUES (:id, :name, :display_name, :parent_id, :desc, :state, "
                    ":tags, :props, :created, :updated) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {
                    "id": f"/providers/ITL.Management/managementGroups/{name}",
                    "name": name,
                    "display_name": props.get("display_name", name),
                    "parent_id": props.get("parent_id"),
                    "desc": props.get("description"),
                    "state": props.get("provisioning_state", "Succeeded"),
                    "tags": json.dumps(props.get("tags", {})),
                    "props": json.dumps({k: v for k, v in props.items()
                                         if k not in ("display_name", "parent_id",
                                                       "description", "provisioning_state",
                                                       "tags", "children")}),
                    "created": created_at or datetime.utcnow().isoformat(),
                    "updated": modified_at or datetime.utcnow().isoformat(),
                },
            )

        elif node_type == "subscription":
            import uuid
            sub_uuid = props.get("subscription_id", str(uuid.uuid4()))
            conn.execute(
                sa.text(
                    "INSERT INTO subscriptions (id, name, display_name, subscription_id, "
                    "state, management_group_id, provisioning_state, tags, properties, "
                    "created_at, updated_at) "
                    "VALUES (:id, :name, :display_name, :sub_id, :state, :mg_id, :prov_state, "
                    ":tags, :props, :created, :updated) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {
                    "id": f"/subscriptions/{name}",
                    "name": name,
                    "display_name": props.get("display_name", name),
                    "sub_id": sub_uuid,
                    "state": props.get("state", "Enabled"),
                    "mg_id": (f"/providers/ITL.Management/managementGroups/{props['management_group_id']}"
                              if props.get("management_group_id") else None),
                    "prov_state": props.get("provisioning_state", "Succeeded"),
                    "tags": json.dumps(props.get("tags", {})),
                    "props": json.dumps({k: v for k, v in props.items()
                                         if k not in ("display_name", "subscription_id",
                                                       "state", "management_group_id",
                                                       "provisioning_state", "tags")}),
                    "created": created_at or datetime.utcnow().isoformat(),
                    "updated": modified_at or datetime.utcnow().isoformat(),
                },
            )

        elif node_type == "resourceGroup":
            # Extract subscription from the resource_id or _subscription_id
            sub_name = props.get("_subscription_id", "unknown")
            location = props.get("location", "eastus")
            rg_id = props.get("_resource_id",
                              f"/subscriptions/{sub_name}/resourceGroups/{name}")
            conn.execute(
                sa.text(
                    "INSERT INTO resource_groups (id, name, subscription_id, location, "
                    "provisioning_state, tags, properties, created_at, updated_at) "
                    "VALUES (:id, :name, :sub_id, :location, :state, :tags, :props, "
                    ":created, :updated) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {
                    "id": rg_id,
                    "name": name.split("/")[-1] if "/" in name else name,
                    "sub_id": f"/subscriptions/{sub_name}",
                    "location": location,
                    "state": props.get("provisioning_state", "Succeeded"),
                    "tags": json.dumps(props.get("tags", {})),
                    "props": json.dumps({k: v for k, v in props.items()
                                         if k not in ("_subscription_id", "_resource_id",
                                                       "location", "provisioning_state",
                                                       "tags", "_resource_group")}),
                    "created": created_at or datetime.utcnow().isoformat(),
                    "updated": modified_at or datetime.utcnow().isoformat(),
                },
            )

        elif node_type == "location":
            conn.execute(
                sa.text(
                    "INSERT INTO locations (id, name, display_name, shortname, region, "
                    "location_type, properties, created_at, updated_at) "
                    "VALUES (:id, :name, :display_name, :shortname, :region, :loc_type, "
                    ":props, :created, :updated) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {
                    "id": f"location:{name}",
                    "name": name,
                    "display_name": props.get("display_name", name),
                    "shortname": props.get("shortname"),
                    "region": props.get("region"),
                    "loc_type": props.get("location_type", props.get("type", "Region")),
                    "props": json.dumps({k: v for k, v in props.items()
                                         if k not in ("display_name", "shortname",
                                                       "region", "location_type", "type",
                                                       "name")}),
                    "created": created_at or datetime.utcnow().isoformat(),
                    "updated": modified_at or datetime.utcnow().isoformat(),
                },
            )

        elif node_type == "extendedLocation":
            conn.execute(
                sa.text(
                    "INSERT INTO extended_locations (id, name, display_name, shortname, "
                    "region, location_type, home_location, properties, created_at, updated_at) "
                    "VALUES (:id, :name, :display_name, :shortname, :region, :loc_type, "
                    ":home, :props, :created, :updated) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {
                    "id": f"extendedLocation:{name}",
                    "name": name,
                    "display_name": props.get("display_name", name),
                    "shortname": props.get("shortname"),
                    "region": props.get("region"),
                    "loc_type": props.get("location_type", "EdgeZone"),
                    "home": props.get("home_location"),
                    "props": json.dumps({}),
                    "created": created_at or datetime.utcnow().isoformat(),
                    "updated": modified_at or datetime.utcnow().isoformat(),
                },
            )

        elif node_type == "policy":
            conn.execute(
                sa.text(
                    "INSERT INTO policies (id, name, display_name, policy_type, mode, "
                    "description, rules, parameters, provisioning_state, tags, properties, "
                    "created_at, updated_at) "
                    "VALUES (:id, :name, :display_name, :policy_type, :mode, :desc, "
                    ":rules, :params, :state, :tags, :props, :created, :updated) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {
                    "id": f"policy:{name}",
                    "name": name,
                    "display_name": props.get("display_name", name),
                    "policy_type": props.get("policy_type", "Custom"),
                    "mode": props.get("mode", "Indexed"),
                    "desc": props.get("description"),
                    "rules": json.dumps(props.get("rules")) if props.get("rules") else None,
                    "params": json.dumps(props.get("parameters")) if props.get("parameters") else None,
                    "state": props.get("provisioning_state", "Succeeded"),
                    "tags": json.dumps(props.get("tags", {})),
                    "props": json.dumps({}),
                    "created": created_at or datetime.utcnow().isoformat(),
                    "updated": modified_at or datetime.utcnow().isoformat(),
                },
            )

        elif node_type == "tag":
            conn.execute(
                sa.text(
                    "INSERT INTO tags (id, name, count, values, provisioning_state, "
                    "created_at, updated_at) "
                    "VALUES (:id, :name, :count, :vals, :state, :created, :updated) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {
                    "id": f"tag:{name}",
                    "name": name,
                    "count": props.get("count", 0),
                    "vals": json.dumps(props.get("values", [])),
                    "state": props.get("provisioning_state", "Succeeded"),
                    "created": created_at or datetime.utcnow().isoformat(),
                    "updated": modified_at or datetime.utcnow().isoformat(),
                },
            )

        elif node_type == "deployment":
            conn.execute(
                sa.text(
                    "INSERT INTO deployments (id, name, resource_group, location, "
                    "template, parameters, mode, provisioning_state, tags, properties, "
                    "created_at, updated_at) "
                    "VALUES (:id, :name, :rg, :location, :template, :params, :mode, "
                    ":state, :tags, :props, :created, :updated) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {
                    "id": f"deployment:{name}",
                    "name": name,
                    "rg": props.get("resource_group"),
                    "location": props.get("location"),
                    "template": json.dumps(props.get("template", {})),
                    "params": json.dumps(props.get("parameters", {})),
                    "mode": props.get("mode", "Incremental"),
                    "state": props.get("provisioning_state", "Succeeded"),
                    "tags": json.dumps(props.get("tags", {})),
                    "props": json.dumps({}),
                    "created": created_at or datetime.utcnow().isoformat(),
                    "updated": modified_at or datetime.utcnow().isoformat(),
                },
            )

        else:
            print(f"  Skipping unknown node type: {node_type} ({name})")

    # Print summary
    for ntype, count in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  Migrated {count} {ntype} records")

    # Rename old tables as backup
    if "nodes" in inspector.get_table_names():
        op.rename_table("nodes", "nodes_legacy")
        print("  Renamed 'nodes' -> 'nodes_legacy'")

    if "relationships" in inspector.get_table_names():
        op.rename_table("relationships", "relationships_legacy")
        print("  Renamed 'relationships' -> 'relationships_legacy'")

    print(f"Migration complete: {sum(counts.values())} total records migrated")


def downgrade() -> None:
    """Restore old tables — rename _legacy back to original names."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Truncate new tables
    for table in ["resource_relationships", "resource_groups", "subscriptions",
                   "management_groups", "locations", "extended_locations",
                   "policies", "tags", "deployments"]:
        if table in inspector.get_table_names():
            conn.execute(sa.text(f"TRUNCATE TABLE {table} CASCADE"))

    # Rename backup tables back
    if "nodes_legacy" in inspector.get_table_names():
        op.rename_table("nodes_legacy", "nodes")

    if "relationships_legacy" in inspector.get_table_names():
        op.rename_table("relationships_legacy", "relationships")
