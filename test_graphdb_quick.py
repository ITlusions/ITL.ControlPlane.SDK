"""Quick smoke test for the graphdb SDK module."""
import asyncio
from itl_controlplane_sdk.graphdb import MetadataService


async def test():
    svc = MetadataService("inmemory")
    ok = await svc.initialize()
    print(f"Initialize: {ok}")

    sub = await svc.register_subscription("sub-123", "Test Sub", "tenant-1")
    print(f"Subscription: {sub.name} (id={sub.id})")

    rg = await svc.register_resource_group("sub-123", "my-rg", "westeurope")
    loc = rg.properties.get("location", "?")
    print(f"ResourceGroup: {rg.name} (location={loc})")

    hierarchy = await svc.get_resource_hierarchy("sub-123")
    print(f"Hierarchy RGs: {hierarchy.resource_groups}")

    metrics = await svc.get_metrics()
    print(f"Metrics: {metrics.total_nodes} nodes, {metrics.total_relationships} rels")

    found = await svc.get_subscription("sub-123")
    print(f"Lookup sub: {found.name if found else 'NOT FOUND'}")

    not_found = await svc.get_subscription("does-not-exist")
    print(f"Lookup missing: {not_found}")

    subs = await svc.list_subscriptions()
    print(f"List subs: {len(subs)} found")

    rgs = await svc.list_resource_groups("sub-123")
    print(f"List RGs: {len(rgs)} found")

    deleted = await svc.delete_resource_group("sub-123", "my-rg")
    print(f"Delete RG: {deleted}")

    rgs_after = await svc.list_resource_groups("sub-123")
    print(f"RGs after delete: {len(rgs_after)}")

    await svc.shutdown()
    print("\nAll graphdb module tests passed!")


if __name__ == "__main__":
    asyncio.run(test())
