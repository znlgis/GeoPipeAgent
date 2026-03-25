"""Helper for vector steps that delegate to a backend method."""

from __future__ import annotations
from typing import Any, Callable

from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult


def run_backend_op(
    ctx: StepContext,
    method: str,
    *,
    positional_params: list[str] | None = None,
    keyword_params: dict[str, str] | None = None,
    extra_stats: Callable[[StepContext, Any, Any], dict] | None = None,
) -> StepResult:
    """Execute a backend operation with standardized param handling.

    Args:
        ctx: Step context.
        method: Backend method name (e.g. 'buffer', 'clip').
        positional_params: Param names to pass as positional args after input gdf.
        keyword_params: Mapping of {param_name: kwarg_name} for keyword args.
        extra_stats: Optional function(ctx, input_gdf, result_gdf) -> dict for custom stats.

    Returns:
        StepResult with the backend output and stats.
    """
    gdf = ctx.input("input")

    args = []
    if positional_params:
        for p in positional_params:
            args.append(ctx.param(p))

    kwargs = {}
    if keyword_params:
        for param_name, kwarg_name in keyword_params.items():
            val = ctx.param(param_name)
            if val is not None:
                kwargs[kwarg_name] = val

    result_gdf = getattr(ctx.backend, method)(gdf, *args, **kwargs)

    stats: dict[str, Any] = {"feature_count": len(result_gdf)}
    if extra_stats:
        stats.update(extra_stats(ctx, gdf, result_gdf))

    return StepResult(output=result_gdf, stats=stats)
