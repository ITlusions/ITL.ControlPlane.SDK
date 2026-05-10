"""
Voorbeeld 3 — Enterprise multi-tenant omgeving
===============================================
Geschikt voor: grote organisaties met meerdere teams en subscriptions

Topologie:
  Management Group: itl-enterprise
  ├── Management Group: team-payments  (sub: sub-payments)
  │   ├── Landing Zone: payments-prod
  │   └── Landing Zone: payments-staging
  └── Management Group: team-platform  (sub: sub-platform)
      ├── Landing Zone: platform-prod (met AKS + Flux)
      └── Defender op platform subscription

Alle resources worden zowel in Azure als in het ITL ControlPlane
geregistreerd voor unified governance en compliance.

Vereiste env vars:
  ITL_CONTROLPLANE_ENDPOINT   https://api.itlusions.io
  ITL_CONTROLPLANE_TOKEN      <token>
  ITL_SUBSCRIPTION_ID         <hoofd-subscription-id>

Deployen:
  pulumi stack init enterprise
  pulumi config set azure-native:location westeurope
  pulumi up
"""

import pulumi
from itl_controlplane_sdk.pulumi import (
    ManagementGroup,
    ITLLandingZone,
    AKSCluster,
    DefenderInitiative,
)

# ── Subscription IDs ─────────────────────────────────────────────────────────
SUB_PAYMENTS  = "22222222-0000-0000-0000-000000000001"
SUB_PLATFORM  = "22222222-0000-0000-0000-000000000002"

# ── Management Groups ─────────────────────────────────────────────────────────
mg_root = ManagementGroup(
    "itl-enterprise",
    display_name="ITL Enterprise",
    group_id="itl-enterprise",
    azure_enabled=True,
    itl_enabled=True,
)

mg_payments = ManagementGroup(
    "team-payments",
    display_name="Team Payments",
    group_id="team-payments",
    parent_id=mg_root.management_group_id,
    subscription_ids=[SUB_PAYMENTS],
    azure_enabled=True,
    itl_enabled=True,
    opts=pulumi.ResourceOptions(depends_on=[mg_root]),
)

mg_platform = ManagementGroup(
    "team-platform",
    display_name="Team Platform",
    group_id="team-platform",
    parent_id=mg_root.management_group_id,
    subscription_ids=[SUB_PLATFORM],
    azure_enabled=True,
    itl_enabled=True,
    opts=pulumi.ResourceOptions(depends_on=[mg_root]),
)

# ── Landing Zones: Payments ───────────────────────────────────────────────────
lz_payments_prod = ITLLandingZone(
    "payments-prod",
    subscription_id=SUB_PAYMENTS,
    environment="production",
    owner="payments-team@itlusions.com",
    budget=10000,
    region="westeurope",
    aks_enabled=False,
    defender_enabled=True,
    azure_enabled=True,
    itl_enabled=True,
    opts=pulumi.ResourceOptions(depends_on=[mg_payments]),
)

lz_payments_staging = ITLLandingZone(
    "payments-staging",
    subscription_id=SUB_PAYMENTS,
    environment="staging",
    owner="payments-team@itlusions.com",
    budget=2000,
    region="westeurope",
    aks_enabled=False,
    defender_enabled=False,
    azure_enabled=True,
    itl_enabled=True,
    opts=pulumi.ResourceOptions(depends_on=[mg_payments]),
)

# ── Landing Zone: Platform (met AKS voor shared services) ────────────────────
lz_platform = ITLLandingZone(
    "platform-prod",
    subscription_id=SUB_PLATFORM,
    environment="production",
    owner="platform-team@itlusions.com",
    budget=20000,
    region="westeurope",
    aks_enabled=False,      # AKS los definiëren voor meer controle
    defender_enabled=False,
    azure_enabled=True,
    itl_enabled=True,
    opts=pulumi.ResourceOptions(depends_on=[mg_platform]),
)

# Shared services cluster (ingress, monitoring, ArgoCD fallback)
platform_cluster = AKSCluster(
    "platform-aks",
    resource_group_name=lz_platform.resource_group_name,
    location="westeurope",
    environment="production",
    node_count=5,
    node_vm_size="Standard_D8s_v5",
    kubernetes_version="1.29",
    flux_repo="https://github.com/ITlusions/itl-platform-gitops",
    flux_branch="main",
    flux_path="clusters/platform-prod",
    subscription_id=SUB_PLATFORM,
    resource_group="platform-prod-rg",
    azure_enabled=True,
    itl_enabled=True,
    opts=pulumi.ResourceOptions(depends_on=[lz_platform]),
)

# Defender op de platform subscription (dekt AKS + storage + KV)
platform_defender = DefenderInitiative(
    "platform-defender",
    subscription_id=SUB_PLATFORM,
    environment="production",
    plans=[
        "VirtualMachines",
        "Containers",
        "StorageAccounts",
        "KeyVaults",
        "Arm",
        "Dns",
    ],
    resource_group="platform-prod-rg",
    azure_enabled=True,
    itl_enabled=True,
    opts=pulumi.ResourceOptions(depends_on=[lz_platform]),
)

# ── Exports ───────────────────────────────────────────────────────────────────
pulumi.export("mg_root_id",               mg_root.management_group_id)
pulumi.export("mg_payments_id",           mg_payments.management_group_id)
pulumi.export("mg_platform_id",           mg_platform.management_group_id)
pulumi.export("payments_prod_rg",         lz_payments_prod.resource_group_name)
pulumi.export("payments_staging_rg",      lz_payments_staging.resource_group_name)
pulumi.export("platform_rg",              lz_platform.resource_group_name)
pulumi.export("platform_cluster_name",    platform_cluster.cluster_name)
pulumi.export("platform_kube_config",     platform_cluster.kube_config)
pulumi.export("platform_defender_id",     platform_defender.policy_assignment_id)
