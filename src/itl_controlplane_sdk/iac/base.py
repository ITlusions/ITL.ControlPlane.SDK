"""
Base abstractions for IaC renderers.

All renderers share:
- RenderContext  : what to render (policies, resources, platform, profile)
- RenderOutput   : what comes out  (filename → content dict)
- IaCRenderer    : ABC every renderer must implement
- RendererType   : supported renderer identifiers
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RendererType(str, Enum):
    """Supported IaC renderer types."""
    ARM = "arm"
    BICEP = "bicep"
    TERRAFORM = "terraform"
    PULUMI = "pulumi"


class Platform(str, Enum):
    """Target deployment platforms."""
    AZURE = "azure"
    KUBERNETES = "kubernetes"
    TALOS = "talos"


class ComponentType(str, Enum):
    """What kind of IaC component to render."""
    POLICY = "policy"
    RESOURCE = "resource"
    ALL = "all"


@dataclass
class RenderContext:
    """
    All inputs needed by any renderer.

    Attributes:
        platform:        Target platform (azure, kubernetes, talos).
        component_type:  Render policies, resources, or both.
        policies:        List of raw policy spec dicts
                         (ARM PolicyDefinition or Kyverno ClusterPolicy).
        resources:       List of raw resource spec dicts
                         (type, name, properties, tags).
        profile_name:    Optional profile label used in generated comments.
        location:        Azure location for resource deployments.
        tags:            Default tags applied to every resource.
        stack_name:      Pulumi / Terraform state stack name.
        namespace:       Kubernetes namespace (Kubernetes/Talos renderers).
    """
    platform: Platform
    component_type: ComponentType = ComponentType.ALL

    policies: List[Dict[str, Any]] = field(default_factory=list)
    resources: List[Dict[str, Any]] = field(default_factory=list)

    profile_name: Optional[str] = None
    location: str = "westeurope"
    tags: Dict[str, str] = field(default_factory=dict)
    stack_name: str = "itl-stack"
    namespace: str = "default"


@dataclass
class RenderOutput:
    """
    The rendered IaC artifacts.

    Attributes:
        files:          Mapping of relative filename → file content.
                        Write these to disk or stream to stdout.
        renderer_type:  Which renderer produced this output.
        platform:       Target platform.
        policy_count:   Number of policies rendered.
        resource_count: Number of resources rendered.
    """
    files: Dict[str, str]
    renderer_type: RendererType
    platform: Platform
    policy_count: int = 0
    resource_count: int = 0

    def write_to(self, output_dir: str) -> List[str]:
        """
        Write all files to *output_dir*.

        Returns:
            List of absolute paths written.
        """
        import os
        written: List[str] = []
        for filename, content in self.files.items():
            path = os.path.join(output_dir, filename)
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
            written.append(path)
        return written

    def to_stdout(self) -> str:
        """Return all file contents concatenated with file-header separators."""
        parts: List[str] = []
        for filename, content in self.files.items():
            parts.append(f"# === {filename} ===\n{content}")
        return "\n\n".join(parts)


class IaCRenderer(ABC):
    """
    Abstract base class for all IaC renderers.

    Subclasses implement :meth:`render` and declare their
    :attr:`renderer_type`.  The base class provides shared helpers.
    """

    renderer_type: RendererType

    @abstractmethod
    def render(self, ctx: RenderContext) -> RenderOutput:
        """
        Render *ctx* into IaC artifacts.

        Args:
            ctx: All inputs needed for rendering.

        Returns:
            RenderOutput with one or more files.
        """

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _safe_name(self, name: str) -> str:
        """Normalise a name to be safe in most IaC identifiers."""
        return name.lower().replace(" ", "-").replace("_", "-")

    def _default_tags(self, ctx: RenderContext) -> Dict[str, str]:
        base: Dict[str, str] = {
            "managed-by": "itl-iac",
            "platform": ctx.platform.value,
        }
        if ctx.profile_name:
            base["profile"] = ctx.profile_name
        base.update(ctx.tags)
        return base
