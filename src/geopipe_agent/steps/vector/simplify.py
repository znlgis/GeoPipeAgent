"""vector.simplify — Simplify vector geometries."""

from __future__ import annotations

from geopipe_agent.steps.registry import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult


@step(
    id="vector.simplify",
    name="矢量简化",
    description="简化矢量几何（减少顶点数量）",
    category="vector",
    params={
        "input": {
            "type": "geodataframe",
            "required": True,
            "description": "输入矢量数据",
        },
        "tolerance": {
            "type": "number",
            "required": True,
            "description": "简化容差（单位取决于 CRS）",
        },
        "preserve_topology": {
            "type": "boolean",
            "required": False,
            "default": True,
            "description": "是否保持拓扑",
        },
    },
    outputs={
        "output": {"type": "geodataframe", "description": "简化后的矢量数据"},
    },
    backends=["geopandas"],
    examples=[
        {
            "description": "简化道路数据（容差100米）",
            "params": {"input": "$roads.output", "tolerance": 100},
        },
    ],
)
def vector_simplify(ctx: StepContext) -> StepResult:
    gdf = ctx.input("input")
    tolerance = ctx.param("tolerance")
    preserve_topology = ctx.param("preserve_topology", True)

    result_gdf = ctx.backend.simplify(
        gdf, tolerance, preserve_topology=preserve_topology
    )

    stats = {
        "feature_count": len(result_gdf),
    }

    return StepResult(output=result_gdf, stats=stats)
