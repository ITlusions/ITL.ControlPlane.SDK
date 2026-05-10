"""
Voorbeeld 5 — Multi-region Disaster Recovery
=============================================
Geschikt voor: HA/DR vereisten, RPO < 1 min, RTO < 5 min

Topologie:
  Traffic Manager (Performance routing)
  ├── westeurope  [PRIMARY]  — volledige AKS workload
  └── northeurope [FAILOVER] — warm-standby AKS, lager node count

Elke regio heeft:
  - Eigen Resource Group (met delete-lock)
  - AKS cluster gestuurd door Flux (zelfde repo, regio-specifieke path)
  - Defender initiative

DR scenario:
  - Traffic Manager detecteert unhealthy primary via /healthz probe
  - Automatische failover naar northeurope binnen 30 seconden
  - ITL ControlPlane weet van beide clusters via itl_enabled=True
    → centrale visibility over welke regio actief is

Vereiste pulumi config:
  pulumi config set primary_node_count 4
  pulumi config set dr_node_count 2

Deployen:
  pulumi stack init dr-prod
  pulumi config set azure-native:location westeurope
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
cfg             = pulumi.Config()
PRIMARY_NODES   = cfg.get_int("primary_node_count", 4)
DR_NODES        = cfg.get_int("dr_node_count", 2)
SUB_ID          = "44444444-0000-0000-0000-000000000000"
GITOPS_REPO     = "https://github.com/ITlusions/itl-helm-charts"
K8S_VERSION     = "1.29"

REGIONS = {
    "primary": {
        "location": "westeurope",
        "suffix":   "weu",
        "flux_path": "clusters/payments-weu",
        "nodes":    PRIMARY_NODES,
        "priority": 1,
    },
    "dr": {
        "location": "northeurope",
        "suffix":   "neu",
        "flux_path": "clusters/payments-neu",
        "nodes":    DR_NODES,
        "priority": 10,
    },
}

# ── Per-regio resources ───────────────────────────────────────────────────────
resource_groups: dict[str, ResourceGroup] = {}
clusters:        dict[str, AKSCluster]    = {}

for role, cfg_r in REGIONS.items():
    loc  = cfg_r["location"]
    sfx  = cfg_r["suffix"]
    rg_name = f"payments-{sfx}"

    rg = ResourceGroup(
        rg_name,
        location=loc,
        environment="production",
        owner="platform-team@itlusions.com",
        subscription_id=SUB_ID,
        lock=True,
        azure_enabled=True,
        itl_enabled=True,
    )
    resource_groups[role] = rg

    cluster = AKSCluster(
        f"payments-aks-{sfx}",
        resource_group_name=rg.resource_group_name,
        location=loc,
        environment="production",
        node_count=cfg_r["nodes"],
        node_vm_size="Standard_D4s_v5",
        kubernetes_version=K8S_VERSION,
        flux_repo=GITOPS_REPO,
        flux_branch="main",
        flux_path=cfg_r["flux_path"],
        subscription_id=SUB_ID,
        resource_group=rg_name,
        azure_enabled=True,
        itl_enabled=True,
        opts=pulumi.ResourceOptions(depends_on=[rg]),
    )
    clusters[role] = cluster

    DefenderInitiative(
        f"payments-defender-{sfx}",
        subscription_id=SUB_ID,
        environment="production",
        plans=["Containers", "KeyVaults", "StorageAccounts"],
        resource_group=rg_name,
        azure_enabled=True,
        itl_enabled=True,
        opts=pulumi.ResourceOptions(depends_on=[rg]),
    )

# ── Traffic Manager — performance routing met automatische failover ───────────
# Gebruik de primary RG als container voor het TM profiel
tm_rg = resource_groups["primary"]

tm_profile = az_network.TrafficManagerProfile(
    "payments-dr-tm",
    resource_group_name=tm_rg.resource_group_name,
    profile_status="Enabled",
    traffic_routing_method="Performance",   # stuurt naar dichtstbijzijnde gezonde regio
    dns_config=az_network.DnsConfigArgs(
        relative_name="itl-payments-dr",
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
    opts=pulumi.ResourceOptions(depends_on=[tm_rg]),
)

for role, cfg_r in REGIONS.items():
    sfx     = cfg_r["suffix"]
    cluster = clusters[role]

    az_network.TrafficManagerExternalEndpoint(
        f"payments-ep-{sfx}",
        resource_group_name=tm_rg.resource_group_name,
        profile_name=tm_profile.name,
        endpoint_status="Enabled",
        target=cluster.cluster_name.apply(
            lambda n, loc=cfg_r["location"]: f"{n}.hcp.{loc}.azmk8s.io"
        ),
        endpoint_location=cfg_r["location"],
        priority=cfg_r["priority"],
        opts=pulumi.ResourceOptions(depends_on=[tm_profile, cluster]),
    )

# ── Exports ───────────────────────────────────────────────────────────────────
pulumi.export("traffic_manager_fqdn",       tm_profile.dns_config.apply(lambda d: d.fqdn))
pulumi.export("primary_cluster_name",       clusters["primary"].cluster_name)
pulumi.export("dr_cluster_name",            clusters["dr"].cluster_name)
pulumi.export("primary_rg",                 resource_groups["primary"].resource_group_name)
pulumi.export("dr_rg",                      resource_groups["dr"].resource_group_name)
pulumi.export("primary_kube_config",        clusters["primary"].kube_config)
pulumi.export("dr_kube_config",             clusters["dr"].kube_config)
