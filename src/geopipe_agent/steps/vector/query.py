"""vector.query — Query/filter vector features."""

from __future__ import annotations

from geopipe_agent.steps.registry import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult


@step(
    id="vector.query",
    name="矢量查询",
    description="按属性表达式查询/过滤矢量要素",
    category="vector",
    params={
        "input": {
            "type": "geodataframe",
            "required": True,
            "description": "输入矢量数据",
        },
        "expression": {
            "type": "string",
            "required": True,
            "description": "Pandas query 表达式（如 'population > 1000'）",
        },
    },
    outputs={
        "output": {"type": "geodataframe", "description": "查询结果"},
    },
    examples=[
        {
            "description": "筛选人口大于1000的要素",
            "params": {"input": "$data.output", "expression": "population > 1000"},
        },
    ],
)
def vector_query(ctx: StepContext) -> StepResult:
    gdf = ctx.input("input")
    expression = ctx.param("expression")

    result_gdf = gdf.query(expression).copy()

    stats = {
        "input_count": len(gdf),
        "output_count": len(result_gdf),
        "expression": expression,
    }

    return StepResult(output=result_gdf, stats=stats)
