"""Pipeline execution context — data passing between steps."""

from __future__ import annotations

import re
from typing import Any

from geopipe_agent.models.result import StepResult
from geopipe_agent.errors import VariableResolutionError


def _replace_variable(m: re.Match, variables: dict) -> str:
    """Replacement function for ``${var_name}`` in string interpolation."""
    var_name = m.group(1)
    if var_name not in variables:
        raise VariableResolutionError(
            f"Variable '${{{var_name}}}' is not defined. "
            f"Available variables: {list(variables.keys())}"
        )
    return str(variables[var_name])


class PipelineContext:
    """Holds variables, step outputs, and provides reference resolution."""

    def __init__(self, variables: dict | None = None) -> None:
        self.variables: dict = dict(variables or {})
        self._step_outputs: dict[str, StepResult] = {}

    def set_output(self, step_id: str, result: StepResult) -> None:
        """Store a step's result for later reference."""
        self._step_outputs[step_id] = result

    def get_output(self, step_id: str) -> StepResult:
        """Get a step's result by step_id."""
        if step_id not in self._step_outputs:
            raise VariableResolutionError(
                f"Step '{step_id}' has no output yet. "
                f"Available step outputs: {list(self._step_outputs.keys())}"
            )
        return self._step_outputs[step_id]

    def resolve(self, value: Any) -> Any:
        """Resolve a value that may contain variable or step references.

        Handles:
          - ``$step_id.attr`` — step output reference
          - ``${var_name}`` — variable substitution
          - Plain values — returned as-is
        """
        if not isinstance(value, str):
            return value

        # Step output reference: $step_id.attr
        if value.startswith("$") and not value.startswith("${"):
            return self._resolve_step_ref(value)

        # Variable substitution: ${var_name} (may be embedded in a string)
        if "${" in value:
            return self._substitute_variables(value)

        return value

    def _resolve_step_ref(self, ref: str) -> Any:
        """Resolve ``$step_id.attr`` or ``$step_id`` (shorthand for ``.output``)."""
        ref_body = ref[1:]  # strip leading $
        if "." not in ref_body:
            # Shorthand: $step_id → $step_id.output
            step_id, attr = ref_body, "output"
        else:
            step_id, attr = ref_body.split(".", 1)
        if step_id not in self._step_outputs:
            raise VariableResolutionError(
                f"Step reference '{ref}' failed: step '{step_id}' has no output. "
                f"Available: {list(self._step_outputs.keys())}"
            )
        result = self._step_outputs[step_id]
        try:
            return getattr(result, attr)
        except AttributeError:
            raise VariableResolutionError(
                f"Step reference '{ref}' failed: StepResult for '{step_id}' "
                f"has no attribute '{attr}'"
            )

    def _substitute_variables(self, text: str) -> Any:
        """Replace ``${var_name}`` placeholders with variable values.

        If the entire string is a single ``${var}`` reference, the raw value
        is returned (preserving type). Otherwise, string interpolation is used.
        """
        # If the entire value is a single ${var} reference, return the raw value
        match = re.fullmatch(r"\$\{(\w+)\}", text)
        if match:
            var_name = match.group(1)
            if var_name not in self.variables:
                raise VariableResolutionError(
                    f"Variable '${{{var_name}}}' is not defined. "
                    f"Available variables: {list(self.variables.keys())}"
                )
            return self.variables[var_name]

        # Otherwise, do string interpolation
        return re.sub(
            r"\$\{(\w+)\}",
            lambda m: _replace_variable(m, self.variables),
            text,
        )

    def resolve_params(self, params: dict) -> dict:
        """Resolve all values in a params dict."""
        return {key: self._resolve_value(value) for key, value in params.items()}

    def _resolve_value(self, value: Any) -> Any:
        """Recursively resolve a single value (dict, list, or scalar)."""
        if isinstance(value, dict):
            return {k: self._resolve_value(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._resolve_value(v) for v in value]
        return self.resolve(value)


class StepContext:
    """Context passed to each step function during execution.

    Provides convenient access to resolved parameters and the backend.
    """

    def __init__(
        self,
        params: dict,
        backend: Any = None,
        pipeline_context: PipelineContext | None = None,
    ) -> None:
        self._params = params
        self.backend = backend
        self.pipeline_context = pipeline_context

    def param(self, name: str, default: Any = None) -> Any:
        """Get a resolved parameter value."""
        return self._params.get(name, default)

    def input(self, name: str = "input") -> Any:
        """Shortcut for getting the 'input' parameter (common pattern)."""
        return self._params.get(name)

    @property
    def params(self) -> dict:
        return self._params
