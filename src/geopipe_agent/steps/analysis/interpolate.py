"""analysis.interpolate — Spatial interpolation from point data."""

from __future__ import annotations

from geopipe_agent.steps.decorators import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult


@step(
    id="analysis.interpolate",
    name="空间插值",
    description="将点数据插值为连续栅格表面（IDW 或 线性/最近邻/三次插值）",
    category="analysis",
    params={
        "input": {
            "type": "geodataframe",
            "required": True,
            "description": "输入点矢量数据",
        },
        "value_field": {
            "type": "string",
            "required": True,
            "description": "用于插值的属性字段名",
        },
        "method": {
            "type": "string",
            "required": False,
            "default": "linear",
            "enum": ["linear", "nearest", "cubic", "idw"],
            "description": "插值方法",
        },
        "resolution": {
            "type": "number",
            "required": False,
            "default": 100,
            "description": "输出栅格分辨率（像素数，宽度方向）",
        },
        "power": {
            "type": "number",
            "required": False,
            "default": 2,
            "description": "IDW 距离幂次（仅 method=idw 时有效）",
        },
    },
    outputs={
        "output": {"type": "raster_info", "description": "插值结果栅格"},
    },
    examples=[
        {
            "description": "线性插值温度数据",
            "params": {
                "input": "$stations.output",
                "value_field": "temperature",
                "method": "linear",
                "resolution": 200,
            },
        },
    ],
)
def analysis_interpolate(ctx: StepContext) -> StepResult:
    import numpy as np
    from scipy.interpolate import griddata
    from rasterio.transform import from_bounds

    gdf = ctx.input("input")
    value_field = ctx.param("value_field")
    method = ctx.param("method", "linear")
    resolution = ctx.param("resolution", 100)
    power = ctx.param("power", 2)

    if value_field not in gdf.columns:
        raise ValueError(
            f"Field '{value_field}' not found. Available: {list(gdf.columns)}"
        )

    coords = np.array([(g.x, g.y) for g in gdf.geometry])
    values = gdf[value_field].values.astype(np.float64)

    minx, miny, maxx, maxy = gdf.total_bounds
    dx = maxx - minx
    dy = maxy - miny
    if dx == 0:
        dx = 1.0
        minx -= 0.5
        maxx += 0.5
    if dy == 0:
        dy = 1.0
        miny -= 0.5
        maxy += 0.5

    width = resolution
    height = max(1, int(resolution * dy / dx))

    xi = np.linspace(minx, maxx, width)
    yi = np.linspace(maxy, miny, height)  # Top to bottom for raster
    grid_x, grid_y = np.meshgrid(xi, yi)

    if method == "idw":
        # Inverse Distance Weighting
        grid_z = _idw(coords, values, grid_x, grid_y, power)
    else:
        grid_z = griddata(
            coords, values, (grid_x, grid_y), method=method, fill_value=np.nan
        )

    transform = from_bounds(minx, miny, maxx, maxy, width, height)
    result_data = grid_z[np.newaxis, :, :]

    profile = {
        "driver": "GTiff",
        "dtype": "float64",
        "width": width,
        "height": height,
        "count": 1,
        "crs": gdf.crs,
        "transform": transform,
    }

    result = {
        "data": result_data,
        "transform": transform,
        "crs": gdf.crs,
        "profile": profile,
    }

    valid = grid_z[np.isfinite(grid_z)]
    stats = {
        "method": method,
        "point_count": len(gdf),
        "width": width,
        "height": height,
        "min": float(valid.min()) if valid.size > 0 else None,
        "max": float(valid.max()) if valid.size > 0 else None,
        "mean": float(valid.mean()) if valid.size > 0 else None,
    }

    return StepResult(output=result, stats=stats)


def _idw(
    points: "np.ndarray",
    values: "np.ndarray",
    grid_x: "np.ndarray",
    grid_y: "np.ndarray",
    power: float,
) -> "np.ndarray":
    """Inverse Distance Weighting interpolation."""
    import numpy as np

    flat_x = grid_x.ravel()
    flat_y = grid_y.ravel()
    result = np.zeros(flat_x.shape)

    for i in range(len(flat_x)):
        dist = np.sqrt((points[:, 0] - flat_x[i]) ** 2 + (points[:, 1] - flat_y[i]) ** 2)
        # Avoid division by zero
        mask = dist > 0
        if not mask.all():
            # Point coincides with a data point
            result[i] = values[~mask][0]
        else:
            weights = 1.0 / dist[mask] ** power
            result[i] = np.sum(weights * values[mask]) / np.sum(weights)

    return result.reshape(grid_x.shape)
