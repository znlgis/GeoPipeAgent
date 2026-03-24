"""io.read_raster — Read raster data from file."""

from __future__ import annotations

from geopipe_agent.steps.decorators import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult


@step(
    id="io.read_raster",
    name="读取栅格数据",
    description="从文件读取栅格数据（GeoTIFF 等），返回 rasterio DatasetReader 信息",
    category="io",
    params={
        "path": {
            "type": "string",
            "required": True,
            "description": "栅格数据文件路径",
        },
    },
    outputs={
        "output": {"type": "raster_info", "description": "栅格数据信息字典"},
    },
    examples=[
        {
            "description": "读取 GeoTIFF",
            "params": {"path": "data/dem.tif"},
        },
    ],
)
def io_read_raster(ctx: StepContext) -> StepResult:
    import rasterio

    path = ctx.param("path")

    with rasterio.open(path) as src:
        data = src.read()
        stats = {
            "width": src.width,
            "height": src.height,
            "crs": str(src.crs) if src.crs else None,
            "band_count": src.count,
            "dtype": str(src.dtypes[0]),
            "bounds": list(src.bounds),
        }
        result = {
            "data": data,
            "transform": src.transform,
            "crs": src.crs,
            "profile": dict(src.profile),
            "path": path,
        }

    return StepResult(output=result, stats=stats)
