"""vector.clip — Clip vector data."""

from __future__ import annotations

from geopipe_agent.steps.registry import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult


@step(
    id="vector.clip",
    name="矢量裁剪",
    description="用裁剪范围裁剪输入矢量数据",
    category="vector",
    params={
        "input": {
            "type": "geodataframe",
            "required": True,
            "description": "输入矢量数据",
        },
        "clip_geometry": {
            "type": "geodataframe",
            "required": True,
            "description": "裁剪范围（矢量数据）",
        },
    },
    outputs={
        "output": {"type": "geodataframe", "description": "裁剪结果"},
    },
    backends=["geopandas", "qgis_process"],
    examples=[
        {
            "description": "裁剪道路数据到研究区范围",
            "params": {
                "input": "$roads.output",
                "clip_geometry": "$boundary.output",
            },
        },
    ],
)
def vector_clip(ctx: StepContext) -> StepResult:
    gdf = ctx.input("input")
    clip_gdf = ctx.param("clip_geometry")

    result_gdf = ctx.backend.clip(gdf, clip_gdf)

    stats = {
        "feature_count": len(result_gdf),
    }

    return StepResult(output=result_gdf, stats=stats)
