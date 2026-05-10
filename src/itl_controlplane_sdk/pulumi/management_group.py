"""
ManagementGroup — ITL Pulumi component for Azure Management Groups.

Provisions an Azure Management Group and optionally registers it with the
ITL ControlPlane API for cross-tenant policy management.

Usage::

    import pulumi
    from itl_controlplane_sdk.pulumi.management_group import ManagementGroup

    mg = ManagementGroup(
        "itl-platform",
        display_name="ITL Platform",
        parent_id="/providers/Microsoft.Management/managementGroups/tenant-root",
        azure_enabled=True,
        itl_enabled=True,
    )

    pulumi.export("management_group_id",   mg.management_group_id)
    pulumi.export("management_group_name", mg.management_group_name)
"""

from __future__ import annotations

from typing import List, Optional

import pulumi
from pulumi import Input, Output

from .component import ITLPulumiComponent

try:
    import pulumi_azure_native.management as az_mgmt  # type: ignore[import-untyped]
    _AZURE_NATIVE_AVAILABLE = True
except ImportError:
    _AZURE_NATIVE_AVAILABLE = False


class ManagementGroup(ITLPulumiComponent):
    """Azure Management Group with optional ITL ControlPlane registration.

    Azure side
    ----------
    - ``ManagementGroup`` nested under *parent_id*.
    - Optional list of child subscription IDs to move under the group.

    ITL side
    --------
    - Registers the management group in the ITL ControlPlane API so that
      cross-tenant and Talos on-prem policies can be applied at this scope.

    Args:
        name:              Logical component name.  Used as the management
                           group ID when *group_id* is not supplied.
        display_name:      Human-readable display name shown in the Azure portal.
        group_id:          Management group ID (slug).  Defaults to *name*.
        parent_id:         Full ARM ID of the parent management group.
                           Defaults to the tenant root group when omitted.
        subscription_ids:  Azure subscription IDs to place under this
                           management group.
        azure_enabled:     Provision Azure resources (default ``True``).
        itl_enabled:       Register with ITL ControlPlane (default ``True``).
        itl_endpoint:      ITL ControlPlane API base URL.
        opts:              Pulumi resource options.

    Outputs:
        management_group_id:    ARM resource ID of the management group.
        management_group_name:  Management group ID slug.
        display_name:           Display name of the management group.
    """

    management_group_id: Output[str]
    management_group_name: Output[str]
    display_name: Output[str]

    def __init__(
        self,
        name: str,
        *,
        display_name: str,
        group_id: Optional[str] = None,
        parent_id: Optional[Input[str]] = None,
        subscription_ids: Optional[List[Input[str]]] = None,
        azure_enabled: bool = True,
        itl_enabled: bool = True,
        itl_endpoint: Optional[str] = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        super().__init__(
            "itl:management:ManagementGroup",
            name,
            azure_enabled=azure_enabled,
            itl_enabled=itl_enabled,
            itl_endpoint=itl_endpoint,
            # ManagementGroups are tenant-scoped; no subscription context needed
            opts=opts,
        )

        effective_group_id = group_id or name

        mg_id: Output[str] = Output.from_input("")
        mg_name: Output[str] = Output.from_input(effective_group_id)

        if azure_enabled:
            if not _AZURE_NATIVE_AVAILABLE:
                raise ImportError(
                    "pulumi-azure-native is required for azure_enabled=True. "
                    "Install with: pip install pulumi-azure-native"
                )

            child_opts = pulumi.ResourceOptions(parent=self)

            # ── Management group ─────────────────────────────────────────────
            mg_details = az_mgmt.ManagementGroupArgs(
                display_name=display_name,
                **(
                    {
                        "details": az_mgmt.CreateManagementGroupDetailsArgs(
                            parent=az_mgmt.CreateParentGroupInfoArgs(
                                id=parent_id,
                            )
                        )
                    }
                    if parent_id is not None
                    else {}
                ),
            )

            mg = az_mgmt.ManagementGroup(
                name,
                group_id=effective_group_id,
                display_name=display_name,
                **(
                    {
                        "details": az_mgmt.CreateManagementGroupDetailsArgs(
                            parent=az_mgmt.CreateParentGroupInfoArgs(
                                id=parent_id,
                            )
                        )
                    }
                    if parent_id is not None
                    else {}
                ),
                opts=child_opts,
            )
            mg_id = mg.id
            mg_name = mg.name

            # ── Subscriptions ────────────────────────────────────────────────
            for sub_id in subscription_ids or []:
                sub_id_val = sub_id if isinstance(sub_id, str) else "__output__"
                az_mgmt.ManagementGroupSubscription(
                    f"{name}-sub-{sub_id_val}",
                    group_id=mg.name,
                    subscription_id=sub_id,
                    opts=pulumi.ResourceOptions(parent=mg),
                )

        # ── ITL ControlPlane registration ─────────────────────────────────────
        self._register_with_itl(
            "ManagementGroup",
            {
                "name": effective_group_id,
                "display_name": display_name,
                "subscription_count": str(len(subscription_ids or [])),
            },
        )

        self.management_group_id = mg_id
        self.management_group_name = mg_name
        self.display_name = Output.from_input(display_name)

        self.register_outputs(
            {
                "management_group_id": self.management_group_id,
                "management_group_name": self.management_group_name,
                "display_name": self.display_name,
            }
        )
