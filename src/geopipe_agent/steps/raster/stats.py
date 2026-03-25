"""raster.stats — Compute raster statistics."""

from __future__ import annotations

from geopipe_agent.steps.registry import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult


@step(
    id="raster.stats",
    name="栅格统计",
    description="计算栅格数据的统计信息（最小值、最大值、均值、标准差）",
    category="raster",
    params={
        "input": {
            "type": "raster_info",
            "required": True,
            "description": "输入栅格数据",
        },
        "band": {
            "type": "number",
            "required": False,
            "default": 1,
            "description": "波段编号（从1开始）",
        },
    },
    outputs={
        "output": {"type": "dict", "description": "统计结果"},
    },
    examples=[
        {
            "description": "计算DEM第一波段统计",
            "params": {"input": "$dem.output", "band": 1},
        },
    ],
)
def raster_stats(ctx: StepContext) -> StepResult:
    import numpy as np

    raster = ctx.input("input")
    band = ctx.param("band", 1)
    data = raster["data"][band - 1]

    # Handle nodata / NaN
    if np.issubdtype(data.dtype, np.floating):
        valid = data[~np.isnan(data)]
    else:
        valid = data.ravel()

    stats = {
        "min": float(valid.min()),
        "max": float(valid.max()),
        "mean": float(valid.mean()),
        "std": float(valid.std()),
        "band": band,
        "pixel_count": int(valid.size),
    }

    return StepResult(output=stats, stats=stats)
