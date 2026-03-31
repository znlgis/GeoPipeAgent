"""Template management router — serves pre-built GIS pipeline templates."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from ..config import BASE_DIR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/template", tags=["template"])

COOKBOOK_DIR = BASE_DIR / "cookbook"

# ── Template metadata registry ────────────────────────────────────────────────

_TEMPLATE_CATALOG: list[dict[str, Any]] = [
    {
        "id": "buffer-analysis",
        "name": "缓冲区分析 / Buffer Analysis",
        "name_en": "Buffer Analysis",
        "name_zh": "缓冲区分析",
        "description_en": "Perform buffer analysis on vector data (e.g., roads) with configurable distance and output format.",
        "description_zh": "对矢量数据（如道路）进行缓冲区分析，支持配置缓冲距离和输出格式。",
        "category": "analysis",
        "tags": ["buffer", "vector", "spatial-analysis"],
        "difficulty": "beginner",
        "filename": "buffer-analysis.yaml",
        "prompt_en": "Read road shapefile, reproject to EPSG:3857, create a 500m buffer around all features, and save as GeoJSON.",
        "prompt_zh": "读取道路 Shapefile 数据，投影到 EPSG:3857，对所有要素创建 500 米缓冲区，保存为 GeoJSON。",
    },
    {
        "id": "overlay-analysis",
        "name": "叠加分析 / Overlay Analysis",
        "name_en": "Overlay Analysis",
        "name_zh": "叠加分析",
        "description_en": "Perform intersection overlay analysis between two vector layers (e.g., land use and flood zones).",
        "description_zh": "对两个矢量图层（如土地利用与洪水区域）进行交集叠加分析。",
        "category": "analysis",
        "tags": ["overlay", "intersection", "vector"],
        "difficulty": "intermediate",
        "filename": "overlay-analysis.yaml",
        "prompt_en": "Load land use and flood zone shapefiles, compute their intersection, and export the result as GeoJSON.",
        "prompt_zh": "加载土地利用和洪水区域 Shapefile，计算它们的交集，导出结果为 GeoJSON。",
    },
    {
        "id": "batch-convert",
        "name": "批量转换 / Batch Convert",
        "name_en": "Batch Convert",
        "name_zh": "批量转换",
        "description_en": "Read Shapefile, reproject to WGS84 (EPSG:4326), and convert to GeoJSON format.",
        "description_zh": "读取 Shapefile 数据，投影到 WGS84 (EPSG:4326)，转换为 GeoJSON 格式。",
        "category": "io",
        "tags": ["convert", "reproject", "format"],
        "difficulty": "beginner",
        "filename": "batch-convert.yaml",
        "prompt_en": "Read a buildings shapefile, reproject to EPSG:4326, and export as GeoJSON.",
        "prompt_zh": "读取建筑物 Shapefile，投影到 EPSG:4326，导出为 GeoJSON。",
    },
    {
        "id": "dissolve-analysis",
        "name": "融合分析 / Dissolve Analysis",
        "name_en": "Dissolve Analysis",
        "name_zh": "融合分析",
        "description_en": "Dissolve polygon features by an attribute field (e.g., land use type).",
        "description_zh": "按属性字段（如土地利用类型）融合面要素。",
        "category": "analysis",
        "tags": ["dissolve", "aggregate", "vector"],
        "difficulty": "beginner",
        "filename": "dissolve-analysis.yaml",
        "prompt_en": "Read land use shapefile, dissolve polygons by land use type using 'first' aggregation, and save as GeoJSON.",
        "prompt_zh": "读取土地利用 Shapefile，按类型字段融合面要素，保存为 GeoJSON。",
    },
    {
        "id": "filter-simplify",
        "name": "筛选与简化 / Filter & Simplify",
        "name_en": "Filter & Simplify",
        "name_zh": "数据筛选与简化",
        "description_en": "Filter features by attribute expression and simplify geometries to reduce file size.",
        "description_zh": "按属性条件筛选要素，然后简化几何以减少文件大小。",
        "category": "vector",
        "tags": ["filter", "simplify", "query"],
        "difficulty": "beginner",
        "filename": "filter-simplify.yaml",
        "prompt_en": "Read parcels shapefile, filter features where area > 1000 sqm, simplify geometry with tolerance 1.0, and export as GeoJSON.",
        "prompt_zh": "读取地块 Shapefile，筛选面积大于 1000 平方米的要素，简化几何（容差 1.0），导出为 GeoJSON。",
    },
    {
        "id": "vector-qc",
        "name": "矢量质检 / Vector QC",
        "name_en": "Vector Data Quality Check",
        "name_zh": "矢量数据质检",
        "description_en": "Comprehensive quality check on vector data: geometry validity, attribute completeness, CRS, topology, value ranges, and duplicates.",
        "description_zh": "对矢量数据进行全面质检：几何有效性、属性完整性、坐标系、拓扑、值域和重复检查。",
        "category": "qc",
        "tags": ["quality-check", "validation", "vector"],
        "difficulty": "advanced",
        "filename": "vector-qc.yaml",
        "prompt_en": "Load buildings shapefile and perform comprehensive QC: CRS check, geometry validity, topology (no overlaps), attribute completeness, domain validation, value range check, and duplicate detection.",
        "prompt_zh": "加载建筑物 Shapefile 进行全面质检：坐标系检查、几何有效性、拓扑（无重叠）、属性完整性、域值校验、数值范围检查和重复检测。",
    },
    {
        "id": "raster-qc",
        "name": "栅格质检 / Raster QC",
        "name_en": "Raster Data Quality Check",
        "name_zh": "栅格数据质检",
        "description_en": "Quality check on raster data (e.g., DEM): NoData validation, value range, and resolution consistency.",
        "description_zh": "对栅格数据（如 DEM）进行质检：NoData 验证、值域范围和分辨率一致性检查。",
        "category": "qc",
        "tags": ["quality-check", "raster", "dem"],
        "difficulty": "intermediate",
        "filename": "raster-qc.yaml",
        "prompt_en": "Load a DEM raster and check: NoData value (-9999, max 30% ratio), value range (-500 to 9000), and resolution consistency (30x30 with 0.5 tolerance).",
        "prompt_zh": "加载 DEM 栅格数据，检查 NoData 值（-9999，最大 30% 比例）、值域范围（-500 到 9000）和分辨率一致性（30x30，容差 0.5）。",
    },
]


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/list")
async def list_templates() -> list[dict[str, Any]]:
    """Return all available templates with metadata (without YAML content)."""
    result = []
    for tpl in _TEMPLATE_CATALOG:
        entry = {k: v for k, v in tpl.items() if k != "filename"}
        # Check if YAML file actually exists
        yaml_path = COOKBOOK_DIR / tpl["filename"]
        entry["available"] = yaml_path.exists()
        result.append(entry)
    return result


@router.get("/{template_id}")
async def get_template(template_id: str) -> dict[str, Any]:
    """Load a specific template by ID, including its YAML content."""
    tpl = None
    for t in _TEMPLATE_CATALOG:
        if t["id"] == template_id:
            tpl = t
            break
    if tpl is None:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

    yaml_path = COOKBOOK_DIR / tpl["filename"]
    if not yaml_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Template YAML file not found: {tpl['filename']}",
        )

    yaml_content = yaml_path.read_text(encoding="utf-8")
    result = {k: v for k, v in tpl.items() if k != "filename"}
    result["yaml_content"] = yaml_content
    return result
