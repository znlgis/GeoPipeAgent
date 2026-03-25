"""qc.crs_check — Verify coordinate reference system."""

from __future__ import annotations

from geopipe_agent.steps.registry import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.qc import QcIssue
from geopipe_agent.steps.qc._helpers import make_vector_qc_result


@step(
    id="qc.crs_check",
    name="坐标参考系检查",
    description="验证矢量数据的坐标参考系是否正确、是否缺失",
    category="qc",
    params={
        "input": {
            "type": "geodataframe",
            "required": True,
            "description": "输入矢量数据",
        },
        "expected_crs": {
            "type": "string",
            "required": False,
            "description": "期望的 CRS（如 'EPSG:4326'），不指定则仅检查 CRS 是否存在",
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
        "output": {"type": "geodataframe", "description": "透传的输入数据"},
        "issues": {"type": "list", "description": "质检问题列表"},
    },
    examples=[
        {
            "description": "检查数据 CRS 是否为 EPSG:4326",
            "params": {"input": "$data.output", "expected_crs": "EPSG:4326"},
        },
    ],
)
def qc_crs_check(ctx: StepContext) -> StepResult:
    from pyproj import CRS

    gdf = ctx.input("input")
    expected_crs_str = ctx.param("expected_crs")
    severity = ctx.param("severity", "error")

    issues: list[QcIssue] = []

    actual_crs = gdf.crs

    if actual_crs is None:
        issues.append(QcIssue(
            rule_id="crs_check",
            severity=severity,
            feature_index=None,
            message="Dataset has no CRS defined",
        ))
    elif expected_crs_str is not None:
        expected_crs = CRS.from_user_input(expected_crs_str)
        if not actual_crs.equals(expected_crs):
            issues.append(QcIssue(
                rule_id="crs_check",
                severity=severity,
                feature_index=None,
                message=(
                    f"CRS mismatch: expected {expected_crs_str}, "
                    f"got {actual_crs.to_epsg() or actual_crs.to_wkt()}"
                ),
                details={
                    "expected": expected_crs_str,
                    "actual": str(actual_crs),
                },
            ))

    return make_vector_qc_result(gdf, issues, {
        "actual_crs": str(actual_crs) if actual_crs else None,
        "expected_crs": expected_crs_str,
    })
