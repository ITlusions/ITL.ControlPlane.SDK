"""
Voorbeeld 2 — Productie applicatieplatform
===========================================
Geschikt voor: productieworkloads die draaien op Kubernetes

Wat wordt aangemaakt:
  - Volledige Landing Zone (Resource Group + lock via ITLLandingZone)
  - AKS cluster (3 nodes, Standard_D4s_v5) met Flux GitOps
  - Defender for Cloud op VMs, Containers, AppServices en Storage
  - Alles geregistreerd in ITL ControlPlane

Vereiste env vars:
  ITL_CONTROLPLANE_ENDPOINT   https://api.itlusions.io
  ITL_CONTROLPLANE_TOKEN      <token>
  ITL_SUBSCRIPTION_ID         <azure-subscription-id>

Deployen:
  pulumi stack init production
  pulumi config set azure-native:location westeurope
  pulumi up
"""

import pulumi
from itl_controlplane_sdk.pulumi import (
    ITLLandingZone,
    AKSCluster,
    DefenderInitiative,
)

SUB_ID = "11111111-0000-0000-0000-000000000000"  # vervang door jouw sub
RG_NAME = "payments-prod-rg"

# ── Landing Zone (Resource Group + lock + ITL registratie) ───────────────────
lz = ITLLandingZone(
    "payments",
    subscription_id=SUB_ID,
    environment="production",
    owner="payments-team@itlusions.com",
    budget=8000,
    region="westeurope",
    # AKS via de landing zone zelf is ook mogelijk (aks_enabled=True),
    # maar hier definiëren we het los voor meer controle
    aks_enabled=False,
    defender_enabled=False,   # Defender apart hieronder
    azure_enabled=True,
    itl_enabled=True,
)

# ── AKS Cluster met Flux GitOps ───────────────────────────────────────────────
cluster = AKSCluster(
    "payments-aks",
    resource_group_name=lz.resource_group_name,
    location="westeurope",
    environment="production",
    node_count=3,
    node_vm_size="Standard_D4s_v5",
    kubernetes_version="1.29",
    flux_repo="https://github.com/ITlusions/itl-helm-charts",
    flux_branch="main",
    flux_path="clusters/payments-prod",
    subscription_id=SUB_ID,
    resource_group=RG_NAME,
    azure_enabled=True,
    itl_enabled=True,
    opts=pulumi.ResourceOptions(depends_on=[lz]),
)

# ── Defender for Cloud ────────────────────────────────────────────────────────
defender = DefenderInitiative(
    "payments-defender",
    subscription_id=SUB_ID,
    environment="production",
    plans=[
        "VirtualMachines",
        "Containers",
        "AppServices",
        "StorageAccounts",
        "KeyVaults",
    ],
    resource_group=RG_NAME,
    azure_enabled=True,
    itl_enabled=True,
    opts=pulumi.ResourceOptions(depends_on=[lz]),
)

# ── Exports ───────────────────────────────────────────────────────────────────
pulumi.export("resource_group_name",   lz.resource_group_name)
pulumi.export("cluster_name",          cluster.cluster_name)
pulumi.export("kube_config",           cluster.kube_config)
pulumi.export("policy_assignment_id",  defender.policy_assignment_id)
