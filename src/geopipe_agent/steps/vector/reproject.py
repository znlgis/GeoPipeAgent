"""vector.reproject — Reproject vector data."""

from __future__ import annotations

from geopipe_agent.steps.registry import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult
from geopipe_agent.steps.vector._delegate import run_backend_op


@step(
    id="vector.reproject",
    name="矢量投影转换",
    description="将矢量数据从当前坐标参考系转换到目标坐标参考系",
    category="vector",
    params={
        "input": {
            "type": "geodataframe",
            "required": True,
            "description": "输入矢量数据",
        },
        "target_crs": {
            "type": "string",
            "required": True,
            "description": "目标坐标参考系（如 EPSG:4326, EPSG:3857）",
        },
    },
    outputs={
        "output": {"type": "geodataframe", "description": "转换后的矢量数据"},
    },
    backends=["native_python", "qgis_process"],
    examples=[
        {
            "description": "转换到 Web Mercator",
            "params": {"input": "$roads.output", "target_crs": "EPSG:3857"},
        },
    ],
)
def vector_reproject(ctx: StepContext) -> StepResult:
    return run_backend_op(
        ctx, "reproject",
        positional_params=["target_crs"],
        extra_stats=lambda ctx, gdf, result: {
            "source_crs": str(gdf.crs) if gdf.crs else None,
            "target_crs": ctx.param("target_crs"),
        },
    )
