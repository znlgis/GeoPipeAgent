"""analysis.voronoi — Generate Voronoi polygons from point data."""

from __future__ import annotations

from geopipe_agent.steps.registry import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult


@step(
    id="analysis.voronoi",
    name="泰森多边形",
    description="根据输入点数据生成泰森多边形（Voronoi图）",
    category="analysis",
    params={
        "input": {
            "type": "geodataframe",
            "required": True,
            "description": "输入点矢量数据",
        },
        "envelope": {
            "type": "geodataframe",
            "required": False,
            "description": "裁剪边界（不指定则使用点的凸包缓冲区）",
        },
    },
    outputs={
        "output": {"type": "geodataframe", "description": "泰森多边形矢量数据"},
    },
    examples=[
        {
            "description": "为气象站点生成泰森多边形",
            "params": {"input": "$stations.output"},
        },
    ],
)
def analysis_voronoi(ctx: StepContext) -> StepResult:
    import numpy as np
    import geopandas as gpd
    from scipy.spatial import Voronoi
    from shapely.geometry import Polygon, box
    from shapely.ops import unary_union

    gdf = ctx.input("input")
    envelope_gdf = ctx.param("envelope")

    # Extract point coordinates
    coords = np.array([(g.x, g.y) for g in gdf.geometry])

    if len(coords) < 3:
        raise ValueError("Voronoi requires at least 3 points.")

    # Compute Voronoi diagram
    vor = Voronoi(coords)

    # Determine bounding box for clipping
    if envelope_gdf is not None:
        clip_geom = unary_union(envelope_gdf.geometry)
    else:
        minx, miny, maxx, maxy = gdf.total_bounds
        dx = (maxx - minx) * 0.1 or 1.0
        dy = (maxy - miny) * 0.1 or 1.0
        clip_geom = box(minx - dx, miny - dy, maxx + dx, maxy + dy)

    # Build finite Voronoi polygons
    polygons = []
    for i, region_idx in enumerate(vor.point_region):
        region = vor.regions[region_idx]
        if not region or -1 in region:
            # Open region — create a large bounding polygon and intersect
            polygons.append(clip_geom)
        else:
            vertices = [vor.vertices[v] for v in region]
            poly = Polygon(vertices)
            if poly.is_valid:
                polygons.append(poly.intersection(clip_geom))
            else:
                polygons.append(poly.buffer(0).intersection(clip_geom))

    result_gdf = gpd.GeoDataFrame(
        gdf.drop(columns="geometry").reset_index(drop=True),
        geometry=polygons,
        crs=gdf.crs,
    )

    stats = {
        "input_point_count": len(gdf),
        "polygon_count": len(result_gdf),
    }

    return StepResult(output=result_gdf, stats=stats)
