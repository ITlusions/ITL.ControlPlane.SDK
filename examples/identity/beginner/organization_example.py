"""
Organization Management Example

Demonstrates organization management within a tenant:
1. OrganizationSpec - creation requests
2. Custom domains with DNS verification
3. Admin user management with roles
4. Organization lifecycle states
5. Multi-org within a single tenant

An Organization exists within a Tenant. Each tenant can have
multiple organizations, each with its own users, domains, and settings.
"""

from datetime import datetime
from uuid import uuid4

from itl_controlplane_sdk.identity.organization import (
    OrganizationSpec,
    OrganizationStatus,
    TenantAdminUser,
    TenantAdminRole,
    CustomDomain,
    DomainStatus,
    DomainVerificationMethod,
)


# ============================================================================
# EXAMPLE 1: Create organizations within a tenant
# ============================================================================

def example_1_create_organization():
    """Create OrganizationSpec objects for organization creation."""
    print("=" * 60)
    print("EXAMPLE 1: Creating Organizations")
    print("=" * 60)

    tenant_id = f"tenant-{uuid4()}"

    # Basic organization spec
    spec = OrganizationSpec(
        tenant_id=tenant_id,
        name="Acme Corporation",
        slug="acme-corp",
        owner_email="admin@acme.com",
        contact_email="support@acme.com",
        description="Main business organization",
    )
    print(f"\nOrganization Spec:")
    print(f"   Tenant:      {spec.tenant_id[:30]}...")
    print(f"   Name:        {spec.name}")
    print(f"   Slug:        {spec.slug}")
    print(f"   Owner:       {spec.owner_email}")
    print(f"   Idempotency: {spec.idempotency_key[:16]}...")

    # Organization with attributes
    dev_spec = OrganizationSpec(
        tenant_id=tenant_id,
        name="Acme Development",
        slug="acme-dev",
        owner_email="devlead@acme.com",
        contact_email="dev@acme.com",
        description="Development and testing organization",
        attributes={
            "environment": "development",
            "max_projects": 50,
            "cost_center": "CC-DEV-001",
        },
    )
    print(f"\nDev Organization Spec:")
    print(f"   Name:       {dev_spec.name}")
    print(f"   Attributes: {dev_spec.attributes}")

    # Serialize for API call
    print(f"\nJSON payload:")
    payload = spec.model_dump()
    for key, value in payload.items():
        display = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
        print(f"   {key}: {display}")


# ============================================================================
# EXAMPLE 2: Admin user management
# ============================================================================

def example_2_admin_users():
    """Create and manage admin users for organizations."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Admin User Management")
    print("=" * 60)

    # Organization admin (default role)
    org_admin = TenantAdminUser(
        user_id=str(uuid4()),
        username="john.admin",
        email="john.admin@acme.com",
        first_name="John",
        last_name="Smith",
    )
    print(f"\nOrganization Admin:")
    print(f"   Username: {org_admin.username}")
    print(f"   Email:    {org_admin.email}")
    print(f"   Roles:    {[r.value for r in org_admin.roles]}")

    # Tenant admin (can manage all organizations)
    tenant_admin = TenantAdminUser(
        user_id=str(uuid4()),
        username="sarah.super",
        email="sarah.super@acme.com",
        first_name="Sarah",
        last_name="Johnson",
        roles=[TenantAdminRole.TENANT_ADMIN, TenantAdminRole.DOMAIN_ADMIN],
    )
    print(f"\nTenant Admin (super user):")
    print(f"   Username: {tenant_admin.username}")
    print(f"   Roles:    {[r.value for r in tenant_admin.roles]}")

    # User admin (can only manage users)
    user_admin = TenantAdminUser(
        user_id=str(uuid4()),
        username="mike.hr",
        email="mike.hr@acme.com",
        first_name="Mike",
        last_name="Brown",
        roles=[TenantAdminRole.USER_ADMIN],
    )
    print(f"\nUser Admin:")
    print(f"   Username: {user_admin.username}")
    print(f"   Roles:    {[r.value for r in user_admin.roles]}")

    # Available roles summary
    print(f"\nAvailable Roles:")
    for role in TenantAdminRole:
        print(f"   • {role.value}")


# ============================================================================
# EXAMPLE 3: Custom domain management
# ============================================================================

def example_3_custom_domains():
    """Create and verify custom domains for SSO/email integration."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Custom Domain Management")
    print("=" * 60)

    # Primary domain (DNS TXT verification)
    primary_domain = CustomDomain(
        domain_name="acme.com",
        primary=True,
        status=DomainStatus.PENDING,
        verification_method=DomainVerificationMethod.DNS_TXT,
        verification_token="itl-verify-a7b3c4d5e6f78a9b",
    )
    print(f"\nPrimary Domain:")
    print(f"   Domain:       {primary_domain.domain_name}")
    print(f"   Primary:      {primary_domain.primary}")
    print(f"   Status:       {primary_domain.status.value}")
    print(f"   Verify via:   {primary_domain.verification_method.value}")
    print(f"   Token:        {primary_domain.verification_token}")
    print(f"\n   Add this DNS TXT record to verify:")
    print(f"      _itl-verify.{primary_domain.domain_name} TXT \"{primary_domain.verification_token}\"")

    # Simulate verification
    primary_domain.status = DomainStatus.VERIFIED
    primary_domain.verified_at = datetime.utcnow()
    print(f"\n   Domain verified at: {primary_domain.verified_at}")
    print(f"   Is verified: {primary_domain.is_verified()}")
    print(f"   Is primary:  {primary_domain.is_primary()}")

    # Secondary domain (CNAME verification)
    secondary_domain = CustomDomain(
        domain_name="mail.acme.com",
        primary=False,
        verification_method=DomainVerificationMethod.DNS_CNAME,
        verification_token="acme-verify.itlcloud.net",
    )
    print(f"\nSecondary Domain:")
    print(f"   Domain:  {secondary_domain.domain_name}")
    print(f"   Primary: {secondary_domain.primary}")
    print(f"   Status:  {secondary_domain.status.value}")
    print(f"   Verify:  CNAME {secondary_domain.domain_name} → {secondary_domain.verification_token}")

    # Domain validation
    print(f"\nDomain Validation:")
    try:
        bad_domain = CustomDomain(domain_name="not..valid.com", primary=False)
    except Exception as e:
        print(f"    Invalid domain: {e}")

    try:
        bad_domain = CustomDomain(domain_name="-bad.com", primary=False)
    except Exception as e:
        print(f"    Hyphen-start: {e}")

    # Domain statuses
    print(f"\nDomain Verification States:")
    for status in DomainStatus:
        print(f"   • {status.value}")


# ============================================================================
# EXAMPLE 4: Organization lifecycle
# ============================================================================

def example_4_lifecycle():
    """Demonstrate organization lifecycle states."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Organization Lifecycle")
    print("=" * 60)

    print(f"\nOrganization States:")
    for status in OrganizationStatus:
        desc = {
            "creating": "Being set up (Keycloak groups, initial config)",
            "active": "Fully operational (users can log in)",
            "suspended": "Temporarily disabled (no API access)",
            "deleting": "Being removed (cleanup in progress)",
            "deleted": "Soft-deleted (kept for audit trail)",
        }
        print(f"   {status.value:12s} → {desc.get(status.value, '')}")

    print(f"\nLifecycle Flow:")
    print(f"   CREATING → ACTIVE → SUSPENDED → DELETING → DELETED")
    print(f"                  ↑         ↓")
    print(f"                  └─────────┘  (reactivation)")


# ============================================================================
# EXAMPLE 5: Multi-org within a tenant
# ============================================================================

def example_5_multi_org():
    """Simulate multiple organizations within a single tenant."""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Multi-Organization Setup")
    print("=" * 60)

    tenant_id = f"tenant-{uuid4()}"
    orgs = []

    org_configs = [
        {"name": "Acme HQ", "slug": "acme-hq", "email": "admin@acme.com",
         "domain": "acme.com", "users": 250},
        {"name": "Acme Europe", "slug": "acme-eu", "email": "eu-admin@acme.com",
         "domain": "eu.acme.com", "users": 120},
        {"name": "Acme Asia", "slug": "acme-asia", "email": "asia-admin@acme.com",
         "domain": "asia.acme.com", "users": 80},
    ]

    for cfg in org_configs:
        spec = OrganizationSpec(
            tenant_id=tenant_id,
            name=cfg["name"],
            slug=cfg["slug"],
            owner_email=cfg["email"],
            contact_email=cfg["email"],
            attributes={"estimated_users": cfg["users"]},
        )

        domain = CustomDomain(
            domain_name=cfg["domain"],
            primary=True,
            status=DomainStatus.VERIFIED,
            verified_at=datetime.utcnow(),
        )

        admin = TenantAdminUser(
            user_id=str(uuid4()),
            username=f"admin-{cfg['slug']}",
            email=cfg["email"],
            roles=[TenantAdminRole.ORGANIZATION_ADMIN],
        )

        orgs.append({"spec": spec, "domain": domain, "admin": admin})

    print(f"\nTenant: {tenant_id[:30]}...")
    print(f"   Organizations: {len(orgs)}")
    for org in orgs:
        s = org["spec"]
        d = org["domain"]
        a = org["admin"]
        print(f"\n   {s.name} ({s.slug})")
        print(f"      Domain: {d.domain_name} ({d.status.value})")
        print(f"      Admin:  {a.username} ({', '.join(r.value for r in a.roles)})")
        print(f"      Users:  ~{s.attributes.get('estimated_users', 0)}")

    print(f"\nIsolation:")
    print(f"   → All orgs share one Keycloak realm (tenant)")
    print(f"   → Each org has separate users, roles, domains")
    print(f"   → Org admins can only manage their own org")
    print(f"   → Tenant admins can manage all orgs")


if __name__ == "__main__":
    example_1_create_organization()
    example_2_admin_users()
    example_3_custom_domains()
    example_4_lifecycle()
    example_5_multi_org()
    print("\nAll Organization Management examples completed!")
