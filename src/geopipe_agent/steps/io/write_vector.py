"""io.write_vector — Write vector data to file."""

from __future__ import annotations

from pathlib import Path

from geopipe_agent.steps.decorators import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult

_FORMAT_MAP = {
    "geojson": "GeoJSON",
    "shapefile": "ESRI Shapefile",
    "shp": "ESRI Shapefile",
    "gpkg": "GPKG",
    "geopackage": "GPKG",
}


@step(
    id="io.write_vector",
    name="写入矢量数据",
    description="将矢量数据写入文件（GeoJSON, Shapefile, GPKG 等）",
    category="io",
    params={
        "input": {
            "type": "geodataframe",
            "required": True,
            "description": "输入矢量数据",
        },
        "path": {
            "type": "string",
            "required": True,
            "description": "输出文件路径",
        },
        "format": {
            "type": "string",
            "required": False,
            "default": "GeoJSON",
            "description": "输出格式 (GeoJSON, Shapefile, GPKG)",
        },
        "encoding": {
            "type": "string",
            "required": False,
            "default": "utf-8",
            "description": "文件编码",
        },
    },
    outputs={
        "output": {"type": "string", "description": "输出文件路径"},
    },
    examples=[
        {
            "description": "输出为 GeoJSON",
            "params": {
                "input": "$buffer.output",
                "path": "output/result.geojson",
                "format": "GeoJSON",
            },
        },
    ],
)
def io_write_vector(ctx: StepContext) -> StepResult:
    gdf = ctx.input("input")
    path = ctx.param("path")
    fmt = ctx.param("format", "GeoJSON")
    encoding = ctx.param("encoding", "utf-8")

    # Normalize format name
    driver = _FORMAT_MAP.get(fmt.lower(), fmt)

    # Ensure output directory exists
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    gdf.to_file(path, driver=driver, encoding=encoding)

    stats = {
        "feature_count": len(gdf),
        "output_path": str(path),
        "format": driver,
    }

    return StepResult(output=str(path), stats=stats)
