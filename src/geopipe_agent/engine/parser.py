"""YAML pipeline parser."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from geopipe_agent.errors import PipelineParseError
from geopipe_agent.models.pipeline import PipelineDefinition, StepDefinition


def parse_yaml(source: str | Path) -> PipelineDefinition:
    """Parse a YAML pipeline file or string into a PipelineDefinition.

    Args:
        source: A file path or a YAML string.

    Returns:
        Parsed PipelineDefinition.

    Raises:
        PipelineParseError: If parsing fails.
    """
    raw = _load_yaml(source)
    return _build_pipeline(raw)


def _load_yaml(source: str | Path) -> dict:
    """Load YAML from a file path or raw string."""
    try:
        path = Path(source)
        if path.exists() and path.is_file():
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        else:
            data = yaml.safe_load(source)
    except yaml.YAMLError as e:
        raise PipelineParseError(f"Invalid YAML: {e}") from e
    except Exception as e:
        # Try parsing as raw YAML string
        try:
            data = yaml.safe_load(str(source))
        except yaml.YAMLError as e2:
            raise PipelineParseError(f"Cannot parse pipeline source: {e2}") from e2

    if not isinstance(data, dict):
        raise PipelineParseError(
            "Pipeline YAML must be a mapping with a 'pipeline' key at the top level."
        )
    return data


def _build_pipeline(raw: dict) -> PipelineDefinition:
    """Convert raw YAML dict to PipelineDefinition."""
    if "pipeline" not in raw:
        raise PipelineParseError(
            "Missing 'pipeline' key at the top level. "
            "Expected: pipeline:\\n  name: ...\\n  steps: ..."
        )

    pipe = raw["pipeline"]
    if not isinstance(pipe, dict):
        raise PipelineParseError("'pipeline' must be a mapping.")

    name = pipe.get("name", "Unnamed Pipeline")
    description = pipe.get("description", "")
    crs = pipe.get("crs")
    variables = pipe.get("variables", {}) or {}
    outputs = pipe.get("outputs", {}) or {}

    raw_steps = pipe.get("steps")
    if not raw_steps or not isinstance(raw_steps, list):
        raise PipelineParseError(
            "'pipeline.steps' must be a non-empty list of step definitions."
        )

    steps = []
    for i, raw_step in enumerate(raw_steps):
        if not isinstance(raw_step, dict):
            raise PipelineParseError(f"Step {i} must be a mapping, got {type(raw_step).__name__}")
        step = _parse_step(raw_step, i)
        steps.append(step)

    return PipelineDefinition(
        name=name,
        steps=steps,
        description=description,
        crs=crs,
        variables=variables,
        outputs=outputs,
    )


def _parse_step(raw: dict, index: int) -> StepDefinition:
    """Parse a single step definition."""
    step_id = raw.get("id")
    if not step_id:
        raise PipelineParseError(f"Step {index} is missing required 'id' field.")

    use = raw.get("use")
    if not use:
        raise PipelineParseError(
            f"Step '{step_id}' is missing required 'use' field. "
            f"'use' should be a step registry ID like 'io.read_vector' or 'vector.buffer'."
        )

    return StepDefinition(
        id=step_id,
        use=use,
        params=raw.get("params", {}),
        when=raw.get("when"),
        on_error=raw.get("on_error", "fail"),
        backend=raw.get("backend"),
    )
