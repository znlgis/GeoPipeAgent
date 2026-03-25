"""vector.overlay — Overlay analysis between two vector layers."""

from __future__ import annotations

from geopipe_agent.steps.registry import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult


@step(
    id="vector.overlay",
    name="矢量叠加分析",
    description="对两个矢量图层进行叠加分析（交集、并集、差集等）",
    category="vector",
    params={
        "input": {
            "type": "geodataframe",
            "required": True,
            "description": "输入矢量数据",
        },
        "overlay_layer": {
            "type": "geodataframe",
            "required": True,
            "description": "叠加图层",
        },
        "how": {
            "type": "string",
            "required": False,
            "default": "intersection",
            "enum": ["intersection", "union", "difference", "symmetric_difference", "identity"],
            "description": "叠加方式",
        },
    },
    outputs={
        "output": {"type": "geodataframe", "description": "叠加分析结果"},
    },
    backends=["gdal_python"],
    examples=[
        {
            "description": "两个图层求交集",
            "params": {
                "input": "$layer1.output",
                "overlay_layer": "$layer2.output",
                "how": "intersection",
            },
        },
    ],
)
def vector_overlay(ctx: StepContext) -> StepResult:
    gdf = ctx.input("input")
    overlay_gdf = ctx.param("overlay_layer")
    how = ctx.param("how", "intersection")

    result_gdf = ctx.backend.overlay(gdf, overlay_gdf, how=how)

    stats = {
        "feature_count": len(result_gdf),
        "overlay_method": how,
    }

    return StepResult(output=result_gdf, stats=stats)
