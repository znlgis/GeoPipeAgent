"""vector.dissolve — Dissolve vector features."""

from __future__ import annotations

from geopipe_agent.steps.decorators import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult


@step(
    id="vector.dissolve",
    name="矢量融合",
    description="将矢量要素按指定字段融合（合并几何）",
    category="vector",
    params={
        "input": {
            "type": "geodataframe",
            "required": True,
            "description": "输入矢量数据",
        },
        "by": {
            "type": "string",
            "required": False,
            "description": "分组字段名。不指定则全部融合",
        },
        "aggfunc": {
            "type": "string",
            "required": False,
            "default": "first",
            "description": "属性聚合函数 (first, sum, mean, count 等)",
        },
    },
    outputs={
        "output": {"type": "geodataframe", "description": "融合结果"},
    },
    backends=["gdal_python"],
    examples=[
        {
            "description": "按类型字段融合",
            "params": {"input": "$data.output", "by": "type"},
        },
    ],
)
def vector_dissolve(ctx: StepContext) -> StepResult:
    gdf = ctx.input("input")
    by = ctx.param("by")
    aggfunc = ctx.param("aggfunc", "first")

    result_gdf = ctx.backend.dissolve(gdf, by=by, aggfunc=aggfunc)

    stats = {
        "feature_count": len(result_gdf),
    }

    return StepResult(output=result_gdf, stats=stats)
