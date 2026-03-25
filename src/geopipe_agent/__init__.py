"""GeoPipeAgent — AI-Native GIS Analysis Pipeline Framework."""

from geopipe_agent.steps.registry import step, StepInfo
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult
from geopipe_agent.models.qc import QcIssue

__version__ = "0.1.0"

# Auto-load all built-in steps so callers never need to do it manually.
from geopipe_agent.steps import load_builtin_steps as _load_builtin_steps

_load_builtin_steps()

__all__ = [
    "step",
    "StepInfo",
    "StepContext",
    "StepResult",
    "QcIssue",
    "__version__",
]
