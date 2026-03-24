"""io.write_raster — Write raster data to file."""

from __future__ import annotations

from pathlib import Path

from geopipe_agent.steps.decorators import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult


@step(
    id="io.write_raster",
    name="写入栅格数据",
    description="将栅格数据写入文件（GeoTIFF 等）",
    category="io",
    params={
        "input": {
            "type": "raster_info",
            "required": True,
            "description": "输入栅格数据（包含 data, profile 的字典）",
        },
        "path": {
            "type": "string",
            "required": True,
            "description": "输出文件路径",
        },
    },
    outputs={
        "output": {"type": "string", "description": "输出文件路径"},
    },
    examples=[
        {
            "description": "写入 GeoTIFF",
            "params": {"input": "$raster.output", "path": "output/result.tif"},
        },
    ],
)
def io_write_raster(ctx: StepContext) -> StepResult:
    import rasterio

    raster_info = ctx.input("input")
    path = ctx.param("path")

    # Ensure output directory exists
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    profile = raster_info["profile"].copy()
    data = raster_info["data"]

    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data)

    stats = {
        "output_path": str(path),
        "width": profile.get("width"),
        "height": profile.get("height"),
    }

    return StepResult(output=str(path), stats=stats)
