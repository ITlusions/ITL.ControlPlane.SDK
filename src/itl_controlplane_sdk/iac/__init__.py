"""
ITL ControlPlane SDK — IaC renderers.

Usage::

    from itl_controlplane_sdk.iac import get_renderer, RenderContext, Platform, ComponentType

    renderer = get_renderer("bicep")
    output = renderer.render(
        RenderContext(
            platform=Platform.AZURE,
            component_type=ComponentType.ALL,
            policies=[...],
            resources=[...],
            location="westeurope",
            stack_name="my-stack",
        )
    )
    written = output.write_to("./output")

Available renderer types: ``arm``, ``bicep``, ``terraform``, ``pulumi``
"""

from .arm import ARMRenderer
from .base import (
    ComponentType,
    IaCRenderer,
    Platform,
    RenderContext,
    RenderOutput,
    RendererType,
)
from .bicep import BicepRenderer
from .pulumi_gen import PulumiRenderer
from .terraform import TerraformRenderer

__all__ = [
    # Factory
    "get_renderer",
    # ABC / types
    "IaCRenderer",
    "RenderContext",
    "RenderOutput",
    "RendererType",
    "Platform",
    "ComponentType",
    # Concrete renderers
    "ARMRenderer",
    "BicepRenderer",
    "TerraformRenderer",
    "PulumiRenderer",
]

_RENDERER_MAP: dict[RendererType, type[IaCRenderer]] = {
    RendererType.ARM: ARMRenderer,
    RendererType.BICEP: BicepRenderer,
    RendererType.TERRAFORM: TerraformRenderer,
    RendererType.PULUMI: PulumiRenderer,
}


def get_renderer(renderer_type: str) -> IaCRenderer:
    """Return an initialised renderer for the given type string.

    Args:
        renderer_type: One of ``"arm"``, ``"bicep"``, ``"terraform"``,
            ``"pulumi"`` (case-insensitive).

    Returns:
        An ``IaCRenderer`` instance ready to call ``.render(ctx)``.

    Raises:
        ValueError: Unknown renderer type.
    """
    try:
        rt = RendererType(renderer_type.lower())
    except ValueError:
        valid = ", ".join(r.value for r in RendererType)
        raise ValueError(
            f"Unknown renderer type: '{renderer_type}'. Valid options: {valid}"
        )

    return _RENDERER_MAP[rt]()
