"""vector.buffer — Buffer analysis."""

from __future__ import annotations

from geopipe_agent.steps.registry import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult
from geopipe_agent.steps.vector._delegate import run_backend_op


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
    backends=["geopandas", "qgis_process"],
    examples=[
        {
            "description": "500米道路缓冲区",
            "params": {"input": "$roads.output", "distance": 500},
        },
    ],
)
def vector_buffer(ctx: StepContext) -> StepResult:
    return run_backend_op(
        ctx, "buffer",
        positional_params=["distance"],
        keyword_params={"cap_style": "cap_style"},
        extra_stats=lambda ctx, gdf, result: {
            "total_area": float(result.geometry.area.sum()),
        },
    )
