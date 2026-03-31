"""Execution report builder."""

from __future__ import annotations

from collections import Counter
from typing import Any


def build_report(
    pipeline_name: str,
    status: str,
    duration: float,
    step_reports: list[dict],
    outputs: dict[str, Any] | None = None,
) -> dict:
    """Build a JSON-serializable execution report.

    The report structure is designed for AI consumption — flat, predictable,
    and including all information needed to interpret results.

    When QC steps are present in the pipeline, a ``qc_summary`` section is
    appended that aggregates all issues across steps.
    """
    report: dict[str, Any] = {
        "pipeline": pipeline_name,
        "status": status,
        "duration_seconds": duration,
        "steps": step_reports,
        "outputs": outputs or {},
    }

    # Aggregate QC issues from all steps
    qc_summary = _build_qc_summary(step_reports)
    if qc_summary:
        report["qc_summary"] = qc_summary

    return report


def _build_qc_summary(step_reports: list[dict]) -> dict[str, Any] | None:
    """Aggregate QC issues from all step reports into a summary.

    Returns ``None`` when no QC issues exist in any step.
    """
    all_issues: list[dict] = []
    for sr in step_reports:
        issues = sr.get("issues")
        if issues:
            all_issues.extend(issues)

    if not all_issues:
        return None

    by_severity = Counter(issue.get("severity", "unknown") for issue in all_issues)
    by_rule = Counter(issue.get("rule_id", "unknown") for issue in all_issues)

    return {
        "total_issues": len(all_issues),
        "by_severity": dict(by_severity),
        "by_rule": dict(by_rule),
        "issues": all_issues,
    }
