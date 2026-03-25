"""qc.duplicate_check — Detect duplicate features by geometry or attributes."""

from __future__ import annotations

from geopipe_agent.steps.registry import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult
from geopipe_agent.models.qc import QcIssue
from geopipe_agent.steps.qc._helpers import make_vector_qc_result


@step(
    id="qc.duplicate_check",
    name="重复要素检查",
    description="检测矢量数据中几何或属性重复的要素",
    category="qc",
    params={
        "input": {
            "type": "geodataframe",
            "required": True,
            "description": "输入矢量数据",
        },
        "check_geometry": {
            "type": "boolean",
            "required": False,
            "default": True,
            "description": "是否检查几何重复",
        },
        "check_fields": {
            "type": "list",
            "required": False,
            "description": "要检查重复的属性字段列表（不指定则不检查属性重复）",
        },
        "tolerance": {
            "type": "number",
            "required": False,
            "default": 0.0,
            "description": "几何比较容差",
        },
        "severity": {
            "type": "string",
            "required": False,
            "default": "warning",
            "enum": ["error", "warning", "info"],
            "description": "问题严重级别",
        },
    },
    outputs={
        "output": {"type": "geodataframe", "description": "透传的输入数据"},
        "issues": {"type": "list", "description": "质检问题列表"},
    },
    examples=[
        {
            "description": "检查几何和名称重复",
            "params": {
                "input": "$buildings.output",
                "check_geometry": True,
                "check_fields": ["name"],
            },
        },
    ],
)
def qc_duplicate_check(ctx: StepContext) -> StepResult:
    gdf = ctx.input("input")
    check_geometry = ctx.param("check_geometry", True)
    check_fields = ctx.param("check_fields")
    tolerance = ctx.param("tolerance", 0.0)
    severity = ctx.param("severity", "warning")

    issues: list[QcIssue] = []

    # Check geometry duplicates
    if check_geometry:
        issues.extend(_check_geometry_duplicates(gdf, tolerance, severity))

    # Check attribute duplicates
    if check_fields:
        issues.extend(_check_attribute_duplicates(gdf, check_fields, severity))

    return make_vector_qc_result(gdf, issues, {
        "check_geometry": check_geometry,
        "check_fields": check_fields,
    })


def _check_geometry_duplicates(gdf, tolerance: float, severity: str) -> list[QcIssue]:
    """Detect features with identical (or near-identical) geometries."""
    issues: list[QcIssue] = []
    seen: dict[str, int] = {}

    for idx, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue

        # Use WKB as a fast equality key; for tolerance > 0, simplify first
        if tolerance > 0:
            key = geom.simplify(tolerance).wkb_hex
        else:
            key = geom.wkb_hex

        if key in seen:
            original_idx = seen[key]
            issues.append(QcIssue(
                rule_id="duplicate_geometry",
                severity=severity,
                feature_index=idx,
                message=f"Feature {idx}: geometry duplicates feature {original_idx}",
                details={"duplicate_of": original_idx},
            ))
        else:
            seen[key] = idx

    return issues


def _check_attribute_duplicates(gdf, fields: list[str], severity: str) -> list[QcIssue]:
    """Detect features with identical values in the specified fields."""
    issues: list[QcIssue] = []

    existing_fields = [f for f in fields if f in gdf.columns]
    if not existing_fields:
        return issues

    seen: dict[tuple, int] = {}
    for idx, row in gdf.iterrows():
        key = tuple(row[f] for f in existing_fields)
        if key in seen:
            original_idx = seen[key]
            issues.append(QcIssue(
                rule_id="duplicate_attributes",
                severity=severity,
                feature_index=idx,
                message=(
                    f"Feature {idx}: attribute values {dict(zip(existing_fields, key))} "
                    f"duplicate feature {original_idx}"
                ),
                details={"duplicate_of": original_idx, "fields": existing_fields},
            ))
        else:
            seen[key] = idx

    return issues
