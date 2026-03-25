"""raster.contour — Generate contour lines from raster data."""

from __future__ import annotations

from geopipe_agent.steps.registry import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult


@step(
    id="raster.contour",
    name="生成等值线",
    description="从栅格数据生成等值线矢量数据",
    category="raster",
    params={
        "input": {
            "type": "raster_info",
            "required": True,
            "description": "输入栅格数据",
        },
        "interval": {
            "type": "number",
            "required": True,
            "description": "等值线间距",
        },
        "band": {
            "type": "number",
            "required": False,
            "default": 1,
            "description": "波段编号（从1开始）",
        },
        "base": {
            "type": "number",
            "required": False,
            "default": 0,
            "description": "等值线基准值",
        },
    },
    outputs={
        "output": {"type": "geodataframe", "description": "等值线矢量数据"},
    },
    examples=[
        {
            "description": "每100米生成等高线",
            "params": {"input": "$dem.output", "interval": 100},
        },
    ],
)
def raster_contour(ctx: StepContext) -> StepResult:
    import numpy as np
    import geopandas as gpd
    from shapely.geometry import LineString
    import matplotlib.pyplot as plt

    raster = ctx.input("input")
    interval = ctx.param("interval")
    band = ctx.param("band", 1)
    base = ctx.param("base", 0)

    data = raster["data"][band - 1]
    transform = raster["transform"]

    # Handle NaN values for contouring
    if np.issubdtype(data.dtype, np.floating):
        plot_data = np.where(np.isnan(data), 0, data)
    else:
        plot_data = data.astype(np.float64)

    # Generate contour levels
    vmin = float(np.nanmin(data)) if np.issubdtype(data.dtype, np.floating) else float(data.min())
    vmax = float(np.nanmax(data)) if np.issubdtype(data.dtype, np.floating) else float(data.max())

    levels = np.arange(
        base + np.ceil((vmin - base) / interval) * interval,
        vmax + interval,
        interval,
    )

    if len(levels) == 0:
        # Return empty GeoDataFrame if no contours
        gdf = gpd.GeoDataFrame(
            {"elevation": [], "geometry": []},
            crs=raster.get("crs"),
        )
        return StepResult(output=gdf, stats={"contour_count": 0})

    # Create pixel coordinate arrays
    rows, cols = data.shape
    x = np.arange(cols)
    y = np.arange(rows)

    # Use matplotlib contour generator (non-interactive)
    fig, ax = plt.subplots()
    cs = ax.contour(x, y, plot_data, levels=levels)
    plt.close(fig)

    # Extract contour lines and convert to geographic coordinates
    geometries = []
    elevations = []

    for level_idx, level_value in enumerate(cs.levels):
        paths = cs.allsegs[level_idx] if level_idx < len(cs.allsegs) else []
        for path in paths:
            if len(path) >= 2:
                # Convert pixel coordinates to geographic coordinates
                coords = []
                for px, py in path:
                    geo_x = transform.c + px * transform.a + py * transform.b
                    geo_y = transform.f + px * transform.d + py * transform.e
                    coords.append((geo_x, geo_y))
                geometries.append(LineString(coords))
                elevations.append(float(level_value))

    gdf = gpd.GeoDataFrame(
        {"elevation": elevations},
        geometry=geometries,
        crs=raster.get("crs"),
    )

    stats = {
        "contour_count": len(gdf),
        "interval": interval,
        "min_elevation": float(min(elevations)) if elevations else None,
        "max_elevation": float(max(elevations)) if elevations else None,
    }

    return StepResult(output=gdf, stats=stats)
