"""qc.value_range — Check numeric field values against min/max thresholds."""

from __future__ import annotations

from geopipe_agent.steps.registry import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult
from geopipe_agent.models.qc import QcIssue
from geopipe_agent.steps.qc._helpers import make_vector_qc_result, is_null, field_missing_issue


@step(
    id="qc.value_range",
    name="数值范围检查",
    description="检查矢量数据中数值字段的值是否在指定的最小/最大范围内",
    category="qc",
    params={
        "input": {
            "type": "geodataframe",
            "required": True,
            "description": "输入矢量数据",
        },
        "field": {
            "type": "string",
            "required": True,
            "description": "要检查的数值字段名",
        },
        "min": {
            "type": "number",
            "required": False,
            "description": "允许的最小值（含），不指定则不检查下界",
        },
        "max": {
            "type": "number",
            "required": False,
            "description": "允许的最大值（含），不指定则不检查上界",
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
            "description": "检查建筑高度在合理范围内",
            "params": {
                "input": "$buildings.output",
                "field": "height",
                "min": 0,
                "max": 1000,
            },
        },
    ],
)
def qc_value_range(ctx: StepContext) -> StepResult:
    gdf = ctx.input("input")
    field_name: str = ctx.param("field")
    min_val = ctx.param("min")
    max_val = ctx.param("max")
    severity = ctx.param("severity", "warning")

    issues: list[QcIssue] = []

    if field_name not in gdf.columns:
        issues.append(field_missing_issue(field_name, severity, "value_range"))
    else:
        for idx, value in gdf[field_name].items():
            if is_null(value):
                continue  # skip null values (attribute_completeness handles these)

            if min_val is not None and value < min_val:
                issues.append(QcIssue(
                    rule_id="value_range",
                    severity=severity,
                    feature_index=idx,
                    message=f"Feature {idx}: {field_name}={value} is below minimum {min_val}",
                    details={"field": field_name, "value": value, "min": min_val},
                ))
            if max_val is not None and value > max_val:
                issues.append(QcIssue(
                    rule_id="value_range",
                    severity=severity,
                    feature_index=idx,
                    message=f"Feature {idx}: {field_name}={value} exceeds maximum {max_val}",
                    details={"field": field_name, "value": value, "max": max_val},
                ))

    return make_vector_qc_result(gdf, issues, {
        "field": field_name,
        "min_threshold": min_val,
        "max_threshold": max_val,
    })
