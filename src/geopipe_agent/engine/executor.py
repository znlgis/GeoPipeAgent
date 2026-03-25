"""Pipeline executor — runs validated pipelines step by step."""

from __future__ import annotations

import ast
import logging
import re
import time
from typing import Any

from geopipe_agent.backends import BackendManager
from geopipe_agent.engine.context import PipelineContext, StepContext
from geopipe_agent.engine.reporter import build_report
from geopipe_agent.errors import StepExecutionError
from geopipe_agent.models.pipeline import PipelineDefinition
from geopipe_agent.models.result import StepResult
from geopipe_agent.steps import registry
from geopipe_agent.utils.safe_eval import validate_condition_ast

logger = logging.getLogger("geopipe_agent")

_MAX_RETRIES = 3


def execute_pipeline(pipeline: PipelineDefinition) -> dict:
    """Execute a validated pipeline and return a JSON-serializable report.

    Execution flow:
      1. Create PipelineContext with variables
      2. For each step: resolve params → select backend → call step func → store output
      3. Build and return execution report
    """
    context = PipelineContext(variables=pipeline.variables)
    backend_manager = BackendManager()

    step_reports: list[dict] = []
    pipeline_start = time.time()
    overall_status = "success"

    for step_def in pipeline.steps:
        step_start = time.time()
        step_report: dict[str, Any] = {
            "id": step_def.id,
            "step": step_def.use,
            "status": "running",
        }

        # --- when: conditional execution ---
        if step_def.when:
            if not _evaluate_condition(step_def.when, context):
                step_report["status"] = "skipped"
                step_report["duration"] = round(time.time() - step_start, 3)
                step_report["skip_reason"] = f"condition not met: {step_def.when}"
                step_reports.append(step_report)
                context.set_output(step_def.id, StepResult())
                logger.info("Step '%s' skipped (when=%s)", step_def.id, step_def.when)
                continue

        try:
            _execute_step(
                step_def, context, backend_manager, step_report, step_start,
            )
            logger.info(
                "Step '%s' (%s) completed in %.3fs",
                step_def.id, step_def.use, step_report["duration"],
            )
        except StepExecutionError:
            raise
        except Exception as e:
            duration = round(time.time() - step_start, 3)
            step_report["status"] = "error"
            step_report["duration"] = duration
            step_report["error"] = str(e)

            if step_def.on_error == "skip":
                logger.warning("Step '%s' failed (skipped): %s", step_def.id, e)
                step_report["status"] = "skipped"
                context.set_output(step_def.id, StepResult())
            else:
                overall_status = "error"
                step_reports.append(step_report)
                raise StepExecutionError(
                    step_def.id, str(e), cause=e,
                    suggestion=_suggest_fix(step_def.use, e),
                ) from e

        step_reports.append(step_report)

    total_duration = round(time.time() - pipeline_start, 3)

    # Resolve pipeline outputs
    resolved_outputs = {}
    for key, ref in pipeline.outputs.items():
        try:
            resolved_outputs[key] = _summarize_output(context.resolve(ref))
        except Exception as e:
            resolved_outputs[key] = f"<resolution error: {e}>"

    return build_report(
        pipeline_name=pipeline.name,
        status=overall_status,
        duration=total_duration,
        step_reports=step_reports,
        outputs=resolved_outputs,
    )


def _execute_step(
    step_def,
    context: PipelineContext,
    backend_manager: BackendManager,
    step_report: dict,
    step_start: float,
) -> None:
    """Execute a single step, optionally retrying on failure."""
    max_attempts = _MAX_RETRIES if step_def.on_error == "retry" else 1
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            # Resolve parameters
            resolved_params = context.resolve_params(step_def.params)

            # Look up step info
            step_info = registry.get(step_def.use)
            if step_info is None:
                raise StepExecutionError(
                    step_def.id,
                    f"Step type '{step_def.use}' is not registered.",
                    suggestion="Check that the step id is correct. "
                    f"Available: {[s.id for s in registry.list_all()]}",
                )

            # Validate required params
            _validate_step_params(step_def.id, resolved_params, step_info)

            # Determine backend (only steps that declare backends need one)
            backend = None
            if step_info.backends:
                backend = backend_manager.get(step_def.backend)

            # Build step context and execute
            step_ctx = StepContext(
                params=resolved_params,
                backend=backend,
                pipeline_context=context,
            )
            result = step_info.func(step_ctx)
            if not isinstance(result, StepResult):
                result = StepResult(output=result)

            # Store output in context
            context.set_output(step_def.id, result)

            step_report["status"] = "success"
            step_report["duration"] = round(time.time() - step_start, 3)
            step_report["output_summary"] = result.summary()
            if attempt > 1:
                step_report["retries"] = attempt - 1

            if result.issues:
                step_report["issues_count"] = len(result.issues)
                step_report["issues"] = [issue.to_dict() for issue in result.issues]

            return  # success

        except StepExecutionError:
            raise
        except Exception as e:
            last_error = e
            if attempt < max_attempts:
                logger.warning(
                    "Step '%s' failed (attempt %d/%d): %s — retrying…",
                    step_def.id, attempt, max_attempts, e,
                )
                time.sleep(0.5 * attempt)
            else:
                break

    assert last_error is not None
    raise last_error


def _suggest_fix(step_use: str, error: Exception) -> str | None:
    """Generate an AI-friendly fix suggestion based on the error."""
    msg = str(error).lower()

    # CRS-related errors
    if "crs" in msg and ("mismatch" in msg or "degree" in msg):
        return "Add a vector.reproject step before this step to convert to a projected CRS."
    if "crs" in msg and "none" in msg:
        return "The input data has no CRS. Set it with vector.reproject or ensure the source file has CRS metadata."

    # File I/O errors
    if "file not found" in msg or "no such file" in msg:
        return "Check that the input file path is correct and the file exists."
    if "permission" in msg:
        return "Check file permissions for the input/output paths."
    if "driver" in msg or "unsupported" in msg and "format" in msg:
        return "Check the file format. Supported vector formats: GeoJSON, Shapefile, GPKG. Supported raster: GeoTIFF."

    # Geometry errors
    if "self-intersection" in msg or "invalid geometry" in msg:
        return "Add a qc.geometry_validity step with auto_fix=true before this step."
    if "empty geometry" in msg:
        return "Filter out features with empty geometries using vector.query before this step."

    # Data type errors
    if "keyerror" in msg or "column" in msg and "not found" in msg:
        return "Check that the referenced column/field name exists in the input data. Use io.read_vector stats to see available columns."
    if "could not convert" in msg or "dtype" in msg:
        return "Check that the field has the expected data type (numeric for calculations, string for text operations)."

    # Backend errors
    if "ogr2ogr" in msg or "gdal" in msg:
        return "The GDAL CLI backend encountered an error. Try using the geopandas backend instead."
    if "qgis_process" in msg:
        return "The QGIS Process backend encountered an error. Try using the geopandas backend instead."

    return None


def _validate_step_params(
    step_id: str, resolved_params: dict, step_info: "registry.StepInfo",
) -> None:
    """Validate that all required params are present in resolved_params.

    Raises StepExecutionError with an AI-friendly message listing
    which params are missing and what the step expects.
    """
    if not step_info.params:
        return

    missing = []
    for name, spec in step_info.params.items():
        if spec.get("required", False) and name not in resolved_params:
            missing.append(name)

    if missing:
        available = sorted(resolved_params.keys()) if resolved_params else []
        param_docs = {
            name: spec.get("description", "")
            for name, spec in step_info.params.items()
            if name in missing
        }
        raise StepExecutionError(
            step_id,
            f"Missing required parameter(s): {missing}. "
            f"Provided: {available}.",
            suggestion=(
                f"Add the missing param(s) to the step's params section. "
                f"Expected: {param_docs}"
            ),
        )


def _evaluate_condition(condition: str, context: PipelineContext) -> bool:
    """Evaluate a ``when`` condition expression.

    Supports:
      - ``$step_id.attr == value`` / ``!= / > / < / >= / <=``
      - Variable substitution ``${var}``
      - Bare step output references ``$step_id.output`` (truthy check)

    Security: Uses AST validation to ensure only comparison/boolean
    expressions are evaluated — no function calls, attribute access,
    or other potentially dangerous constructs.
    """
    resolved = condition

    # Replace ${var} placeholders
    def _replace_var(m: re.Match) -> str:
        var_name = m.group(1)
        try:
            val = context.variables.get(var_name, "")
            return repr(val)
        except Exception:
            return repr("")

    resolved = re.sub(r"\$\{(\w+)\}", _replace_var, resolved)

    # Replace $step_id.attr and bare $step_id references
    def _replace_ref(m: re.Match) -> str:
        ref = m.group(0)
        try:
            val = context.resolve(ref)
            return repr(val)
        except Exception:
            return repr(None)

    # Match $step_id.attr first (longer match), then bare $step_id
    resolved = re.sub(r"\$(\w[\w-]*)(?:\.(\w+))?", _replace_ref, resolved)

    # Validate AST before eval: only allow safe node types
    try:
        tree = ast.parse(resolved, mode="eval")
    except SyntaxError:
        logger.warning(
            "Failed to parse when condition '%s' (resolved: '%s'), treating as False",
            condition, resolved,
        )
        return False

    unsafe = validate_condition_ast(tree)
    if unsafe:
        logger.warning(
            "%s in when condition '%s', treating as False",
            unsafe, condition,
        )
        return False

    try:
        return bool(eval(  # noqa: S307
            compile(tree, "<when>", "eval"),
            {"__builtins__": {}},
            {},
        ))
    except Exception:
        logger.warning(
            "Failed to evaluate when condition '%s' (resolved: '%s'), treating as False",
            condition, resolved,
        )
        return False


def _summarize_output(value: Any) -> Any:
    """Create a JSON-serializable summary of an output value."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return value
    try:
        return {
            "type": "GeoDataFrame",
            "feature_count": len(value),
            "crs": str(value.crs) if hasattr(value, "crs") and value.crs else None,
        }
    except Exception:
        return str(type(value).__name__)
