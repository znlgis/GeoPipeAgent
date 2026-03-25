"""qc.attribute_domain — Validate attribute values against allowed domains."""

from __future__ import annotations

import re

import pandas as pd

from geopipe_agent.steps.registry import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult
from geopipe_agent.models.qc import QcIssue


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
        issues.append(QcIssue(
            rule_id="attribute_domain",
            severity=severity,
            feature_index=None,
            message=f"Field '{field_name}' does not exist in the dataset",
            details={"field": field_name},
        ))
    else:
        compiled_pattern = re.compile(pattern_str) if pattern_str else None

        for idx, value in gdf[field_name].items():
            if value is None or (isinstance(value, float) and pd.isna(value)):
                continue  # skip nulls

            violation = False
            if allowed_values is not None and value not in allowed_values:
                violation = True
                msg = (
                    f"Feature {idx}: {field_name}='{value}' "
                    f"not in allowed values {allowed_values}"
                )
            elif compiled_pattern is not None and not compiled_pattern.fullmatch(str(value)):
                violation = True
                msg = (
                    f"Feature {idx}: {field_name}='{value}' "
                    f"does not match pattern '{pattern_str}'"
                )

            if violation:
                issues.append(QcIssue(
                    rule_id="attribute_domain",
                    severity=severity,
                    feature_index=idx,
                    message=msg,
                    details={"field": field_name, "value": value},
                ))

    issue_indices = sorted({
        i.feature_index for i in issues if i.feature_index is not None
    })
    issues_gdf = gdf.iloc[issue_indices].copy() if issue_indices else gdf.iloc[0:0].copy()

    stats = {
        "total_features": len(gdf),
        "issues_count": len(issues),
        "field": field_name,
        "allowed_values": allowed_values,
        "pattern": pattern_str,
    }

    return StepResult(
        output=gdf,
        stats=stats,
        metadata={"issues_gdf": issues_gdf},
        issues=issues,
    )
