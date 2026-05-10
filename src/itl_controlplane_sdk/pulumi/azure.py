"""
ITL Azure Stack — provision Azure resources with Pulumi.

Uses the IaC PulumiRenderer to generate a Pulumi Python program,
then runs it with the Pulumi Automation API (local program mode).

Usage::

    import asyncio
    from itl_controlplane_sdk.pulumi.azure import ITLAzureStack

    stack = ITLAzureStack(
        stack_name="itl-prod",
        project_name="itl-infrastructure",
        location="westeurope",
        resources=[
            {"name": "itl-kv",  "type": "azure/keyvault",  "properties": {}},
            {"name": "itl-aks", "type": "azure/aks",        "properties": {"agentPoolProfiles": [{"count": 3}]}},
        ],
        policies=[],                          # optional Azure policy defs
        profile_name="enterprise",            # optional tag
        pulumi_config={"resourceGroup": "itl-prod-rg"},
    )

    result = asyncio.run(stack.up())
    print(result["outputs"])
"""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import pulumi.automation as auto
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "pulumi is required for ITLAzureStack. "
        "Install with: pip install itl-controlplane-sdk[iac-azure]"
    ) from exc

from itl_controlplane_sdk.iac import (
    ComponentType,
    Platform,
    PulumiRenderer,
    RenderContext,
)


class ITLAzureStack:
    """Provision ITL Azure resources via Pulumi Automation API.

    Wraps the ``PulumiRenderer`` + Pulumi ``LocalWorkspace`` so you can
    call ``preview()`` / ``up()`` / ``destroy()`` without touching the
    Pulumi CLI directly.
    """

    def __init__(
        self,
        stack_name: str,
        project_name: str,
        location: str = "westeurope",
        resources: Optional[List[Dict[str, Any]]] = None,
        policies: Optional[List[Dict[str, Any]]] = None,
        profile_name: Optional[str] = None,
        work_dir: Optional[str] = None,
        pulumi_config: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Args:
            stack_name:    Pulumi stack name (e.g. ``"prod"``).
            project_name:  Pulumi project name (e.g. ``"itl-infrastructure"``).
            location:      Azure region (default ``"westeurope"``).
            resources:     List of ITL resource specs (type + name + properties).
            policies:      Optional list of Azure policy definitions to deploy.
            profile_name:  Optional profile tag applied to all resources.
            work_dir:      Directory for generated Pulumi program.  Defaults to
                           a temporary directory that is cleaned up automatically.
            pulumi_config: Extra Pulumi config values (e.g. ``{"resourceGroup": "my-rg"}``).
        """
        self.stack_name = stack_name
        self.project_name = project_name
        self.location = location
        self.resources = resources or []
        self.policies = policies or []
        self.profile_name = profile_name
        self.pulumi_config = pulumi_config or {}

        # Work directory management
        self._owns_work_dir = work_dir is None
        self._work_dir: Optional[Path] = Path(work_dir) if work_dir else None

        self._renderer = PulumiRenderer()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def preview(self) -> str:
        """Run ``pulumi preview`` and return the diff as a string."""
        stack = await self._get_stack()
        result = await asyncio.get_event_loop().run_in_executor(
            None, stack.preview
        )
        return result.stdout

    async def up(self, expect_no_changes: bool = False) -> Dict[str, Any]:
        """Run ``pulumi up`` and return outputs + summary.

        Returns::

            {
                "status": "ok" | "error",
                "outputs": {"vault_uri": ..., ...},
                "summary": {"resource_changes": {...}, ...},
            }
        """
        stack = await self._get_stack()
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: stack.up(on_output=print, expect_no_changes=expect_no_changes),
        )
        return {
            "status": "ok",
            "outputs": {k: v.value for k, v in result.outputs.items()},
            "summary": {
                "resource_changes": result.summary.resource_changes,
                "message": result.summary.message,
            },
        }

    async def destroy(self) -> None:
        """Run ``pulumi destroy`` — removes all provisioned resources."""
        stack = await self._get_stack()
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: stack.destroy(on_output=print)
        )

    async def outputs(self) -> Dict[str, Any]:
        """Return current stack outputs without running an update."""
        stack = await self._get_stack()
        raw = await asyncio.get_event_loop().run_in_executor(
            None, stack.outputs
        )
        return {k: v.value for k, v in raw.items()}

    def write_program(self, output_dir: str) -> List[str]:
        """Write the generated Pulumi program to *output_dir* without running it.

        Useful for code review or manual ``pulumi up`` runs.

        Returns:
            List of written file paths.
        """
        ctx = self._build_context()
        render_out = self._renderer.render(ctx)
        return render_out.write_to(output_dir)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_context(self) -> RenderContext:
        component_type = ComponentType.ALL
        if self.resources and not self.policies:
            component_type = ComponentType.RESOURCE
        elif self.policies and not self.resources:
            component_type = ComponentType.POLICY

        return RenderContext(
            platform=Platform.AZURE,
            component_type=component_type,
            resources=self.resources,
            policies=self.policies,
            profile_name=self.profile_name,
            location=self.location,
            stack_name=self.stack_name,
        )

    def _ensure_work_dir(self) -> Path:
        if self._work_dir is None:
            self._work_dir = Path(tempfile.mkdtemp(prefix="itl-pulumi-"))
        self._work_dir.mkdir(parents=True, exist_ok=True)
        # Generate (or refresh) the program files
        ctx = self._build_context()
        render_out = self._renderer.render(ctx)
        render_out.write_to(str(self._work_dir))
        return self._work_dir

    async def _get_stack(self) -> auto.Stack:
        work_dir = self._ensure_work_dir()
        stack = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: auto.create_or_select_stack(
                stack_name=self.stack_name,
                project_name=self.project_name,
                work_dir=str(work_dir),
            ),
        )
        # Apply config
        cfg: Dict[str, auto.ConfigValue] = {}
        for k, v in self.pulumi_config.items():
            cfg[k] = auto.ConfigValue(value=str(v))
        # Always set azure-native location
        cfg.setdefault(
            "azure-native:location",
            auto.ConfigValue(value=self.location),
        )
        if cfg:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: stack.set_all_config(cfg)
            )
        return stack

    def __del__(self) -> None:
        if self._owns_work_dir and self._work_dir and self._work_dir.exists():
            shutil.rmtree(self._work_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "ITLAzureStack":
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._owns_work_dir and self._work_dir and self._work_dir.exists():
            shutil.rmtree(self._work_dir, ignore_errors=True)
            self._work_dir = None
