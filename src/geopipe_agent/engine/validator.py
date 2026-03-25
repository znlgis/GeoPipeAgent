"""Pipeline validator — checks schema, references, and constraints."""

from __future__ import annotations

import re

from geopipe_agent.errors import PipelineValidationError
from geopipe_agent.models.pipeline import PipelineDefinition
from geopipe_agent.steps.registry import StepRegistry

# step_id must match: lowercase letters, digits, underscore, hyphen
_VALID_STEP_ID = re.compile(r"^[a-z0-9_-]+$")


def validate_pipeline(pipeline: PipelineDefinition) -> list[str]:
    """Validate a parsed pipeline definition.

    Returns a list of warning strings (non-fatal).
    Raises PipelineValidationError for fatal issues.
    """
    warnings: list[str] = []
    registry = StepRegistry()
    seen_ids: set[str] = set()
    available_outputs: set[str] = set()

    for step in pipeline.steps:
        # 1. step_id format
        if not _VALID_STEP_ID.match(step.id):
            raise PipelineValidationError(
                f"Step id '{step.id}' is invalid. "
                f"step_id must match [a-z0-9_-] (no dots allowed). "
                f"Dots are reserved for output references ($step_id.attr)."
            )

        # 2. Duplicate step_id
        if step.id in seen_ids:
            raise PipelineValidationError(
                f"Duplicate step id '{step.id}'. Each step must have a unique id."
            )
        seen_ids.add(step.id)

        # 3. Step exists in registry
        if not registry.has(step.use):
            raise PipelineValidationError(
                f"Step '{step.id}' uses '{step.use}' which is not registered. "
                f"Available steps: {[s.id for s in registry.list_all()]}"
            )

        # 4. Validate step references in params
        _validate_param_refs(step.id, step.params, available_outputs, pipeline.variables)

        # 5. Validate on_error
        if step.on_error not in ("fail", "skip", "retry"):
            raise PipelineValidationError(
                f"Step '{step.id}' has invalid on_error='{step.on_error}'. "
                f"Must be one of: fail, skip, retry."
            )

        # Mark this step's output as available for subsequent steps
        available_outputs.add(step.id)

    # Validate output references
    for key, ref in pipeline.outputs.items():
        if isinstance(ref, str) and ref.startswith("$"):
            ref_body = ref[1:]
            if "." in ref_body:
                step_id = ref_body.split(".")[0]
                if step_id not in seen_ids:
                    raise PipelineValidationError(
                        f"Output '{key}' references step '{step_id}' which does not exist."
                    )

    return warnings


def _validate_param_refs(
    step_id: str,
    params: dict,
    available_outputs: set[str],
    variables: dict,
) -> None:
    """Check that all $step.attr and ${var} references are valid.

    Recursively inspects nested dicts and lists.
    """
    for key, value in params.items():
        _validate_value_refs(step_id, key, value, available_outputs, variables)


def _validate_value_refs(
    step_id: str,
    key: str,
    value: object,
    available_outputs: set[str],
    variables: dict,
) -> None:
    """Validate references in a single value, recursing into dicts/lists."""
    if isinstance(value, dict):
        for k, v in value.items():
            _validate_value_refs(step_id, f"{key}.{k}", v, available_outputs, variables)
        return
    if isinstance(value, list):
        for i, v in enumerate(value):
            _validate_value_refs(step_id, f"{key}[{i}]", v, available_outputs, variables)
        return
    if not isinstance(value, str):
        return

    # Step reference
    if value.startswith("$") and not value.startswith("${"):
        ref_body = value[1:]
        if "." not in ref_body:
            raise PipelineValidationError(
                f"Step '{step_id}', param '{key}': invalid reference '{value}'. "
                f"Expected format: $other_step_id.attribute"
            )
        ref_step_id = ref_body.split(".")[0]
        if ref_step_id not in available_outputs:
            raise PipelineValidationError(
                f"Step '{step_id}', param '{key}': references step '{ref_step_id}' "
                f"which has not been defined before this step. "
                f"Available: {sorted(available_outputs)}"
            )

    # Variable reference
    if "${" in value:
        for match in re.finditer(r"\$\{(\w+)\}", value):
            var_name = match.group(1)
            if var_name not in variables:
                raise PipelineValidationError(
                    f"Step '{step_id}', param '{key}': variable '${{{var_name}}}' "
                    f"is not defined in pipeline.variables. "
                    f"Available: {sorted(variables.keys())}"
                )
