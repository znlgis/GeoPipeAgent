"""qc.raster_resolution — Check raster pixel size consistency."""

from __future__ import annotations

from geopipe_agent.steps.registry import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult
from geopipe_agent.models.qc import QcIssue
from geopipe_agent.steps.qc._helpers import make_raster_qc_result


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
        return make_raster_qc_result(raster, issues)

    # transform[0] = pixel width (X), transform[4] = pixel height (Y, typically negative)
    actual = {"x": abs(transform[0]), "y": abs(transform[4])}
    expected = {"x": expected_x, "y": expected_y}

    for axis in ("x", "y"):
        diff = abs(actual[axis] - expected[axis])
        if diff > tolerance:
            issues.append(QcIssue(
                rule_id="raster_resolution",
                severity=severity,
                feature_index=None,
                message=f"{axis.upper()} resolution mismatch: expected {expected[axis]}, got {actual[axis]} (diff={diff:.6f})",
                details={"axis": axis, "expected": expected[axis], "actual": actual[axis], "tolerance": tolerance},
            ))

    return make_raster_qc_result(raster, issues, {
        "actual_x_resolution": actual["x"],
        "actual_y_resolution": actual["y"],
        "expected_x_resolution": expected_x,
        "expected_y_resolution": expected_y,
    })
