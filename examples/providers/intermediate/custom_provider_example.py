"""
Custom ResourceProvider Implementation Example

Demonstrates how to build your own resource provider by extending the
ResourceProvider base class. This is the foundation pattern for adding
new resource types to the ITL ControlPlane.

Shows:
1. Extending ResourceProvider with custom logic
2. Implementing all CRUD operations (create, get, delete, list)
3. Adding custom actions (execute_action)
4. Request validation with business rules
5. Registering the provider in the registry
"""

import asyncio
from typing import Dict, List, Any
from datetime import datetime

from itl_controlplane_sdk.providers.base import ResourceProvider
from itl_controlplane_sdk.providers.registry import ResourceProviderRegistry
from itl_controlplane_sdk.core import (
    ResourceRequest,
    ResourceResponse,
    ResourceListResponse,
    ProvisioningState,
)


# ============================================================================
# CUSTOM PROVIDER: DNS Zone Provider
# ============================================================================

class DnsZoneProvider(ResourceProvider):
    """
    Custom provider for managing DNS Zones.
    
    Extends ResourceProvider to handle DNS zone lifecycle:
    - Create/update DNS zones
    - Get zone details with record counts
    - List zones per resource group
    - Delete zones with safety checks
    - Custom action: export zone file
    
    This demonstrates the full contract a provider must implement.
    """

    # Valid DNS zone types
    ZONE_TYPES = {"Public", "Private"}

    def __init__(self):
        super().__init__("ITL.Network")
        # Declare which resource types this provider handles
        self.supported_resource_types = ["dnsZones"]
        # In-memory storage (use a real database in production)
        self._zones: Dict[str, ResourceResponse] = {}
        self._record_counts: Dict[str, int] = {}

    async def create_or_update_resource(self, request: ResourceRequest) -> ResourceResponse:
        """
        Create or update a DNS zone.
        
        Expected body:
            {
                "zoneType": "Public" | "Private",
                "ttl": 3600,
                "tags": {"env": "prod"}
            }
        """
        resource_id = self.generate_resource_id(
            request.subscription_id,
            request.resource_group,
            request.resource_type,
            request.resource_name,
        )

        is_update = resource_id in self._zones
        now = datetime.utcnow().isoformat() + "Z"

        properties = {
            "zoneType": request.body.get("zoneType", "Public"),
            "ttl": request.body.get("ttl", 3600),
            "numberOfRecordSets": self._record_counts.get(resource_id, 0),
            "nameServers": [
                f"ns1.itlcloud.net",
                f"ns2.itlcloud.net",
            ],
        }

        if is_update:
            # Preserve creation metadata on update
            existing = self._zones[resource_id]
            properties["createdTime"] = existing.properties.get("createdTime")
            properties["modifiedTime"] = now
        else:
            properties["createdTime"] = now
            properties["modifiedTime"] = now

        response = ResourceResponse(
            id=resource_id,
            name=request.resource_name,
            type=f"{self.provider_namespace}/{request.resource_type}",
            location=request.location,
            properties=properties,
            tags=request.body.get("tags"),
            provisioning_state=ProvisioningState.SUCCEEDED,
        )

        self._zones[resource_id] = response
        return response

    async def get_resource(self, request: ResourceRequest) -> ResourceResponse:
        """Get a specific DNS zone with current record count."""
        resource_id = self.generate_resource_id(
            request.subscription_id,
            request.resource_group,
            request.resource_type,
            request.resource_name,
        )
        if resource_id not in self._zones:
            raise KeyError(f"DNS zone not found: {request.resource_name}")
        return self._zones[resource_id]

    async def delete_resource(self, request: ResourceRequest) -> ResourceResponse:
        """
        Delete a DNS zone.
        
        Safety: Prevents deletion if zone has records (unless force=True in body).
        """
        resource_id = self.generate_resource_id(
            request.subscription_id,
            request.resource_group,
            request.resource_type,
            request.resource_name,
        )
        if resource_id not in self._zones:
            raise KeyError(f"DNS zone not found: {request.resource_name}")

        record_count = self._record_counts.get(resource_id, 0)
        force = request.body.get("force", False) if request.body else False

        if record_count > 0 and not force:
            raise ValueError(
                f"Cannot delete zone '{request.resource_name}' with {record_count} records. "
                f"Use force=True to delete anyway."
            )

        zone = self._zones.pop(resource_id)
        self._record_counts.pop(resource_id, None)
        zone.provisioning_state = ProvisioningState.SUCCEEDED
        return zone

    async def list_resources(self, request: ResourceRequest) -> ResourceListResponse:
        """List all DNS zones in a resource group."""
        prefix = f"/subscriptions/{request.subscription_id}/resourceGroups/{request.resource_group}"
        matching = [z for zid, z in self._zones.items() if zid.startswith(prefix)]
        return ResourceListResponse(value=matching)

    async def execute_action(self, request: ResourceRequest) -> ResourceResponse:
        """
        Execute custom actions on a DNS zone.
        
        Supported actions:
        - export: Generate zone file content
        - add_record: Add a DNS record (increments count)
        """
        resource_id = self.generate_resource_id(
            request.subscription_id,
            request.resource_group,
            request.resource_type,
            request.resource_name,
        )

        if resource_id not in self._zones:
            raise KeyError(f"DNS zone not found: {request.resource_name}")

        zone = self._zones[resource_id]

        if request.action == "export":
            # Generate a simplified zone file
            zone_file = (
                f"; Zone file for {request.resource_name}\n"
                f"$TTL {zone.properties.get('ttl', 3600)}\n"
                f"@ IN SOA ns1.itlcloud.net. admin.{request.resource_name}. (\n"
                f"    2026020701 ; Serial\n"
                f"    3600       ; Refresh\n"
                f"    900        ; Retry\n"
                f"    604800     ; Expire\n"
                f"    86400      ; Minimum TTL\n"
                f")\n"
            )
            zone.properties["exportedZoneFile"] = zone_file
            return zone

        elif request.action == "add_record":
            # Simulate adding a record
            self._record_counts[resource_id] = self._record_counts.get(resource_id, 0) + 1
            zone.properties["numberOfRecordSets"] = self._record_counts[resource_id]
            return zone

        else:
            raise NotImplementedError(f"Action '{request.action}' not supported")

    def validate_request(self, request: ResourceRequest) -> List[str]:
        """Validate DNS zone requests with business rules."""
        errors = super().validate_request(request)

        if request.body:
            zone_type = request.body.get("zoneType")
            if zone_type and zone_type not in self.ZONE_TYPES:
                errors.append(f"Invalid zoneType '{zone_type}'. Must be: {self.ZONE_TYPES}")

            ttl = request.body.get("ttl")
            if ttl is not None:
                if not isinstance(ttl, int) or ttl < 60 or ttl > 86400:
                    errors.append("TTL must be an integer between 60 and 86400")

        # Validate zone name format
        if request.resource_name:
            if not request.resource_name.endswith(".com") and not request.resource_name.endswith(".net") and not request.resource_name.endswith(".org"):
                pass  # Internal zones don't need TLD

        return errors


# ============================================================================
# DEMO: Full lifecycle with registry integration
# ============================================================================

async def main():
    """Demonstrate custom provider lifecycle."""
    print("=" * 60)
    print("Custom ResourceProvider Example: DNS Zones")
    print("=" * 60)

    # --- Register custom provider in registry ---
    registry = ResourceProviderRegistry()
    dns_provider = DnsZoneProvider()
    registry.register_provider("ITL.Network", "dnsZones", dns_provider)

    print(f"\nRegistered providers: {registry.list_providers()}")
    print(f"Provider info: {dns_provider.get_provider_info()}")
    print(f"Supports 'dnsZones': {dns_provider.supports_resource_type('dnsZones')}")
    print(f"Supports 'vms': {dns_provider.supports_resource_type('vms')}")

    # --- Create DNS zones ---
    print("\n" + "-" * 60)
    print("Creating DNS zones...")
    print("-" * 60)

    zone1_req = ResourceRequest(
        subscription_id="sub-001",
        resource_group="dns-rg",
        provider_namespace="ITL.Network",
        resource_type="dnsZones",
        resource_name="example.com",
        location="global",
        body={"zoneType": "Public", "ttl": 3600, "tags": {"env": "prod"}},
    )
    zone1 = await registry.create_or_update_resource("ITL.Network", "dnsZones", zone1_req)
    print(f"\nCreated: {zone1.name}")
    print(f"   Type:        {zone1.properties['zoneType']}")
    print(f"   TTL:         {zone1.properties['ttl']}")
    print(f"   Nameservers: {zone1.properties['nameServers']}")

    zone2_req = ResourceRequest(
        subscription_id="sub-001",
        resource_group="dns-rg",
        provider_namespace="ITL.Network",
        resource_type="dnsZones",
        resource_name="internal.local",
        location="global",
        body={"zoneType": "Private", "ttl": 300},
    )
    zone2 = await registry.create_or_update_resource("ITL.Network", "dnsZones", zone2_req)
    print(f"\nCreated: {zone2.name} (Private, TTL={zone2.properties['ttl']})")

    # --- Custom action: add records ---
    print("\n" + "-" * 60)
    print("Custom actions...")
    print("-" * 60)

    add_req = ResourceRequest(
        subscription_id="sub-001",
        resource_group="dns-rg",
        provider_namespace="ITL.Network",
        resource_type="dnsZones",
        resource_name="example.com",
        location="global",
        body={},
        action="add_record",
    )
    for i in range(3):
        result = await dns_provider.execute_action(add_req)
    print(f"\nAdded 3 records to {zone1.name}")
    print(f"   Record count: {result.properties['numberOfRecordSets']}")

    # --- Custom action: export zone file ---
    export_req = ResourceRequest(
        subscription_id="sub-001",
        resource_group="dns-rg",
        provider_namespace="ITL.Network",
        resource_type="dnsZones",
        resource_name="example.com",
        location="global",
        body={},
        action="export",
    )
    exported = await dns_provider.execute_action(export_req)
    print(f"\nExported zone file:\n{exported.properties['exportedZoneFile']}")

    # --- List zones ---
    print("-" * 60)
    print("Listing zones...")
    print("-" * 60)

    list_req = ResourceRequest(
        subscription_id="sub-001",
        resource_group="dns-rg",
        provider_namespace="ITL.Network",
        resource_type="dnsZones",
        resource_name="any",
        location="global",
        body={},
    )
    zones = await registry.list_resources("ITL.Network", "dnsZones", list_req)
    print(f"\nDNS Zones in dns-rg: {len(zones.value)}")
    for z in zones.value:
        print(f"   • {z.name} ({z.properties['zoneType']}, records={z.properties['numberOfRecordSets']})")

    # --- Delete with safety check ---
    print("\n" + "-" * 60)
    print("Delete with safety check...")
    print("-" * 60)

    try:
        await registry.delete_resource("ITL.Network", "dnsZones", zone1_req)
    except ValueError as e:
        print(f"\n Safety check: {e}")

    # Force delete
    force_req = ResourceRequest(
        subscription_id="sub-001",
        resource_group="dns-rg",
        provider_namespace="ITL.Network",
        resource_type="dnsZones",
        resource_name="example.com",
        location="global",
        body={"force": True},
    )
    deleted = await registry.delete_resource("ITL.Network", "dnsZones", force_req)
    print(f" Force deleted: {deleted.name}")

    # --- Validation error ---
    print("\n" + "-" * 60)
    print("Validation errors...")
    print("-" * 60)

    bad_req = ResourceRequest(
        subscription_id="sub-001",
        resource_group="dns-rg",
        provider_namespace="ITL.Network",
        resource_type="dnsZones",
        resource_name="bad-zone",
        location="global",
        body={"zoneType": "InvalidType", "ttl": 5},
    )
    errors = dns_provider.validate_request(bad_req)
    print(f"\n Validation errors for bad request:")
    for err in errors:
        print(f"   • {err}")

    print("\nAll Custom Provider examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
