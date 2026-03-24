"""io.read_vector — Read vector data from file."""

from __future__ import annotations

from geopipe_agent.steps.decorators import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult


@step(
    id="io.read_vector",
    name="读取矢量数据",
    description="从文件读取矢量数据（Shapefile, GeoJSON, GPKG 等），返回 GeoDataFrame",
    category="io",
    params={
        "path": {
            "type": "string",
            "required": True,
            "description": "矢量数据文件路径",
        },
        "layer": {
            "type": "string",
            "required": False,
            "description": "图层名称（多图层文件时使用）",
        },
        "encoding": {
            "type": "string",
            "required": False,
            "default": "utf-8",
            "description": "文件编码",
        },
    },
    outputs={
        "output": {"type": "geodataframe", "description": "读取的矢量数据"},
    },
    examples=[
        {
            "description": "读取 Shapefile",
            "params": {"path": "data/roads.shp"},
        },
        {
            "description": "读取 GeoJSON",
            "params": {"path": "data/buildings.geojson"},
        },
    ],
)
def io_read_vector(ctx: StepContext) -> StepResult:
    import geopandas as gpd

    path = ctx.param("path")
    layer = ctx.param("layer")
    encoding = ctx.param("encoding", "utf-8")

    kwargs = {}
    if layer:
        kwargs["layer"] = layer
    if encoding:
        kwargs["encoding"] = encoding

    gdf = gpd.read_file(path, **kwargs)

    stats = {
        "feature_count": len(gdf),
        "crs": str(gdf.crs) if gdf.crs else None,
        "geometry_types": list(gdf.geometry.geom_type.unique()) if len(gdf) > 0 else [],
        "columns": list(gdf.columns),
    }

    return StepResult(output=gdf, stats=stats)
