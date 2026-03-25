"""qc.attribute_completeness — Check for missing required attributes."""

from __future__ import annotations

import pandas as pd

from geopipe_agent.steps.decorators import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult
from geopipe_agent.models.qc import QcIssue


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
    columns = set(gdf.columns)

    # Check for entirely missing columns first
    missing_columns = [f for f in required_fields if f not in columns]
    for col in missing_columns:
        issues.append(QcIssue(
            rule_id="attribute_completeness",
            severity=severity,
            feature_index=None,
            message=f"Required column '{col}' does not exist in the dataset",
            details={"missing_column": col},
        ))

    # Check field values for existing required columns
    existing_required = [f for f in required_fields if f in columns]
    for col in existing_required:
        for idx, value in gdf[col].items():
            is_missing = False
            if value is None or (isinstance(value, float) and pd.isna(value)):
                is_missing = True
            elif not allow_empty and isinstance(value, str) and value.strip() == "":
                is_missing = True

            if is_missing:
                issues.append(QcIssue(
                    rule_id="attribute_completeness",
                    severity=severity,
                    feature_index=idx,
                    message=f"Feature {idx}: field '{col}' is null or empty",
                    details={"field": col},
                ))

    # Build issues GeoDataFrame subset
    issue_indices = sorted({
        i.feature_index for i in issues if i.feature_index is not None
    })
    issues_gdf = gdf.iloc[issue_indices].copy() if issue_indices else gdf.iloc[0:0].copy()

    stats = {
        "total_features": len(gdf),
        "issues_count": len(issues),
        "checked_fields": required_fields,
        "missing_columns": missing_columns,
    }

    return StepResult(
        output=gdf,
        stats=stats,
        metadata={"issues_gdf": issues_gdf},
        issues=issues,
    )
