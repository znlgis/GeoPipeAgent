"""qc.raster_value_range — Check raster pixel values against expected range."""

from __future__ import annotations

from geopipe_agent.steps.registry import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.qc import QcIssue
from geopipe_agent.steps.qc._helpers import make_raster_qc_result


@step(
    id="qc.raster_value_range",
    name="栅格值域检查",
    description="检查栅格数据像素值是否在预期范围内",
    category="qc",
    params={
        "input": {
            "type": "raster",
            "required": True,
            "description": "输入栅格数据（dict: data, transform, crs, profile）",
        },
        "min": {
            "type": "number",
            "required": False,
            "description": "允许的最小像素值（含），不指定则不检查下界",
        },
        "max": {
            "type": "number",
            "required": False,
            "description": "允许的最大像素值（含），不指定则不检查上界",
        },
        "band": {
            "type": "integer",
            "required": False,
            "default": 0,
            "description": "要检查的波段索引（0-based），默认检查第一个波段",
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
            "description": "检查 NDVI 值在 -1 到 1 之间",
            "params": {"input": "$ndvi.output", "min": -1, "max": 1},
        },
    ],
)
def qc_raster_value_range(ctx: StepContext) -> StepResult:
    import numpy as np

    raster = ctx.input("input")
    min_val = ctx.param("min")
    max_val = ctx.param("max")
    band = ctx.param("band", 0)
    severity = ctx.param("severity", "warning")

    issues: list[QcIssue] = []

    data = raster["data"]
    profile = raster.get("profile", {})
    nodata = profile.get("nodata")

    # Extract the target band
    if data.ndim == 3:
        if band >= data.shape[0]:
            issues.append(QcIssue(
                rule_id="raster_value_range",
                severity="error",
                feature_index=None,
                message=f"Band index {band} out of range (raster has {data.shape[0]} bands)",
            ))
            return make_raster_qc_result(raster, issues)
        band_data = data[band]
    else:
        band_data = data

    # Mask out NoData pixels
    valid_data = band_data[band_data != nodata] if nodata is not None else band_data.ravel()

    if valid_data.size == 0:
        return make_raster_qc_result(raster, [], {"valid_pixels": 0})

    actual_min = float(np.nanmin(valid_data))
    actual_max = float(np.nanmax(valid_data))

    if min_val is not None and actual_min < min_val:
        below_count = int(np.sum(valid_data < min_val))
        issues.append(QcIssue(
            rule_id="raster_value_range",
            severity=severity,
            feature_index=None,
            message=(
                f"Band {band}: {below_count} pixels below minimum {min_val} "
                f"(actual min={actual_min})"
            ),
            details={
                "band": band,
                "below_min_count": below_count,
                "actual_min": actual_min,
                "threshold_min": min_val,
            },
        ))

    if max_val is not None and actual_max > max_val:
        above_count = int(np.sum(valid_data > max_val))
        issues.append(QcIssue(
            rule_id="raster_value_range",
            severity=severity,
            feature_index=None,
            message=(
                f"Band {band}: {above_count} pixels above maximum {max_val} "
                f"(actual max={actual_max})"
            ),
            details={
                "band": band,
                "above_max_count": above_count,
                "actual_max": actual_max,
                "threshold_max": max_val,
            },
        ))

    return make_raster_qc_result(raster, issues, {
        "band": band,
        "valid_pixels": int(valid_data.size),
        "actual_min": actual_min,
        "actual_max": actual_max,
    })
