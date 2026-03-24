"""vector.buffer — Buffer analysis."""

from __future__ import annotations

from geopipe_agent.steps.decorators import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult


@step(
    id="vector.buffer",
    name="矢量缓冲区分析",
    description="对输入的矢量数据生成指定距离的缓冲区",
    category="vector",
    params={
        "input": {
            "type": "geodataframe",
            "required": True,
            "description": "输入矢量数据",
        },
        "distance": {
            "type": "number",
            "required": True,
            "description": "缓冲区距离（单位取决于 CRS）",
        },
        "cap_style": {
            "type": "string",
            "required": False,
            "default": "round",
            "enum": ["round", "flat", "square"],
            "description": "端点样式",
        },
    },
    outputs={
        "output": {"type": "geodataframe", "description": "缓冲区结果"},
        "stats": {"type": "dict", "description": "统计信息"},
    },
    backends=["gdal_python", "qgis_process"],
    examples=[
        {
            "description": "500米道路缓冲区",
            "params": {"input": "$roads.output", "distance": 500},
        },
    ],
)
def vector_buffer(ctx: StepContext) -> StepResult:
    gdf = ctx.input("input")
    distance = ctx.param("distance")
    cap_style = ctx.param("cap_style", "round")

    result_gdf = ctx.backend.buffer(gdf, distance, cap_style=cap_style)

    stats = {
        "feature_count": len(result_gdf),
        "total_area": float(result_gdf.geometry.area.sum()),
    }

    return StepResult(output=result_gdf, stats=stats)
