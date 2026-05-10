"""
Voorbeeld 6 — Pulumi Automation API: programmatisch tenant provisioning
========================================================================
Geschikt voor: SaaS platforms, self-service portals, CI/CD pipelines

Dit voorbeeld is géén Pulumi program dat je direct met `pulumi up` draait.
Het is een Python script dat de Pulumi Automation API gebruikt om stacks
programmatisch te beheren — zonder de Pulumi CLI interactief aan te roepen.

Use case: ITL platform portal ontvangt een "nieuwe tenant aanmaken" verzoek
via een REST API → roept dit script aan → Pulumi stack wordt aangemaakt en
gedeployed → portal toont de outputs aan de gebruiker.

Wat het script doet:
  1. Definieer een Pulumi program inline (als Python functie)
  2. Maak of select de stack via de Automation API
  3. Configureer azure-native region en stack-specifieke config
  4. Voer `up()` uit met live streaming output
  5. Lees outputs terug en return ze naar de aanroeper
  6. Optioneel: `destroy()` + `remove()` voor tenant offboarding

Vereiste env vars:
  PULUMI_ACCESS_TOKEN         <pulumi-cloud-token>  (of gebruik lokale backend)
  ITL_CONTROLPLANE_ENDPOINT   https://api.itlusions.io
  ITL_CONTROLPLANE_TOKEN      <token>
  AZURE_CLIENT_ID / AZURE_CLIENT_SECRET / AZURE_TENANT_ID  (service principal)

Uitvoeren:
  python provision_tenant.py --tenant acme --env production --budget 3000
  python provision_tenant.py --tenant acme --destroy
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from typing import Any, Dict

import pulumi
import pulumi.automation as auto

from itl_controlplane_sdk.pulumi import (
    ITLLandingZone,
    AKSCluster,
    DefenderInitiative,
)

# ── Inline Pulumi program (wordt uitgevoerd inside de Automation API) ─────────

def make_tenant_program(
    tenant_name: str,
    subscription_id: str,
    environment: str,
    budget: int,
    aks_enabled: bool,
    gitops_repo: str,
) -> auto.PulumiFn:
    """
    Factory die een Pulumi program functie teruggeeft voor één tenant.
    De closure vangt de tenant-specifieke parameters in.
    """

    def program() -> None:
        lz = ITLLandingZone(
            tenant_name,
            subscription_id=subscription_id,
            environment=environment,
            owner=f"{tenant_name}-ops@itlusions.com",
            budget=budget,
            region="westeurope",
            aks_enabled=False,
            defender_enabled=True,
            azure_enabled=True,
            itl_enabled=True,
        )

        if aks_enabled:
            cluster = AKSCluster(
                f"{tenant_name}-aks",
                resource_group_name=lz.resource_group_name,
                location="westeurope",
                environment=environment,
                node_count=2,
                node_vm_size="Standard_D2s_v5",
                kubernetes_version="1.29",
                flux_repo=gitops_repo,
                flux_branch="main",
                flux_path=f"clusters/{tenant_name}",
                subscription_id=subscription_id,
                resource_group=f"{tenant_name}-rg",
                azure_enabled=True,
                itl_enabled=True,
                opts=pulumi.ResourceOptions(depends_on=[lz]),
            )
            pulumi.export("cluster_name", cluster.cluster_name)
            pulumi.export("kube_config",  cluster.kube_config)

        pulumi.export("resource_group_name", lz.resource_group_name)
        pulumi.export("resource_group_id",   lz.resource_group_id)

    return program


# ── Automation API helpers ─────────────────────────────────────────────────────

PULUMI_ORG     = os.environ.get("PULUMI_ORG", "itlusions")
PULUMI_PROJECT = "itl-tenant-provisioner"


def _stack_name(tenant: str, env: str) -> str:
    return f"{PULUMI_ORG}/{PULUMI_PROJECT}/{tenant}-{env}"


async def provision_tenant(
    tenant_name: str,
    subscription_id: str,
    environment: str = "production",
    budget: int = 2000,
    aks_enabled: bool = False,
    gitops_repo: str = "https://github.com/ITlusions/itl-helm-charts",
) -> Dict[str, Any]:
    """
    Provisioning van een nieuwe tenant via de Pulumi Automation API.
    Geeft de stack outputs terug als dict.
    """
    program = make_tenant_program(
        tenant_name, subscription_id, environment, budget, aks_enabled, gitops_repo
    )

    print(f"[*] Provisioning tenant '{tenant_name}' (env={environment}) ...")

    stack = await auto.create_or_select_stack(
        stack_name=f"{tenant_name}-{environment}",
        project_name=PULUMI_PROJECT,
        program=program,
    )

    # Stack configuratie
    await stack.set_config("azure-native:location", auto.ConfigValue("westeurope"))
    await stack.set_config("azure-native:subscriptionId", auto.ConfigValue(subscription_id))

    # Streaming output zodat CI/CD logs leesbaar zijn
    def on_output(msg: str) -> None:
        print(f"  | {msg}", end="")

    result = await stack.up(on_output=on_output)

    print(f"\n[✓] Tenant '{tenant_name}' provisioned. Summary: {result.summary.result}")

    return {k: v.value for k, v in result.outputs.items()}


async def deprovision_tenant(tenant_name: str, environment: str = "production") -> None:
    """
    Verwijder alle resources van een tenant (offboarding).
    Stack wordt vernietigd én verwijderd uit de Pulumi backend.
    """
    print(f"[!] Destroying tenant '{tenant_name}' (env={environment}) ...")

    # Selecteer bestaande stack (program kan leeg zijn bij destroy)
    stack = await auto.select_stack(
        stack_name=f"{tenant_name}-{environment}",
        project_name=PULUMI_PROJECT,
        program=lambda: None,
    )

    def on_output(msg: str) -> None:
        print(f"  | {msg}", end="")

    await stack.destroy(on_output=on_output)
    stack.workspace.remove_stack(f"{tenant_name}-{environment}")

    print(f"\n[✓] Tenant '{tenant_name}' verwijderd.")


# ── CLI entrypoint ─────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ITL Tenant Provisioner")
    parser.add_argument("--tenant",     required=True,  help="Tenant naam (lowercase, geen spaties)")
    parser.add_argument("--env",        default="production", choices=["development", "staging", "production"])
    parser.add_argument("--sub",        default=os.environ.get("ITL_SUBSCRIPTION_ID", ""), help="Azure subscription ID")
    parser.add_argument("--budget",     type=int, default=2000, help="Maandelijks budget in EUR")
    parser.add_argument("--aks",        action="store_true", help="AKS cluster inschakelen")
    parser.add_argument("--gitops-repo",default="https://github.com/ITlusions/itl-helm-charts")
    parser.add_argument("--destroy",    action="store_true", help="Tenant verwijderen (offboarding)")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    if args.destroy:
        await deprovision_tenant(args.tenant, args.env)
        return

    if not args.sub:
        print("ERROR: --sub of ITL_SUBSCRIPTION_ID is vereist", file=sys.stderr)
        sys.exit(1)

    outputs = await provision_tenant(
        tenant_name=args.tenant,
        subscription_id=args.sub,
        environment=args.env,
        budget=args.budget,
        aks_enabled=args.aks,
        gitops_repo=args.gitops_repo,
    )

    print("\n── Stack outputs ─────────────────────────────")
    for key, value in outputs.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
