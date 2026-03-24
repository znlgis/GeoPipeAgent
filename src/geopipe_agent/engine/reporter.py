"""Execution report builder."""

from __future__ import annotations

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
    """
    return {
        "pipeline": pipeline_name,
        "status": status,
        "duration_seconds": duration,
        "steps": step_reports,
        "outputs": outputs or {},
    }
