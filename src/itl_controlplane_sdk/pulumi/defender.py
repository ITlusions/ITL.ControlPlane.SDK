"""
DefenderInitiative — ITL Pulumi component for Microsoft Defender for Cloud.

Deploys a Defender for Cloud policy initiative to Azure and/or registers it
with the ITL ControlPlane API.

Usage::

    import pulumi
    from itl_controlplane_sdk.pulumi.defender import DefenderInitiative

    initiative = DefenderInitiative(
        "payments-defender",
        subscription_id="00000000-0000-0000-0000-000000000000",
        environment="production",
        plans=["VirtualMachines", "SqlServers", "AppServices", "StorageAccounts"],
        azure_enabled=True,
        itl_enabled=True,
    )

    pulumi.export("policy_assignment_id", initiative.policy_assignment_id)
"""

from __future__ import annotations

from typing import List, Optional, Sequence

import pulumi
from pulumi import Input, Output

from .component import ITLPulumiComponent

try:
    import pulumi_azure_native.authorization as az_authz  # type: ignore[import-untyped]
    import pulumi_azure_native.security as az_security  # type: ignore[import-untyped]
    _AZURE_NATIVE_AVAILABLE = True
except ImportError:
    _AZURE_NATIVE_AVAILABLE = False


# Defender for Cloud built-in initiative definition ID
_MCSB_INITIATIVE_ID = (
    "/providers/Microsoft.Authorization/policySetDefinitions/"
    "1f3afdf9-d0c9-4c3d-847f-89da613e70a8"  # Microsoft Cloud Security Benchmark
)

_DEFAULT_PLANS: List[str] = [
    "VirtualMachines",
    "SqlServers",
    "AppServices",
    "StorageAccounts",
    "KeyVaults",
    "Dns",
    "Arm",
    "Containers",
]


class DefenderInitiative(ITLPulumiComponent):
    """Deploy Microsoft Defender for Cloud initiative.

    Azure side
    ----------
    - Assigns the **Microsoft Cloud Security Benchmark** (MCSB) policy initiative
      to the target subscription.
    - Enables the requested Defender for Cloud pricing plans.

    ITL side
    --------
    - Registers the security initiative with the ITL ControlPlane policy
      registry so it appears in the unified compliance report.

    Args:
        name:              Logical component name.
        subscription_id:   Azure subscription ID to protect.
        environment:       Deployment environment tag (e.g. ``"production"``).
        plans:             Defender pricing plans to enable.  Defaults to all
                           standard plans.
        azure_enabled:     Deploy to Azure (default ``True``).
        itl_enabled:       Register with ITL ControlPlane (default ``True``).
        itl_endpoint:      ITL ControlPlane API base URL.
        opts:              Pulumi resource options.

    Outputs:
        policy_assignment_id:  Azure policy assignment resource ID.
        registered_plans:      List of enabled Defender plans.
    """

    policy_assignment_id: Output[str]
    registered_plans: Output[List[str]]

    def __init__(
        self,
        name: str,
        *,
        subscription_id: Input[str],
        environment: str = "production",
        plans: Optional[List[str]] = None,
        resource_group: Optional[str] = None,
        azure_enabled: bool = True,
        itl_enabled: bool = True,
        itl_endpoint: Optional[str] = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        sub_id_str = subscription_id if isinstance(subscription_id, str) else None
        super().__init__(
            "itl:security:DefenderInitiative",
            name,
            azure_enabled=azure_enabled,
            itl_enabled=itl_enabled,
            itl_endpoint=itl_endpoint,
            subscription_id=sub_id_str,
            resource_group=resource_group,
            provider_namespace="ITL.Security",
            opts=opts,
        )

        active_plans: List[str] = plans if plans is not None else _DEFAULT_PLANS

        assignment_id: Output[str] = Output.from_input("")

        if azure_enabled:
            if not _AZURE_NATIVE_AVAILABLE:
                raise ImportError(
                    "pulumi-azure-native is required for azure_enabled=True. "
                    "Install with: pip install pulumi-azure-native"
                )

            scope = Output.from_input(subscription_id).apply(
                lambda sid: f"/subscriptions/{sid}"
            )

            # ── MCSB policy set assignment ──────────────────────────────────
            assignment = az_authz.PolicyAssignment(
                f"{name}-mcsb",
                scope=scope,
                policy_definition_id=_MCSB_INITIATIVE_ID,
                display_name=f"ITL MCSB — {name}",
                description=(
                    f"Microsoft Cloud Security Benchmark assigned by ITL "
                    f"Pulumi component for environment '{environment}'."
                ),
                enforcement_mode=az_authz.EnforcementMode.DEFAULT,
                opts=pulumi.ResourceOptions(parent=self),
            )
            assignment_id = assignment.id

            # ── Defender pricing plans ───────────────────────────────────────
            for plan in active_plans:
                az_security.Pricing(
                    f"{name}-defender-{plan.lower()}",
                    pricing_name=plan,
                    pricing_tier=az_security.PricingTier.STANDARD,
                    opts=pulumi.ResourceOptions(parent=self),
                )

        # ── ITL ControlPlane registration ────────────────────────────────────
        self._register_with_itl(
            "Policy",
            {
                "name": name,
                "environment": environment,
                "plans": ",".join(active_plans),
                "initiative": "MCSB",
                "azure_enabled": str(azure_enabled),
            },
        )

        self.policy_assignment_id = assignment_id
        self.registered_plans = Output.from_input(active_plans)
        self.register_outputs(
            {
                "policy_assignment_id": self.policy_assignment_id,
                "registered_plans": self.registered_plans,
            }
        )
