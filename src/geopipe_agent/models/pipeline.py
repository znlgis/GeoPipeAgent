"""Pipeline and step definition models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StepDefinition:
    """Definition of a single pipeline step from YAML."""

    id: str
    use: str
    params: dict = field(default_factory=dict)
    when: str | None = None
    on_error: str = "fail"  # fail / skip / retry
    backend: str | None = None

    def __post_init__(self):
        if self.params is None:
            self.params = {}


@dataclass
class PipelineDefinition:
    """Parsed pipeline definition from YAML."""

    name: str
    steps: list[StepDefinition]
    description: str = ""
    crs: str | None = None
    variables: dict = field(default_factory=dict)
    outputs: dict = field(default_factory=dict)
