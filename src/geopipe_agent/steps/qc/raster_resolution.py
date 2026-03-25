"""qc.raster_resolution — Check raster pixel size consistency."""

from __future__ import annotations

from geopipe_agent.steps.registry import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult
from geopipe_agent.models.qc import QcIssue


@step(
    id="qc.raster_resolution",
    name="分辨率一致性检查",
    description="检查栅格数据的像元大小是否符合预期",
    category="qc",
    params={
        "input": {
            "type": "raster",
            "required": True,
            "description": "输入栅格数据（dict: data, transform, crs, profile）",
        },
        "expected_x": {
            "type": "number",
            "required": True,
            "description": "期望的 X 方向像元大小（绝对值）",
        },
        "expected_y": {
            "type": "number",
            "required": True,
            "description": "期望的 Y 方向像元大小（绝对值）",
        },
        "tolerance": {
            "type": "number",
            "required": False,
            "default": 0.0001,
            "description": "像元大小的允许偏差",
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
            "description": "检查 DEM 分辨率为 30m",
            "params": {
                "input": "$dem.output",
                "expected_x": 30,
                "expected_y": 30,
                "tolerance": 0.5,
            },
        },
    ],
)
def qc_raster_resolution(ctx: StepContext) -> StepResult:
    raster = ctx.input("input")
    expected_x = ctx.param("expected_x")
    expected_y = ctx.param("expected_y")
    tolerance = ctx.param("tolerance", 0.0001)
    severity = ctx.param("severity", "warning")

    issues: list[QcIssue] = []

    transform = raster.get("transform")
    if transform is None:
        issues.append(QcIssue(
            rule_id="raster_resolution",
            severity="error",
            feature_index=None,
            message="Raster has no transform defined",
        ))
        return StepResult(
            output=raster,
            stats={"issues_count": len(issues)},
            issues=issues,
        )

    # Extract pixel sizes from the affine transform
    # transform[0] = pixel width (X), transform[4] = pixel height (Y, typically negative)
    actual_x = abs(transform[0])
    actual_y = abs(transform[4])

    if abs(actual_x - expected_x) > tolerance:
        issues.append(QcIssue(
            rule_id="raster_resolution",
            severity=severity,
            feature_index=None,
            message=(
                f"X resolution mismatch: expected {expected_x}, "
                f"got {actual_x} (diff={abs(actual_x - expected_x):.6f})"
            ),
            details={
                "axis": "x",
                "expected": expected_x,
                "actual": actual_x,
                "tolerance": tolerance,
            },
        ))

    if abs(actual_y - expected_y) > tolerance:
        issues.append(QcIssue(
            rule_id="raster_resolution",
            severity=severity,
            feature_index=None,
            message=(
                f"Y resolution mismatch: expected {expected_y}, "
                f"got {actual_y} (diff={abs(actual_y - expected_y):.6f})"
            ),
            details={
                "axis": "y",
                "expected": expected_y,
                "actual": actual_y,
                "tolerance": tolerance,
            },
        ))

    stats = {
        "issues_count": len(issues),
        "actual_x_resolution": actual_x,
        "actual_y_resolution": actual_y,
        "expected_x_resolution": expected_x,
        "expected_y_resolution": expected_y,
    }

    return StepResult(output=raster, stats=stats, issues=issues)
