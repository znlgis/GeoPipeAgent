"""qc.raster_nodata — Check NoData value consistency in raster data."""

from __future__ import annotations

from geopipe_agent.steps.decorators import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult
from geopipe_agent.models.qc import QcIssue


@step(
    id="qc.raster_nodata",
    name="NoData一致性检查",
    description="检查栅格数据的 NoData 值是否设置、NoData 像元比例是否异常",
    category="qc",
    params={
        "input": {
            "type": "raster",
            "required": True,
            "description": "输入栅格数据（dict: data, transform, crs, profile）",
        },
        "expected_nodata": {
            "type": "number",
            "required": False,
            "description": "期望的 NoData 值（不指定则仅检查是否设置了 NoData）",
        },
        "max_nodata_ratio": {
            "type": "number",
            "required": False,
            "default": 0.5,
            "description": "允许的最大 NoData 像元比例（0~1），超过此比例视为异常",
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
        "output": {"type": "raster", "description": "透传的输入栅格数据"},
        "issues": {"type": "list", "description": "质检问题列表"},
    },
    examples=[
        {
            "description": "检查 DEM 的 NoData 设置",
            "params": {
                "input": "$dem.output",
                "expected_nodata": -9999,
                "max_nodata_ratio": 0.3,
            },
        },
    ],
)
def qc_raster_nodata(ctx: StepContext) -> StepResult:
    import numpy as np

    raster = ctx.input("input")
    expected_nodata = ctx.param("expected_nodata")
    max_ratio = ctx.param("max_nodata_ratio", 0.5)
    severity = ctx.param("severity", "warning")

    issues: list[QcIssue] = []

    data = raster["data"]
    profile = raster.get("profile", {})
    actual_nodata = profile.get("nodata")

    # Check if NoData is defined
    if actual_nodata is None:
        issues.append(QcIssue(
            rule_id="raster_nodata",
            severity=severity,
            feature_index=None,
            message="Raster has no NoData value defined in profile",
        ))
    else:
        # Check expected NoData value
        if expected_nodata is not None and actual_nodata != expected_nodata:
            issues.append(QcIssue(
                rule_id="raster_nodata",
                severity=severity,
                feature_index=None,
                message=(
                    f"NoData value mismatch: expected {expected_nodata}, "
                    f"got {actual_nodata}"
                ),
                details={
                    "expected_nodata": expected_nodata,
                    "actual_nodata": actual_nodata,
                },
            ))

        # Check NoData ratio
        total_pixels = data.size
        if total_pixels > 0:
            nodata_count = int(np.sum(data == actual_nodata))
            ratio = nodata_count / total_pixels
            if ratio > max_ratio:
                issues.append(QcIssue(
                    rule_id="raster_nodata",
                    severity=severity,
                    feature_index=None,
                    message=(
                        f"NoData ratio {ratio:.2%} exceeds maximum "
                        f"allowed {max_ratio:.2%}"
                    ),
                    details={
                        "nodata_count": nodata_count,
                        "total_pixels": total_pixels,
                        "nodata_ratio": round(ratio, 4),
                        "max_ratio": max_ratio,
                    },
                ))

    stats = {
        "issues_count": len(issues),
        "actual_nodata": actual_nodata,
    }

    return StepResult(
        output=raster,
        stats=stats,
        issues=issues,
    )
