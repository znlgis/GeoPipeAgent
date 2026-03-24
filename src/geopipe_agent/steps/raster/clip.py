"""raster.clip — Clip raster data by geometry."""

from __future__ import annotations

from geopipe_agent.steps.decorators import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult


@step(
    id="raster.clip",
    name="栅格裁剪",
    description="使用矢量几何或边界框裁剪栅格数据",
    category="raster",
    params={
        "input": {
            "type": "raster_info",
            "required": True,
            "description": "输入栅格数据",
        },
        "mask": {
            "type": "geodataframe",
            "required": True,
            "description": "裁剪掩膜（矢量数据）",
        },
        "crop": {
            "type": "boolean",
            "required": False,
            "default": True,
            "description": "是否裁剪到掩膜范围",
        },
        "nodata": {
            "type": "number",
            "required": False,
            "default": 0,
            "description": "无数据填充值",
        },
    },
    outputs={
        "output": {"type": "raster_info", "description": "裁剪后的栅格数据"},
    },
    examples=[
        {
            "description": "用矢量边界裁剪栅格",
            "params": {"input": "$dem.output", "mask": "$boundary.output"},
        },
    ],
)
def raster_clip(ctx: StepContext) -> StepResult:
    import numpy as np
    import rasterio
    from rasterio.mask import mask as rasterio_mask
    from rasterio.transform import from_bounds
    import tempfile
    import os

    raster = ctx.input("input")
    mask_gdf = ctx.param("mask")
    crop = ctx.param("crop", True)
    nodata = ctx.param("nodata", 0)

    # Write raster to a temporary file for rasterio.mask
    profile = raster["profile"].copy()
    data = raster["data"]

    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        with rasterio.open(tmp_path, "w", **profile) as dst:
            dst.write(data)

        # Get mask geometries
        geometries = mask_gdf.geometry.values

        with rasterio.open(tmp_path) as src:
            out_image, out_transform = rasterio_mask(
                src, geometries, crop=crop, nodata=nodata
            )
            out_profile = src.profile.copy()
    finally:
        os.unlink(tmp_path)

    out_profile.update({
        "height": out_image.shape[1],
        "width": out_image.shape[2],
        "transform": out_transform,
        "nodata": nodata,
    })

    result = {
        "data": out_image,
        "transform": out_transform,
        "crs": raster["crs"],
        "profile": out_profile,
    }

    stats = {
        "width": out_image.shape[2],
        "height": out_image.shape[1],
        "band_count": out_image.shape[0],
    }

    return StepResult(output=result, stats=stats)
