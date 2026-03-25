"""Step result models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StepResult:
    """Result of executing a single pipeline step.

    Steps return a StepResult containing output data and optional metadata.
    Attributes are accessible via dot notation for step references ($step_id.output).

    QC steps populate the ``issues`` list with :class:`~geopipe_agent.models.qc.QcIssue`
    instances. Non-QC steps leave it empty (backwards-compatible).
    """

    output: Any = None
    stats: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    issues: list = field(default_factory=list)

    def __getattr__(self, name: str) -> Any:
        # Allow accessing stats/metadata keys as attributes for $step.key references
        if name.startswith("_"):
            raise AttributeError(name)
        # Use __dict__ to avoid recursive __getattr__ calls during init/unpickling
        stats = self.__dict__.get("stats", {})
        metadata = self.__dict__.get("metadata", {})
        if name in stats:
            return stats[name]
        if name in metadata:
            return metadata[name]
        raise AttributeError(
            f"StepResult has no attribute '{name}'. "
            f"Available: output, stats={list(stats.keys())}, "
            f"metadata={list(metadata.keys())}"
        )

    def summary(self) -> dict:
        """Generate a summary dict suitable for JSON reporting."""
        summary = {}
        if self.output is not None:
            try:
                # GeoDataFrame summary
                summary["feature_count"] = len(self.output)
                if hasattr(self.output, "crs") and self.output.crs:
                    summary["crs"] = str(self.output.crs)
                if hasattr(self.output, "geometry"):
                    summary["geometry_types"] = list(
                        self.output.geometry.geom_type.unique()
                    )
            except (TypeError, AttributeError):
                summary["type"] = type(self.output).__name__
        summary.update(self.stats)

        # QC issues summary
        if self.issues:
            summary["issues_count"] = len(self.issues)
            by_severity: dict[str, int] = {}
            for issue in self.issues:
                sev = getattr(issue, "severity", "unknown")
                by_severity[sev] = by_severity.get(sev, 0) + 1
            summary["issues_by_severity"] = by_severity

        return summary
