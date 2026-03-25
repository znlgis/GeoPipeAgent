"""Step registry — global catalog of all registered steps.

Module-level registry (no singleton class needed). The ``@step`` decorator
auto-registers step functions here on import.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class StepInfo:
    """Metadata for a registered step."""

    id: str
    func: Callable
    name: str = ""
    description: str = ""
    category: str = ""
    params: dict = field(default_factory=dict)
    outputs: dict = field(default_factory=dict)
    backends: list[str] = field(default_factory=list)
    examples: list[dict] = field(default_factory=list)

    def __post_init__(self):
        if not self.name:
            self.name = self.id

    def to_dict(self) -> dict:
        """Serialize step info for documentation / skill generation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "params": self.params,
            "outputs": self.outputs,
            "backends": self.backends,
            "examples": self.examples,
        }


# ---------------------------------------------------------------------------
# Module-level registry
# ---------------------------------------------------------------------------

_steps: dict[str, StepInfo] = {}


def register(info: StepInfo) -> None:
    _steps[info.id] = info


def get(step_id: str) -> StepInfo | None:
    return _steps.get(step_id)


def list_all() -> list[StepInfo]:
    return list(_steps.values())


def list_by_category(category: str) -> list[StepInfo]:
    return [s for s in _steps.values() if s.category == category]


def has(step_id: str) -> bool:
    return step_id in _steps


def categories() -> list[str]:
    return sorted({s.category for s in _steps.values()})


def reset() -> None:
    """Clear the registry (useful for testing)."""
    _steps.clear()


# ---------------------------------------------------------------------------
# @step decorator
# ---------------------------------------------------------------------------


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
            params={"input": {"type": "geodataframe", "required": True}},
            outputs={"output": {"type": "geodataframe"}},
        )
        def vector_buffer(ctx):
            ...
    """

    def decorator(func: Callable) -> Callable:
        cat = category or (id.split(".")[0] if "." in id else "")
        info = StepInfo(
            id=id,
            func=func,
            name=name,
            description=description,
            category=cat,
            params=params or {},
            outputs=outputs or {},
            backends=backends or [],
            examples=examples or [],
        )
        register(info)
        func._step_info = info  # type: ignore[attr-defined]
        return func

    return decorator


# ---------------------------------------------------------------------------
# Backward-compatible wrapper so existing ``StepRegistry()`` calls keep working
# during migration. All methods delegate to the module-level functions above.
# ---------------------------------------------------------------------------


class StepRegistry:
    """Thin compatibility wrapper around the module-level registry."""

    def register(self, info: StepInfo) -> None:  # noqa: D102
        register(info)

    def get(self, step_id: str) -> StepInfo | None:  # noqa: D102
        return get(step_id)

    def list_all(self) -> list[StepInfo]:  # noqa: D102
        return list_all()

    def list_by_category(self, category: str) -> list[StepInfo]:  # noqa: D102
        return list_by_category(category)

    def has(self, step_id: str) -> bool:  # noqa: D102
        return has(step_id)

    def categories(self) -> list[str]:  # noqa: D102
        return categories()

    @staticmethod
    def reset() -> None:  # noqa: D102
        reset()
