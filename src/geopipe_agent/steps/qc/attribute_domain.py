"""qc.attribute_domain — Validate attribute values against allowed domains."""

from __future__ import annotations

import re

from geopipe_agent.steps.registry import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult
from geopipe_agent.models.qc import QcIssue
from geopipe_agent.steps.qc._helpers import make_vector_qc_result, is_null, field_missing_issue


@step(
    id="qc.attribute_domain",
    name="属性值域检查",
    description="检查矢量数据中指定字段的值是否在允许的值域范围内（枚举列表或正则模式）",
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
            "description": "要检查的字段名",
        },
        "allowed_values": {
            "type": "list",
            "required": False,
            "description": "允许的值列表（枚举方式）",
        },
        "pattern": {
            "type": "string",
            "required": False,
            "description": "允许的值正则表达式模式",
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
            "description": "检查用地类型是否在允许范围内",
            "params": {
                "input": "$parcels.output",
                "field": "land_use",
                "allowed_values": ["residential", "commercial", "industrial", "green"],
            },
        },
    ],
)
def qc_attribute_domain(ctx: StepContext) -> StepResult:
    gdf = ctx.input("input")
    field_name: str = ctx.param("field")
    allowed_values = ctx.param("allowed_values")
    pattern_str = ctx.param("pattern")
    severity = ctx.param("severity", "warning")

    issues: list[QcIssue] = []

    if field_name not in gdf.columns:
        issues.append(field_missing_issue(field_name, severity, "attribute_domain"))
    else:
        compiled_pattern = re.compile(pattern_str) if pattern_str else None
        for idx, value in gdf[field_name].items():
            if is_null(value):
                continue
            msg = None
            if allowed_values is not None and value not in allowed_values:
                msg = f"Feature {idx}: {field_name}='{value}' not in allowed values {allowed_values}"
            elif compiled_pattern and not compiled_pattern.fullmatch(str(value)):
                msg = f"Feature {idx}: {field_name}='{value}' does not match pattern '{pattern_str}'"
            if msg:
                issues.append(QcIssue(
                    rule_id="attribute_domain",
                    severity=severity,
                    feature_index=idx,
                    message=msg,
                    details={"field": field_name, "value": value},
                ))

    return make_vector_qc_result(gdf, issues, {
        "field": field_name,
        "allowed_values": allowed_values,
        "pattern": pattern_str,
    })
