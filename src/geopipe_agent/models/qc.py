"""Quality check issue models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class QcIssue:
    """Single quality check issue record.

    Represents one violation found during a QC step execution.
    Each issue pinpoints a specific feature and describes the problem.
    """

    rule_id: str
    """Rule identifier, e.g. ``"geometry_validity"``."""

    severity: str
    """Severity level: ``"error"`` | ``"warning"`` | ``"info"``."""

    feature_index: int | None = None
    """Row index of the problematic feature in the GeoDataFrame (None for dataset-level issues)."""

    message: str = ""
    """Human-readable description, e.g. ``"Feature 42: Self-intersection at (120.5, 31.2)"``."""

    geometry: Any = None
    """Optional geometry of the issue location (for visualization)."""

    details: dict = field(default_factory=dict)
    """Rule-specific extra information."""

    def to_dict(self) -> dict:
        """Convert to a JSON-serializable dict for reporting."""
        d: dict[str, Any] = {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "message": self.message,
        }
        if self.feature_index is not None:
            d["feature_index"] = self.feature_index
        if self.details:
            d["details"] = self.details
        return d
