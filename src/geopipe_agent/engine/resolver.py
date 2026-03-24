"""Variable and reference resolver."""

from __future__ import annotations

from geopipe_agent.engine.context import PipelineContext
from geopipe_agent.models.pipeline import PipelineDefinition


def resolve_step_params(
    pipeline: PipelineDefinition,
    step_index: int,
    context: PipelineContext,
) -> dict:
    """Resolve all parameters for a step, substituting variables and references."""
    step = pipeline.steps[step_index]
    return context.resolve_params(step.params)
