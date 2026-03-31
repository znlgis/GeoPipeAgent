"""qc.attribute_completeness — Check for missing required attributes."""

from __future__ import annotations

from geopipe_agent.steps.registry import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult
from geopipe_agent.models.qc import QcIssue
from geopipe_agent.steps.qc._helpers import make_vector_qc_result, is_null


@step(
    id="qc.attribute_completeness",
    name="属性完整性检查",
    description="检查矢量数据的必填字段是否缺失或为空值",
    category="qc",
    params={
        "input": {
            "type": "geodataframe",
            "required": True,
            "description": "输入矢量数据",
        },
        "required_fields": {
            "type": "list",
            "required": True,
            "description": "必填字段名列表",
        },
        "allow_empty": {
            "type": "boolean",
            "required": False,
            "default": False,
            "description": "是否允许空字符串（默认不允许）",
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
            "description": "检查建筑物必填属性",
            "params": {
                "input": "$buildings.output",
                "required_fields": ["name", "height", "type"],
            },
        },
    ],
)
def qc_attribute_completeness(ctx: StepContext) -> StepResult:
    gdf = ctx.input("input")
    required_fields: list[str] = ctx.param("required_fields")
    allow_empty = ctx.param("allow_empty", False)
    severity = ctx.param("severity", "warning")

    issues: list[QcIssue] = []
    missing_columns = [f for f in required_fields if f not in gdf.columns]

    for col in missing_columns:
        issues.append(QcIssue(
            rule_id="attribute_completeness",
            severity=severity,
            feature_index=None,
            message=f"Required column '{col}' does not exist in the dataset",
            details={"missing_column": col},
        ))

    for col in required_fields:
        if col not in gdf.columns:
            continue
        for idx, value in gdf[col].items():
            if is_null(value) or (not allow_empty and isinstance(value, str) and value.strip() == ""):
                issues.append(QcIssue(
                    rule_id="attribute_completeness",
                    severity=severity,
                    feature_index=idx,
                    message=f"Feature {idx}: field '{col}' is null or empty",
                    details={"field": col},
                ))

    return make_vector_qc_result(gdf, issues, {
        "checked_fields": required_fields,
        "missing_columns": missing_columns,
    })
