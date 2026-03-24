"""Error classes for GeoPipeAgent.

All errors include AI-friendly messages with suggestions for resolution.
"""


class GeopipeAgentError(Exception):
    """Base exception for all GeoPipeAgent errors."""
    pass


class PipelineParseError(GeopipeAgentError):
    """Raised when YAML pipeline parsing fails."""
    pass


class PipelineValidationError(GeopipeAgentError):
    """Raised when pipeline validation fails (schema, references, etc.)."""
    pass


class StepExecutionError(GeopipeAgentError):
    """Raised when a step execution fails.

    Attributes:
        step_id: The ID of the step that failed.
        suggestion: AI-readable suggestion for fixing the error.
        cause: The original exception that caused this error.
    """

    def __init__(self, step_id: str, message: str, cause: Exception | None = None,
                 suggestion: str | None = None):
        self.step_id = step_id
        self.suggestion = suggestion
        self.cause = cause
        super().__init__(message)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict for AI consumption."""
        result = {
            "error": "StepExecutionError",
            "step_id": self.step_id,
            "message": str(self),
        }
        if self.suggestion:
            result["suggestion"] = self.suggestion
        if self.cause:
            result["cause"] = str(self.cause)
        return result


class BackendNotAvailableError(GeopipeAgentError):
    """Raised when a requested backend is not available."""
    pass


class StepNotFoundError(GeopipeAgentError):
    """Raised when a referenced step ID is not found in the registry."""
    pass


class VariableResolutionError(GeopipeAgentError):
    """Raised when a variable or step reference cannot be resolved."""
    pass
