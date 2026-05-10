"""
Voorbeeld 1 — Minimale ontwikkelomgeving
=========================================
Geschikt voor: feature branches, proof-of-concept, lokale sandbox

Wat wordt aangemaakt:
  - Eén Resource Group in westeurope
  - Geen AKS, geen Defender (kost beperken)
  - Registratie in ITL ControlPlane (itl_enabled=True)

Vereiste env vars:
  ITL_CONTROLPLANE_ENDPOINT   https://api.itlusions.io
  ITL_CONTROLPLANE_TOKEN      <token>
  ITL_SUBSCRIPTION_ID         <azure-subscription-id>

Deployen:
  pulumi stack init dev
  pulumi config set azure-native:location westeurope
  pulumi up
"""

import pulumi
from itl_controlplane_sdk.pulumi import ResourceGroup

SUB_ID = "00000000-0000-0000-0000-000000000000"  # vervang door jouw sub

# ── Resource Group ────────────────────────────────────────────────────────────
rg = ResourceGroup(
    "dev-sandbox",
    location="westeurope",
    environment="development",
    owner="developer@itlusions.com",
    subscription_id=SUB_ID,
    lock=False,          # geen delete-lock in dev
    azure_enabled=True,
    itl_enabled=True,
)

# ── Exports ───────────────────────────────────────────────────────────────────
pulumi.export("resource_group_name", rg.resource_group_name)
pulumi.export("resource_group_id",   rg.resource_group_id)
