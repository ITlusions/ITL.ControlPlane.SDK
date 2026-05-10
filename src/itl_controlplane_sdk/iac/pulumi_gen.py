"""
Pulumi renderer.

Generates ready-to-run Pulumi Python programs:
  - __main__.py      : All resource + policy definitions
  - Pulumi.yaml      : Project descriptor
  - requirements.txt : Pinned Pulumi provider packages

Supports:
  - Platform.AZURE      → pulumi_azure_native
  - Platform.KUBERNETES → pulumi_kubernetes  (Kyverno ClusterPolicies)
  - Platform.TALOS      → pulumi_kubernetes  (same provider, Talos labels)

The generated __main__.py can be run directly with `pulumi up`.
"""

from __future__ import annotations

import json
import textwrap
from typing import Any, Dict, List

from .base import (
    ComponentType,
    IaCRenderer,
    Platform,
    RenderContext,
    RenderOutput,
    RendererType,
)


class PulumiRenderer(IaCRenderer):
    """Renders policy and resource specs to a Pulumi Python program."""

    renderer_type = RendererType.PULUMI

    def render(self, ctx: RenderContext) -> RenderOutput:
        imports: List[str] = ["import pulumi"]
        resource_blocks: List[str] = []
        policy_count = 0
        resource_count = 0

        if ctx.platform == Platform.AZURE:
            imports.append("import pulumi_azure_native as azure")
            if ctx.component_type in (ComponentType.RESOURCE, ComponentType.ALL):
                blocks, count = self._azure_resources(ctx)
                resource_blocks.extend(blocks)
                resource_count = count
            if ctx.component_type in (ComponentType.POLICY, ComponentType.ALL):
                blocks, count = self._azure_policies(ctx)
                resource_blocks.extend(blocks)
                policy_count = count

        else:  # KUBERNETES / TALOS
            imports.append("import pulumi_kubernetes as k8s")
            if ctx.component_type in (ComponentType.POLICY, ComponentType.ALL):
                blocks, count = self._kyverno_policies(ctx)
                resource_blocks.extend(blocks)
                policy_count = count
            if ctx.component_type in (ComponentType.RESOURCE, ComponentType.ALL):
                blocks, count = self._kubernetes_resources(ctx)
                resource_blocks.extend(blocks)
                resource_count = count

        main_py = self._assemble_main(ctx, imports, resource_blocks)

        files: Dict[str, str] = {
            "__main__.py": main_py,
            "Pulumi.yaml": self._pulumi_yaml(ctx),
            "requirements.txt": self._requirements(ctx),
        }

        return RenderOutput(
            files=files,
            renderer_type=RendererType.PULUMI,
            platform=ctx.platform,
            policy_count=policy_count,
            resource_count=resource_count,
        )

    # ------------------------------------------------------------------
    # Azure resources
    # ------------------------------------------------------------------

    def _azure_resources(self, ctx: RenderContext) -> tuple[List[str], int]:
        blocks: List[str] = []
        tags = self._default_tags(ctx)

        _MAP = {
            "azure/keyvault": self._keyvault_py,
            "azure/aks": self._aks_py,
            "azure/nsg": self._nsg_py,
            "azure/vnet": self._vnet_py,
            "azure/storage": self._storage_py,
            "azure/identity": self._identity_py,
        }

        for spec in ctx.resources:
            res_type = spec.get("type", "").lower()
            fn = _MAP.get(res_type)
            if fn:
                blocks.append(fn(spec, ctx.location, tags))

        return blocks, len(blocks)

    def _keyvault_py(self, spec: Dict, location: str, tags: Dict) -> str:
        name = spec.get("name", "itl-keyvault")
        safe = self._py_name(name)
        props = spec.get("properties", {})
        sku = props.get("sku", {}).get("name", "standard")
        return f"""\
# KeyVault: {name}
{safe} = azure.keyvault.Vault(
    "{name}",
    vault_name="{name}",
    location="{location}",
    resource_group_name=pulumi.Config().get("resourceGroup") or "itl-rg",
    properties=azure.keyvault.VaultPropertiesArgs(
        tenant_id=azure.authorization.get_client_config().tenant_id,
        sku=azure.keyvault.SkuArgs(name=azure.keyvault.SkuName.{sku.upper()}, family="A"),
        enable_soft_delete=True,
        soft_delete_retention_in_days=90,
        enable_purge_protection=True,
        enable_rbac_authorization=True,
    ),
    tags={self._py_dict(tags)},
)
pulumi.export("{safe}_uri", {safe}.properties.vault_uri)
"""

    def _aks_py(self, spec: Dict, location: str, tags: Dict) -> str:
        name = spec.get("name", "itl-aks")
        safe = self._py_name(name)
        props = spec.get("properties", {})
        pool = props.get("agentPoolProfiles", [{}])[0]
        node_count = pool.get("count", 3)
        vm_size = pool.get("vmSize", "Standard_D4s_v3")
        return f"""\
# AKS Cluster: {name}
{safe} = azure.containerservice.ManagedCluster(
    "{name}",
    resource_name_="{name}",
    location="{location}",
    resource_group_name=pulumi.Config().get("resourceGroup") or "itl-rg",
    identity=azure.containerservice.ManagedClusterIdentityArgs(type="SystemAssigned"),
    enable_rbac=True,
    agent_pool_profiles=[
        azure.containerservice.ManagedClusterAgentPoolProfileArgs(
            name="system",
            count={node_count},
            vm_size="{vm_size}",
            mode="System",
            os_disk_size_gb=128,
        )
    ],
    network_profile=azure.containerservice.ContainerServiceNetworkProfileArgs(
        network_plugin="azure",
        network_policy="azure",
    ),
    tags={self._py_dict(tags)},
)
pulumi.export("{safe}_fqdn", {safe}.properties.fqdn)
"""

    def _nsg_py(self, spec: Dict, location: str, tags: Dict) -> str:
        name = spec.get("name", "itl-nsg")
        safe = self._py_name(name)
        return f"""\
# NSG: {name}
{safe} = azure.network.NetworkSecurityGroup(
    "{name}",
    network_security_group_name="{name}",
    location="{location}",
    resource_group_name=pulumi.Config().get("resourceGroup") or "itl-rg",
    tags={self._py_dict(tags)},
)
"""

    def _vnet_py(self, spec: Dict, location: str, tags: Dict) -> str:
        name = spec.get("name", "itl-vnet")
        safe = self._py_name(name)
        props = spec.get("properties", {})
        prefix = props.get("addressPrefix", "10.0.0.0/16")
        return f"""\
# VNet: {name}
{safe} = azure.network.VirtualNetwork(
    "{name}",
    virtual_network_name="{name}",
    location="{location}",
    resource_group_name=pulumi.Config().get("resourceGroup") or "itl-rg",
    address_space=azure.network.AddressSpaceArgs(address_prefixes=["{prefix}"]),
    tags={self._py_dict(tags)},
)
"""

    def _storage_py(self, spec: Dict, location: str, tags: Dict) -> str:
        name = spec.get("name", "itlstorage")
        safe = self._py_name(name)
        props = spec.get("properties", {})
        sku = props.get("sku", "Standard_LRS")
        return f"""\
# Storage: {name}
{safe} = azure.storage.StorageAccount(
    "{name}",
    account_name="{name}",
    location="{location}",
    resource_group_name=pulumi.Config().get("resourceGroup") or "itl-rg",
    kind="StorageV2",
    sku=azure.storage.SkuArgs(name="{sku}"),
    properties=azure.storage.StorageAccountPropertiesCreateParametersArgs(
        minimum_tls_version="TLS1_2",
        supports_https_traffic_only=True,
        allow_blob_public_access=False,
    ),
    tags={self._py_dict(tags)},
)
"""

    def _identity_py(self, spec: Dict, location: str, tags: Dict) -> str:
        name = spec.get("name", "itl-identity")
        safe = self._py_name(name)
        return f"""\
# Managed Identity: {name}
{safe} = azure.managedidentity.UserAssignedIdentity(
    "{name}",
    resource_name_="{name}",
    location="{location}",
    resource_group_name=pulumi.Config().get("resourceGroup") or "itl-rg",
    tags={self._py_dict(tags)},
)
pulumi.export("{safe}_client_id", {safe}.properties.client_id)
"""

    # ------------------------------------------------------------------
    # Azure policies (as ARM resource via pulumi_azure_native)
    # ------------------------------------------------------------------

    def _azure_policies(self, ctx: RenderContext) -> tuple[List[str], int]:
        blocks: List[str] = []
        for policy in ctx.policies:
            name = policy.get("name", "policy")
            safe = self._py_name(name)
            props = policy.get("properties", policy)
            rule_json = json.dumps(props.get("policyRule", {}))
            params_json = json.dumps(props.get("parameters", {}))
            display = props.get("displayName", name)
            desc = props.get("description", "")
            mode = props.get("mode", "All")
            block = f"""\
# Policy: {display}
{safe}_policy = azure.authorization.PolicyDefinition(
    "{name}",
    policy_definition_name="{name}",
    display_name="{display}",
    description="{desc}",
    policy_type="Custom",
    mode="{mode}",
    policy_rule={rule_json},
    parameters={params_json},
    metadata={{"managed-by": "itl-iac"{f', "profile": "{ctx.profile_name}"' if ctx.profile_name else ''}}},
)
"""
            blocks.append(block)
        return blocks, len(blocks)

    # ------------------------------------------------------------------
    # Kubernetes / Talos policies (Kyverno ClusterPolicy)
    # ------------------------------------------------------------------

    def _kyverno_policies(self, ctx: RenderContext) -> tuple[List[str], int]:
        blocks: List[str] = []
        for policy in ctx.policies:
            name = policy.get("metadata", {}).get("name", "policy")
            safe = self._py_name(name)
            manifest_repr = repr(policy)
            block = f"""\
# Kyverno ClusterPolicy: {name}
{safe}_policy = k8s.apiextensions.CustomResource(
    "{name}",
    api_version="kyverno.io/v1",
    kind="ClusterPolicy",
    metadata=k8s.meta.v1.ObjectMetaArgs(name="{name}"),
    spec={manifest_repr}.get("spec", {{}}),
)
"""
            blocks.append(block)
        return blocks, len(blocks)

    # ------------------------------------------------------------------
    # Kubernetes resources
    # ------------------------------------------------------------------

    def _kubernetes_resources(self, ctx: RenderContext) -> tuple[List[str], int]:
        blocks: List[str] = []
        for spec in ctx.resources:
            res_type = spec.get("type", "").lower()
            name = spec.get("name", "resource")
            safe = self._py_name(name)
            if res_type in ("kubernetes/namespace", "talos/namespace"):
                block = f"""\
# Namespace: {name}
{safe}_ns = k8s.core.v1.Namespace(
    "{name}",
    metadata=k8s.meta.v1.ObjectMetaArgs(name="{name}"),
)
"""
                blocks.append(block)
        return blocks, len(blocks)

    # ------------------------------------------------------------------
    # File assembly
    # ------------------------------------------------------------------

    def _assemble_main(
        self, ctx: RenderContext, imports: List[str], blocks: List[str]
    ) -> str:
        profile_comment = f" (profile: {ctx.profile_name})" if ctx.profile_name else ""
        header = f"""\
\"\"\"
ITL IaC — Pulumi Python program{profile_comment}
Platform : {ctx.platform.value}
Generated by ITL ControlPlane SDK

Run with: pulumi up
\"\"\"
"""
        imports_block = "\n".join(imports)
        body = "\n\n".join(blocks) if blocks else "# No components defined\n"
        return f"{header}\n{imports_block}\n\n\n{body}"

    def _pulumi_yaml(self, ctx: RenderContext) -> str:
        stack = ctx.stack_name
        profile_comment = f" ({ctx.profile_name})" if ctx.profile_name else ""
        return f"""\
name: {stack}
description: ITL IaC stack — {ctx.platform.value}{profile_comment}
runtime:
  name: python
  options:
    toolchain: pip
config:
  pulumi:tags:
    value:
      managed-by: itl-iac
      platform: {ctx.platform.value}
"""

    def _requirements(self, ctx: RenderContext) -> str:
        if ctx.platform == Platform.AZURE:
            return """\
pulumi>=3.0.0,<4.0.0
pulumi-azure-native>=2.0.0,<3.0.0
"""
        else:
            return """\
pulumi>=3.0.0,<4.0.0
pulumi-kubernetes>=4.0.0,<5.0.0
"""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _py_name(self, name: str) -> str:
        return name.lower().replace("-", "_").replace(" ", "_")

    def _py_dict(self, d: Dict[str, str]) -> str:
        inner = ", ".join(f'"{k}": "{v}"' for k, v in d.items())
        return "{" + inner + "}"
