"""raster.reproject — Reproject raster data to a different CRS."""

from __future__ import annotations

from geopipe_agent.steps.decorators import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult


@step(
    id="raster.reproject",
    name="栅格投影转换",
    description="将栅格数据从当前坐标参考系转换到目标坐标参考系",
    category="raster",
    params={
        "input": {
            "type": "raster_info",
            "required": True,
            "description": "输入栅格数据",
        },
        "target_crs": {
            "type": "string",
            "required": True,
            "description": "目标坐标参考系（如 EPSG:4326, EPSG:3857）",
        },
        "resampling": {
            "type": "string",
            "required": False,
            "default": "nearest",
            "enum": ["nearest", "bilinear", "cubic", "lanczos"],
            "description": "重采样方法",
        },
    },
    outputs={
        "output": {"type": "raster_info", "description": "转换后的栅格数据"},
    },
    examples=[
        {
            "description": "转换到 Web Mercator",
            "params": {"input": "$dem.output", "target_crs": "EPSG:3857"},
        },
    ],
)
def raster_reproject(ctx: StepContext) -> StepResult:
    import numpy as np
    from rasterio.crs import CRS
    from rasterio.warp import calculate_default_transform, reproject, Resampling

    raster = ctx.input("input")
    target_crs = ctx.param("target_crs")
    resampling_name = ctx.param("resampling", "nearest")

    resampling_map = {
        "nearest": Resampling.nearest,
        "bilinear": Resampling.bilinear,
        "cubic": Resampling.cubic,
        "lanczos": Resampling.lanczos,
    }
    resampling_method = resampling_map.get(resampling_name, Resampling.nearest)

    src_data = raster["data"]
    src_crs = raster["crs"]
    src_transform = raster["transform"]
    profile = raster["profile"].copy()

    dst_crs = CRS.from_user_input(target_crs)
    band_count, src_height, src_width = src_data.shape

    transform, width, height = calculate_default_transform(
        src_crs, dst_crs, src_width, src_height,
        left=src_transform.c,
        bottom=src_transform.f + src_transform.e * src_height,
        right=src_transform.c + src_transform.a * src_width,
        top=src_transform.f,
    )

    dst_data = np.zeros((band_count, height, width), dtype=src_data.dtype)

    for i in range(band_count):
        reproject(
            source=src_data[i],
            destination=dst_data[i],
            src_transform=src_transform,
            src_crs=src_crs,
            dst_transform=transform,
            dst_crs=dst_crs,
            resampling=resampling_method,
        )

    profile.update({
        "crs": dst_crs,
        "transform": transform,
        "width": width,
        "height": height,
    })

    result = {
        "data": dst_data,
        "transform": transform,
        "crs": dst_crs,
        "profile": profile,
    }

    stats = {
        "source_crs": str(src_crs),
        "target_crs": target_crs,
        "width": width,
        "height": height,
    }

    return StepResult(output=result, stats=stats)
