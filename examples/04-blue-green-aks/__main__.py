"""
Voorbeeld 4 — Blue/Green AKS deployment
=========================================
Geschikt voor: zero-downtime upgrades, canary releases, cluster-level migraties

Strategie:
  - Twee AKS clusters in dezelfde resource group: *blue* (live) en *green* (standby)
  - Pulumi config bepaalt welk cluster actief is: ``active_slot = "blue" | "green"``
  - Flux wijst elk cluster naar een andere kustomization path:
      clusters/payments-blue  →  live manifests
      clusters/payments-green →  next-version manifests
  - Na validatie: verander active_slot en run `pulumi up` → Traffic Manager
    wisselt automatisch

Wat wordt aangemaakt:
  - 1 Resource Group
  - 2 AKS clusters (blue + green, elk met eigen Flux path)
  - Defender initiative op de subscription
  - Azure Traffic Manager profiel (priority routing)
  - Beide clusters geregistreerd in ITL ControlPlane

Vereiste pulumi config:
  pulumi config set active_slot blue    # of "green"
  pulumi config set node_count 3
  pulumi config set kubernetes_version 1.29

Deployen:
  pulumi stack init payments-prod
  pulumi config set azure-native:location westeurope
  pulumi config set active_slot blue
  pulumi up

Upgraden naar green:
  pulumi config set kubernetes_version 1.30   # update green cluster
  # test green cluster ...
  pulumi config set active_slot green          # wissel Traffic Manager
  pulumi up
"""

from __future__ import annotations

import pulumi
import pulumi_azure_native.network as az_network
from itl_controlplane_sdk.pulumi import (
    ResourceGroup,
    AKSCluster,
    DefenderInitiative,
)

# ── Config ────────────────────────────────────────────────────────────────────
cfg = pulumi.Config()
ACTIVE_SLOT      = cfg.get("active_slot", "blue")        # "blue" | "green"
NODE_COUNT       = cfg.get_int("node_count", 3)
K8S_VERSION      = cfg.get("kubernetes_version", "1.29")
SUB_ID           = "33333333-0000-0000-0000-000000000000"
GITOPS_REPO      = "https://github.com/ITlusions/itl-helm-charts"

assert ACTIVE_SLOT in ("blue", "green"), "active_slot moet 'blue' of 'green' zijn"

# Slot weights: actief slot krijgt priority 1, standby priority 10
slot_priority = {"blue": 1, "green": 10} if ACTIVE_SLOT == "blue" else {"blue": 10, "green": 1}

# ── Resource Group ────────────────────────────────────────────────────────────
rg = ResourceGroup(
    "payments-bluegreen",
    location="westeurope",
    environment="production",
    owner="payments-team@itlusions.com",
    subscription_id=SUB_ID,
    lock=True,
    azure_enabled=True,
    itl_enabled=True,
)

# ── AKS Blue ──────────────────────────────────────────────────────────────────
cluster_blue = AKSCluster(
    "payments-aks-blue",
    resource_group_name=rg.resource_group_name,
    location="westeurope",
    environment="production",
    node_count=NODE_COUNT,
    node_vm_size="Standard_D4s_v5",
    kubernetes_version="1.29",          # blue blijft stabiele versie
    flux_repo=GITOPS_REPO,
    flux_branch="main",
    flux_path="clusters/payments-blue",
    subscription_id=SUB_ID,
    resource_group="payments-bluegreen",
    azure_enabled=True,
    itl_enabled=True,
    opts=pulumi.ResourceOptions(depends_on=[rg]),
)

# ── AKS Green ─────────────────────────────────────────────────────────────────
cluster_green = AKSCluster(
    "payments-aks-green",
    resource_group_name=rg.resource_group_name,
    location="westeurope",
    environment="production",
    node_count=NODE_COUNT,
    node_vm_size="Standard_D4s_v5",
    kubernetes_version=K8S_VERSION,     # green krijgt de nieuwe versie
    flux_repo=GITOPS_REPO,
    flux_branch="main",
    flux_path="clusters/payments-green",
    subscription_id=SUB_ID,
    resource_group="payments-bluegreen",
    azure_enabled=True,
    itl_enabled=True,
    opts=pulumi.ResourceOptions(depends_on=[rg]),
)

# ── Azure Traffic Manager (priority routing) ──────────────────────────────────
tm_profile = az_network.TrafficManagerProfile(
    "payments-tm",
    resource_group_name=rg.resource_group_name,
    profile_status="Enabled",
    traffic_routing_method="Priority",
    dns_config=az_network.DnsConfigArgs(
        relative_name="itl-payments",
        ttl=30,
    ),
    monitor_config=az_network.MonitorConfigArgs(
        protocol="HTTPS",
        port=443,
        path="/healthz",
        interval_in_seconds=10,
        timeout_in_seconds=5,
        tolerated_number_of_failures=2,
    ),
    opts=pulumi.ResourceOptions(depends_on=[rg]),
)

# Endpoint blue
tm_endpoint_blue = az_network.TrafficManagerExternalEndpoint(
    "payments-ep-blue",
    resource_group_name=rg.resource_group_name,
    profile_name=tm_profile.name,
    endpoint_status="Enabled",
    target=cluster_blue.cluster_name.apply(lambda n: f"{n}.hcp.westeurope.azmk8s.io"),
    priority=slot_priority["blue"],
    opts=pulumi.ResourceOptions(depends_on=[tm_profile, cluster_blue]),
)

# Endpoint green
tm_endpoint_green = az_network.TrafficManagerExternalEndpoint(
    "payments-ep-green",
    resource_group_name=rg.resource_group_name,
    profile_name=tm_profile.name,
    endpoint_status="Enabled",
    target=cluster_green.cluster_name.apply(lambda n: f"{n}.hcp.westeurope.azmk8s.io"),
    priority=slot_priority["green"],
    opts=pulumi.ResourceOptions(depends_on=[tm_profile, cluster_green]),
)

# ── Defender ──────────────────────────────────────────────────────────────────
defender = DefenderInitiative(
    "payments-bluegreen-defender",
    subscription_id=SUB_ID,
    environment="production",
    plans=["VirtualMachines", "Containers", "KeyVaults"],
    resource_group="payments-bluegreen",
    azure_enabled=True,
    itl_enabled=True,
    opts=pulumi.ResourceOptions(depends_on=[rg]),
)

# ── Exports ───────────────────────────────────────────────────────────────────
pulumi.export("active_slot",          ACTIVE_SLOT)
pulumi.export("traffic_manager_fqdn", tm_profile.dns_config.apply(lambda d: d.fqdn))
pulumi.export("blue_cluster_name",    cluster_blue.cluster_name)
pulumi.export("green_cluster_name",   cluster_green.cluster_name)
pulumi.export("blue_priority",        slot_priority["blue"])
pulumi.export("green_priority",       slot_priority["green"])
