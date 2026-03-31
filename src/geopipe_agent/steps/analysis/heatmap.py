"""analysis.heatmap — Generate heatmap (kernel density estimation) from point data."""

from __future__ import annotations

from geopipe_agent.steps.registry import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult


@step(
    id="analysis.heatmap",
    name="热力图",
    description="基于核密度估计（KDE）生成热力图栅格",
    category="analysis",
    params={
        "input": {
            "type": "geodataframe",
            "required": True,
            "description": "输入点矢量数据",
        },
        "resolution": {
            "type": "number",
            "required": False,
            "default": 100,
            "description": "输出栅格分辨率（像素数，宽度方向）",
        },
        "bandwidth": {
            "type": "number",
            "required": False,
            "description": "核函数带宽。不指定则自动估计",
        },
    },
    outputs={
        "output": {"type": "raster_info", "description": "热力图栅格数据"},
    },
    examples=[
        {
            "description": "生成犯罪热力图",
            "params": {"input": "$crimes.output", "resolution": 200},
        },
    ],
)
def analysis_heatmap(ctx: StepContext) -> StepResult:
    import numpy as np
    from scipy.ndimage import gaussian_filter
    from rasterio.transform import from_bounds

    from geopipe_agent.steps.analysis._grid import normalize_bounds, compute_grid_dims

    gdf = ctx.input("input")
    resolution = ctx.param("resolution", 100)
    bandwidth = ctx.param("bandwidth")

    # Extract point coordinates
    coords = np.array([(g.x, g.y) for g in gdf.geometry])

    minx, miny, maxx, maxy, dx, dy = normalize_bounds(gdf.total_bounds)

    # Compute grid dimensions
    width, height = compute_grid_dims(resolution, dx, dy)

    # Build 2D histogram
    heatmap, _, _ = np.histogram2d(
        coords[:, 1], coords[:, 0],
        bins=[height, width],
        range=[[miny, maxy], [minx, maxx]],
    )

    # Apply Gaussian smoothing
    if bandwidth is None:
        sigma = max(1.0, min(width, height) / 20.0)
    else:
        pixel_size = dx / width
        sigma = bandwidth / pixel_size

    heatmap = gaussian_filter(heatmap.astype(np.float64), sigma=sigma)

    # Flip vertically because raster origin is top-left
    heatmap = heatmap[::-1]

    # Build raster info
    transform = from_bounds(minx, miny, maxx, maxy, width, height)
    crs = gdf.crs

    result_data = heatmap[np.newaxis, :, :]  # Single band

    profile = {
        "driver": "GTiff",
        "dtype": "float64",
        "width": width,
        "height": height,
        "count": 1,
        "crs": crs,
        "transform": transform,
    }

    result = {
        "data": result_data,
        "transform": transform,
        "crs": crs,
        "profile": profile,
    }

    stats = {
        "point_count": len(gdf),
        "width": width,
        "height": height,
        "max_density": float(heatmap.max()),
    }

    return StepResult(output=result, stats=stats)
