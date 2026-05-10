"""
ARM (Azure Resource Manager) renderer.

Outputs:
  - azuredeploy.json        : ARM deployment template containing all resources
  - policies/<name>.json    : One ARM policy definition file per policy
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from .base import (
    ComponentType,
    IaCRenderer,
    Platform,
    RenderContext,
    RenderOutput,
    RendererType,
)

_ARM_SCHEMA = "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#"
_POLICY_API = "2021-06-01"
_POLICY_RG_API = "2021-06-01"


class ARMRenderer(IaCRenderer):
    """Renders policy and resource specs to ARM JSON templates."""

    renderer_type = RendererType.ARM

    def render(self, ctx: RenderContext) -> RenderOutput:
        files: Dict[str, str] = {}
        policy_count = 0
        resource_count = 0

        if ctx.component_type in (ComponentType.POLICY, ComponentType.ALL):
            if ctx.platform == Platform.AZURE:
                policy_resources, count = self._render_azure_policies(ctx)
                files.update(policy_resources)
                policy_count = count
            # Kyverno/Kubernetes policies are not ARM — skip with comment file
            elif ctx.platform in (Platform.KUBERNETES, Platform.TALOS):
                files["note.txt"] = (
                    "# ARM renderer does not support Kubernetes/Talos policies.\n"
                    "# Use the Terraform or Pulumi renderer for Kyverno ClusterPolicies.\n"
                )

        if ctx.component_type in (ComponentType.RESOURCE, ComponentType.ALL):
            if ctx.platform == Platform.AZURE:
                resource_template, count = self._render_resource_template(ctx)
                files["azuredeploy.json"] = resource_template
                resource_count = count

        return RenderOutput(
            files=files,
            renderer_type=RendererType.ARM,
            platform=ctx.platform,
            policy_count=policy_count,
            resource_count=resource_count,
        )

    # ------------------------------------------------------------------
    # Azure policies
    # ------------------------------------------------------------------

    def _render_azure_policies(self, ctx: RenderContext) -> tuple[Dict[str, str], int]:
        files: Dict[str, str] = {}
        for policy in ctx.policies:
            name = policy.get("name") or policy.get("displayName", "policy")
            safe = self._safe_name(name)
            arm_def = self._policy_to_arm_resource(policy, ctx)
            wrapper = {
                "$schema": _ARM_SCHEMA,
                "contentVersion": "1.0.0.0",
                "resources": [arm_def],
            }
            files[f"policies/{safe}.json"] = json.dumps(wrapper, indent=2)
        return files, len(ctx.policies)

    def _policy_to_arm_resource(
        self, policy: Dict[str, Any], ctx: RenderContext
    ) -> Dict[str, Any]:
        name = policy.get("name", "policy")
        props = policy.get("properties", policy)
        return {
            "type": "Microsoft.Authorization/policyDefinitions",
            "apiVersion": _POLICY_API,
            "name": name,
            "properties": {
                "displayName": props.get("displayName", name),
                "description": props.get("description", ""),
                "policyType": props.get("policyType", "Custom"),
                "mode": props.get("mode", "All"),
                "metadata": {
                    **props.get("metadata", {}),
                    "managedBy": "itl-iac",
                    **({"profile": ctx.profile_name} if ctx.profile_name else {}),
                },
                "parameters": props.get("parameters", {}),
                "policyRule": props.get("policyRule", {}),
            },
        }

    # ------------------------------------------------------------------
    # Azure resources
    # ------------------------------------------------------------------

    def _render_resource_template(
        self, ctx: RenderContext
    ) -> tuple[str, int]:
        resources: List[Dict[str, Any]] = []
        tags = self._default_tags(ctx)

        for spec in ctx.resources:
            res_type = spec.get("type", "")
            arm_res = self._resource_spec_to_arm(spec, ctx.location, tags)
            if arm_res:
                resources.append(arm_res)

        template = {
            "$schema": _ARM_SCHEMA,
            "contentVersion": "1.0.0.0",
            "parameters": {
                "location": {
                    "type": "string",
                    "defaultValue": ctx.location,
                    "metadata": {"description": "Azure region for all resources"},
                }
            },
            "resources": resources,
        }
        return json.dumps(template, indent=2), len(resources)

    def _resource_spec_to_arm(
        self,
        spec: Dict[str, Any],
        location: str,
        tags: Dict[str, str],
    ) -> Dict[str, Any] | None:
        res_type = spec.get("type", "").lower()
        name = spec.get("name", "resource")
        props = spec.get("properties", {})

        _TYPE_MAP: Dict[str, str] = {
            "azure/keyvault": "Microsoft.KeyVault/vaults",
            "azure/aks": "Microsoft.ContainerService/managedClusters",
            "azure/nsg": "Microsoft.Network/networkSecurityGroups",
            "azure/vnet": "Microsoft.Network/virtualNetworks",
            "azure/storage": "Microsoft.Storage/storageAccounts",
            "azure/identity": "Microsoft.ManagedIdentity/userAssignedIdentities",
        }

        arm_type = _TYPE_MAP.get(res_type)
        if not arm_type:
            return None  # unsupported type — skip silently

        return {
            "type": arm_type,
            "apiVersion": props.get("apiVersion", "2023-01-01"),
            "name": name,
            "location": location,
            "tags": {**tags, **spec.get("tags", {})},
            "properties": {
                k: v for k, v in props.items() if k != "apiVersion"
            },
        }
