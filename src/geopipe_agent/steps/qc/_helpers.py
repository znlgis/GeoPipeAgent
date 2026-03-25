"""QC step helpers — shared utilities for quality check steps."""

from __future__ import annotations

import math
from typing import Any

from geopipe_agent.models.qc import QcIssue
from geopipe_agent.models.result import StepResult


def build_issues_gdf(gdf: Any, issues: list[QcIssue]) -> Any:
    """Extract the subset of features that have QC issues.

    Returns an empty GeoDataFrame with the same schema if no issues
    reference specific features.
    """
    indices = sorted({
        i.feature_index for i in issues if i.feature_index is not None
    })
    return gdf.iloc[indices].copy() if indices else gdf.iloc[0:0].copy()


def make_vector_qc_result(
    gdf: Any,
    issues: list[QcIssue],
    extra_stats: dict | None = None,
) -> StepResult:
    """Build a StepResult for vector QC steps (check-and-passthrough pattern).

    Handles the common boilerplate:
    - Sets ``output`` to the original GeoDataFrame (passthrough)
    - Computes ``issues_gdf`` from issue indices
    - Builds stats with ``total_features`` and ``issues_count``
    """
    issues_gdf = build_issues_gdf(gdf, issues)
    stats: dict = {
        "total_features": len(gdf),
        "issues_count": len(issues),
    }
    if extra_stats:
        stats.update(extra_stats)
    return StepResult(
        output=gdf,
        stats=stats,
        metadata={"issues_gdf": issues_gdf},
        issues=issues,
    )


def make_raster_qc_result(
    raster: dict,
    issues: list[QcIssue],
    extra_stats: dict | None = None,
) -> StepResult:
    """Build a StepResult for raster QC steps."""
    stats: dict = {"issues_count": len(issues)}
    if extra_stats:
        stats.update(extra_stats)
    return StepResult(output=raster, stats=stats, issues=issues)


def is_null(value: Any) -> bool:
    """Check whether a value is null / NaN (common in QC field iteration)."""
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return False


def field_missing_issue(
    field: str, severity: str, rule_id: str,
) -> QcIssue:
    """Create a QcIssue for a missing field."""
    return QcIssue(
        rule_id=rule_id,
        severity=severity,
        feature_index=None,
        message=f"Field '{field}' does not exist in the dataset",
        details={"field": field},
    )
