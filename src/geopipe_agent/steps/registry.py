"""Step registry — global catalog of all registered steps."""

from __future__ import annotations

from typing import Callable


class _StepInfo:
    """Metadata for a registered step."""

    def __init__(
        self,
        id: str,
        func: Callable,
        name: str = "",
        description: str = "",
        category: str = "",
        params: dict | None = None,
        outputs: dict | None = None,
        backends: list[str] | None = None,
        examples: list[dict] | None = None,
    ):
        self.id = id
        self.func = func
        self.name = name or id
        self.description = description
        self.category = category
        self.params = params or {}
        self.outputs = outputs or {}
        self.backends = backends or []
        self.examples = examples or []

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


class StepRegistry:
    """Singleton registry holding all step definitions.

    Uses the singleton pattern to ensure a single global catalog of steps.
    Access via ``StepRegistry()`` always returns the same instance.
    """

    _instance: StepRegistry | None = None

    def __new__(cls) -> StepRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._steps: dict[str, _StepInfo] = {}
        return cls._instance

    def register(self, info: _StepInfo) -> None:
        self._steps[info.id] = info

    def get(self, step_id: str) -> _StepInfo | None:
        return self._steps.get(step_id)

    def list_all(self) -> list[_StepInfo]:
        return list(self._steps.values())

    def list_by_category(self, category: str) -> list[_StepInfo]:
        return [s for s in self._steps.values() if s.category == category]

    def has(self, step_id: str) -> bool:
        return step_id in self._steps

    def categories(self) -> list[str]:
        return sorted({s.category for s in self._steps.values()})

    @classmethod
    def reset(cls) -> None:
        """Reset registry (useful for testing)."""
        if cls._instance is not None:
            cls._instance._steps = {}
