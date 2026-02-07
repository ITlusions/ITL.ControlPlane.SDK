"""
Tenant Management Example

Demonstrates the multi-tenancy model in the ITL ControlPlane SDK:
1. Creating TenantSpec requests (with idempotency)
2. Building Tenant objects (the resource itself)
3. Tenant lifecycle states (Creating → Active → Suspended → Deleted)
4. Tenant validation rules (realm naming, contact email)
5. TenantResponse for API output

A Tenant = a Keycloak realm. Each tenant provides complete isolation
for users, roles, and organizations within it.
"""

from datetime import datetime
from uuid import uuid4

from itl_controlplane_sdk.identity.tenant import (
    TenantSpec,
    Tenant,
    TenantStatus,
    TenantResponse,
    TenantWithOrganizations,
)


# ============================================================================
# EXAMPLE 1: Create tenant specifications (API input)
# ============================================================================

def example_1_tenant_spec():
    """Create TenantSpec objects - the request contract for tenant creation."""
    print("=" * 60)
    print("EXAMPLE 1: TenantSpec (Creation Request)")
    print("=" * 60)

    # Basic tenant spec
    spec = TenantSpec(
        name="Acme Corporation",
        keycloak_realm_name="acme-prod",
        contact_email="admin@acme.com",
        description="Production tenant for Acme Corporation",
    )
    print(f"\nTenantSpec created:")
    print(f"   Name:           {spec.name}")
    print(f"   Realm:          {spec.keycloak_realm_name}")
    print(f"   Contact:        {spec.contact_email}")
    print(f"   Description:    {spec.description}")
    print(f"   Idempotency:    {spec.idempotency_key[:16]}...")

    # Spec with custom attributes
    enterprise_spec = TenantSpec(
        name="BigCorp Enterprise",
        keycloak_realm_name="bigcorp-enterprise",
        contact_email="platform@bigcorp.com",
        description="Enterprise tenant with premium features",
        attributes={
            "region": "eu-west-1",
            "tier": "enterprise",
            "max_users": 10000,
            "features": ["sso", "audit-log", "custom-domains"],
            "billing_id": "BILL-2026-001",
        },
    )
    print(f"\nEnterprise TenantSpec:")
    print(f"   Name:       {enterprise_spec.name}")
    print(f"   Attributes: {enterprise_spec.attributes}")

    # Idempotency: two specs with same data get DIFFERENT idempotency keys
    spec_a = TenantSpec(
        name="Test", keycloak_realm_name="test-a", contact_email="a@test.com",
    )
    spec_b = TenantSpec(
        name="Test", keycloak_realm_name="test-b", contact_email="b@test.com",
    )
    print(f"\nIdempotency keys are unique per request:")
    print(f"   Spec A: {spec_a.idempotency_key[:16]}...")
    print(f"   Spec B: {spec_b.idempotency_key[:16]}...")
    print(f"   Different: {spec_a.idempotency_key != spec_b.idempotency_key}")

    # Serialize to JSON (for API calls)
    json_data = spec.model_dump()
    print(f"\nSerialized to dict (for API):")
    for key, value in json_data.items():
        print(f"   {key}: {value}")


# ============================================================================
# EXAMPLE 2: Tenant validation rules
# ============================================================================

def example_2_validation():
    """Show validation rules for tenant creation."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Tenant Validation")
    print("=" * 60)

    # Invalid: realm name with uppercase
    try:
        TenantSpec(
            name="Bad Realm",
            keycloak_realm_name="Bad-Realm-Name",  # uppercase not allowed
            contact_email="admin@test.com",
        )
    except Exception as e:
        print(f"\n Uppercase realm name: {e}")

    # Invalid: realm name starting with hyphen
    try:
        TenantSpec(
            name="Hyphen Start",
            keycloak_realm_name="-bad-start",
            contact_email="admin@test.com",
        )
    except Exception as e:
        print(f" Hyphen-start realm: {e}")

    # Invalid: realm name with special characters
    try:
        TenantSpec(
            name="Special Chars",
            keycloak_realm_name="bad_realm!",
            contact_email="admin@test.com",
        )
    except Exception as e:
        print(f" Special chars in realm: {e}")

    # Invalid: bad email
    try:
        TenantSpec(
            name="Bad Email",
            keycloak_realm_name="valid-realm",
            contact_email="not-an-email",
        )
    except Exception as e:
        print(f" Invalid email: {e}")

    # Valid: lowercase, alphanumeric, hyphens
    valid = TenantSpec(
        name="Valid Tenant",
        keycloak_realm_name="valid-tenant-2026",
        contact_email="admin@valid.com",
    )
    print(f"\nValid spec: realm='{valid.keycloak_realm_name}'")


# ============================================================================
# EXAMPLE 3: Tenant resource lifecycle
# ============================================================================

def example_3_tenant_lifecycle():
    """Demonstrate tenant lifecycle states."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Tenant Lifecycle")
    print("=" * 60)

    tenant_id = f"tenant-{uuid4()}"

    # Create tenant in CREATING state
    tenant = Tenant(
        id=tenant_id,
        name="Acme Corp",
        keycloak_realm="acme-prod",
        contact_email="admin@acme.com",
        created_by="system-admin",
        status=TenantStatus.CREATING,
    )
    print(f"\nTenant created:")
    print(f"   ID:      {tenant.id}")
    print(f"   Status:  {tenant.status.value}")
    print(f"   Active:  {tenant.is_active()}")

    # Transition to ACTIVE (after Keycloak realm is created)
    tenant.status = TenantStatus.ACTIVE
    tenant.keycloak_realm_id = str(uuid4())
    tenant.updated_at = datetime.utcnow()
    tenant.updated_by = "system-admin"
    print(f"\n→ Status: {tenant.status.value}")
    print(f"  Active:  {tenant.is_active()}")
    print(f"  Realm ID: {tenant.keycloak_realm_id}")

    # Suspend tenant
    tenant.status = TenantStatus.SUSPENDED
    tenant.updated_at = datetime.utcnow()
    tenant.updated_by = "security-team"
    print(f"\n→ Status: {tenant.status.value}")
    print(f"  Active:     {tenant.is_active()}")
    print(f"  Deletable:  {tenant.is_deletable()}")

    # Soft delete
    tenant.status = TenantStatus.DELETING
    tenant.updated_at = datetime.utcnow()
    print(f"\n→ Status: {tenant.status.value}")

    tenant.status = TenantStatus.DELETED
    tenant.updated_at = datetime.utcnow()
    print(f"→ Status: {tenant.status.value}")
    print(f"  Active:     {tenant.is_active()}")
    print(f"  Deletable:  {tenant.is_deletable()}")

    # Lifecycle summary
    print(f"\nLifecycle: CREATING → ACTIVE → SUSPENDED → DELETING → DELETED")


# ============================================================================
# EXAMPLE 4: TenantResponse for API output
# ============================================================================

def example_4_api_response():
    """Create API responses from tenant objects."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: TenantResponse (API Output)")
    print("=" * 60)

    # Full tenant object (internal)
    tenant = Tenant(
        id=f"tenant-{uuid4()}",
        name="Acme Corp",
        keycloak_realm="acme-prod",
        keycloak_realm_id=str(uuid4()),
        status=TenantStatus.ACTIVE,
        contact_email="admin@acme.com",
        description="Production tenant",
        created_by="system-admin",
        organization_count=3,
        attributes={"tier": "enterprise", "region": "eu-west-1"},
    )

    # Convert to API response (hides internal fields like keycloak_realm_id)
    response = TenantResponse(
        id=tenant.id,
        name=tenant.name,
        keycloak_realm=tenant.keycloak_realm,
        status=tenant.status,
        contact_email=tenant.contact_email,
        description=tenant.description,
        created_at=tenant.created_at,
        organization_count=tenant.organization_count,
        attributes=tenant.attributes,
    )
    print(f"\nAPI Response:")
    response_dict = response.model_dump()
    for key, value in response_dict.items():
        print(f"   {key}: {value}")

    # Extended response with organizations
    extended = TenantWithOrganizations(
        **tenant.model_dump(),
        organizations=["org-001", "org-002", "org-003"],
    )
    print(f"\nExtended Response (with orgs):")
    print(f"   Organizations: {extended.organizations}")
    print(f"   Org count:     {extended.organization_count}")


# ============================================================================
# EXAMPLE 5: Simulated multi-tenant setup
# ============================================================================

def example_5_multi_tenant():
    """Simulate creating a multi-tenant environment."""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Multi-Tenant Setup")
    print("=" * 60)

    tenants = {}

    # Create tenants for different customers
    customer_configs = [
        {"name": "Acme Corp", "realm": "acme-prod", "email": "admin@acme.com", "tier": "enterprise"},
        {"name": "Widget Inc", "realm": "widget-prod", "email": "it@widget.io", "tier": "professional"},
        {"name": "StartupXYZ", "realm": "startupxyz-dev", "email": "dev@startupxyz.com", "tier": "starter"},
    ]

    for cfg in customer_configs:
        # Create spec
        spec = TenantSpec(
            name=cfg["name"],
            keycloak_realm_name=cfg["realm"],
            contact_email=cfg["email"],
            attributes={"tier": cfg["tier"]},
        )

        # Simulate creation → active
        tenant = Tenant(
            id=f"tenant-{uuid4()}",
            name=spec.name,
            keycloak_realm=spec.keycloak_realm_name,
            keycloak_realm_id=str(uuid4()),
            status=TenantStatus.ACTIVE,
            contact_email=spec.contact_email,
            created_by="platform-system",
            attributes=spec.attributes,
        )
        tenants[tenant.id] = tenant

    print(f"\nCreated {len(tenants)} tenants:")
    for tid, t in tenants.items():
        print(f"   • {t.name}")
        print(f"     Realm: {t.keycloak_realm}")
        print(f"     Tier:  {t.attributes.get('tier')}")
        print(f"     ID:    {tid[:30]}...")

    # Each tenant is completely isolated
    print(f"\nIsolation: Each tenant = separate Keycloak realm")
    print(f"   → Users in 'acme-prod' cannot see 'widget-prod' data")
    print(f"   → Roles/permissions are realm-scoped")
    print(f"   → Deletion of one tenant does not affect others")


if __name__ == "__main__":
    example_1_tenant_spec()
    example_2_validation()
    example_3_tenant_lifecycle()
    example_4_api_response()
    example_5_multi_tenant()
    print("\nAll Tenant Management examples completed!")
