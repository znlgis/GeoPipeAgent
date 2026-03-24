"""@step decorator for registering pipeline steps."""

from __future__ import annotations

from typing import Callable

from geopipe_agent.steps.registry import StepRegistry, _StepInfo


def step(
    id: str,
    name: str = "",
    description: str = "",
    category: str = "",
    params: dict | None = None,
    outputs: dict | None = None,
    backends: list[str] | None = None,
    examples: list[dict] | None = None,
) -> Callable:
    """Decorator that registers a function as a pipeline step.

    Usage::

        @step(
            id="vector.buffer",
            name="Buffer",
            description="Generate buffer polygons",
            category="vector",
            params={"input": {"type": "geodataframe", "required": True}, ...},
            outputs={"output": {"type": "geodataframe"}},
        )
        def vector_buffer(ctx):
            ...
    """

    def decorator(func: Callable) -> Callable:
        # Derive category from id if not provided
        cat = category or (id.split(".")[0] if "." in id else "")
        info = _StepInfo(
            id=id,
            func=func,
            name=name,
            description=description,
            category=cat,
            params=params,
            outputs=outputs,
            backends=backends,
            examples=examples,
        )
        StepRegistry().register(info)
        # Attach metadata to the function for introspection
        func._step_info = info
        return func

    return decorator
