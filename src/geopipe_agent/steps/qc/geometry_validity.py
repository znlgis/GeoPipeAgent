"""qc.geometry_validity — Check geometry validity of vector features."""

from __future__ import annotations

from geopipe_agent.steps.registry import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult
from geopipe_agent.models.qc import QcIssue
from geopipe_agent.steps.qc._helpers import build_issues_gdf


@step(
    id="qc.geometry_validity",
    name="几何有效性检查",
    description="检查矢量数据的几何有效性，检测自相交、空几何、环方向错误等问题",
    category="qc",
    params={
        "input": {
            "type": "geodataframe",
            "required": True,
            "description": "输入矢量数据",
        },
        "auto_fix": {
            "type": "boolean",
            "required": False,
            "default": False,
            "description": "是否自动修复无效几何（buffer(0)）",
        },
        "severity": {
            "type": "string",
            "required": False,
            "default": "error",
            "enum": ["error", "warning", "info"],
            "description": "问题严重级别",
        },
    },
    outputs={
        "output": {"type": "geodataframe", "description": "透传的输入数据（或修复后的数据）"},
        "issues": {"type": "list", "description": "质检问题列表"},
    },
    examples=[
        {
            "description": "检查建筑物几何有效性",
            "params": {"input": "$buildings.output", "auto_fix": False},
        },
    ],
)
def qc_geometry_validity(ctx: StepContext) -> StepResult:
    from shapely.validation import explain_validity

    gdf = ctx.input("input")
    auto_fix = ctx.param("auto_fix", False)
    severity = ctx.param("severity", "error")

    issues: list[QcIssue] = []

    for idx, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            issues.append(QcIssue(
                rule_id="geometry_validity",
                severity=severity,
                feature_index=idx,
                message=f"Feature {idx}: geometry is empty or null",
            ))
        elif not geom.is_valid:
            reason = explain_validity(geom)
            issues.append(QcIssue(
                rule_id="geometry_validity",
                severity=severity,
                feature_index=idx,
                message=f"Feature {idx}: {reason}",
                geometry=geom,
                details={"reason": reason},
            ))

    output_gdf = gdf
    if auto_fix and issues:
        output_gdf = gdf.copy()
        output_gdf.geometry = output_gdf.geometry.buffer(0)

    stats = {
        "total_features": len(gdf),
        "issues_count": len(issues),
        "valid_count": len(gdf) - len(issues),
    }

    return StepResult(
        output=output_gdf,
        stats=stats,
        metadata={"issues_gdf": build_issues_gdf(gdf, issues)},
        issues=issues,
    )
