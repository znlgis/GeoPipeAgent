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
    """Execute a validated pipeline and return a JSON-serializable report."""
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
        }

        # Conditional execution
        if step_def.when and not _evaluate_condition(step_def.when, context):
            step_report.update(
                status="skipped",
                duration=round(time.time() - step_start, 3),
                skip_reason=f"condition not met: {step_def.when}",
            )
            step_reports.append(step_report)
            context.set_output(step_def.id, StepResult())
            logger.info("Step '%s' skipped (when=%s)", step_def.id, step_def.when)
            continue

        try:
            result = _execute_step(step_def, context, backend_manager)
            context.set_output(step_def.id, result)

            step_report.update(
                status="success",
                duration=round(time.time() - step_start, 3),
                output_summary=result.summary(),
            )
            if result.issues:
                step_report["issues_count"] = len(result.issues)
                step_report["issues"] = [i.to_dict() for i in result.issues]

            logger.info(
                "Step '%s' (%s) completed in %.3fs",
                step_def.id, step_def.use, step_report["duration"],
            )

        except StepExecutionError:
            raise
        except Exception as e:
            step_report.update(
                duration=round(time.time() - step_start, 3),
                error=str(e),
            )
            if step_def.on_error == "skip":
                step_report["status"] = "skipped"
                context.set_output(step_def.id, StepResult())
                logger.warning("Step '%s' failed (skipped): %s", step_def.id, e)
            else:
                overall_status = "error"
                step_report["status"] = "error"
                step_reports.append(step_report)
                raise StepExecutionError(
                    step_def.id, str(e), cause=e,
                    suggestion=_suggest_fix(step_def.use, e),
                ) from e

        step_reports.append(step_report)

    total_duration = round(time.time() - pipeline_start, 3)

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


def _execute_step(step_def, context, backend_manager):
    """Execute a single step, with retry if on_error='retry'."""
    max_attempts = _MAX_RETRIES if step_def.on_error == "retry" else 1

    def _run():
        resolved_params = context.resolve_params(step_def.params)
        step_info = registry.get(step_def.use)
        if step_info is None:
            raise StepExecutionError(
                step_def.id,
                f"Step type '{step_def.use}' is not registered.",
                suggestion=f"Available: {[s.id for s in registry.list_all()]}",
            )
        _validate_step_params(step_def.id, resolved_params, step_info)

        backend = None
        if step_info.backends:
            backend = backend_manager.get(step_def.backend)

        ctx = StepContext(
            params=resolved_params,
            backend=backend,
            pipeline_context=context,
        )
        result = step_info.func(ctx)
        return result if isinstance(result, StepResult) else StepResult(output=result)

    return _with_retry(_run, max_attempts, step_def.id)


def _with_retry(fn, max_attempts: int, step_id: str):
    """Call fn(), retrying on failure up to max_attempts times."""
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except StepExecutionError:
            raise
        except Exception as e:
            last_error = e
            if attempt < max_attempts:
                logger.warning(
                    "Step '%s' attempt %d/%d failed: %s — retrying...",
                    step_id, attempt, max_attempts, e,
                )
                time.sleep(0.5 * attempt)
    raise last_error


def _validate_step_params(step_id, resolved_params, step_info):
    """Validate required params are present and coerce types where possible."""
    if not step_info.params:
        return

    missing = [
        name for name, spec in step_info.params.items()
        if spec.get("required", False) and name not in resolved_params
    ]
    if missing:
        param_docs = {
            name: step_info.params[name].get("description", "")
            for name in missing
        }
        raise StepExecutionError(
            step_id,
            f"Missing required parameter(s): {missing}. "
            f"Provided: {sorted(resolved_params.keys())}.",
            suggestion=f"Add the missing param(s): {param_docs}",
        )

    # Type coercion: convert string values to expected types where safe
    for name, spec in step_info.params.items():
        if name not in resolved_params:
            continue
        expected = spec.get("type", "")
        value = resolved_params[name]
        if value is None:
            continue
        try:
            if expected == "number" and isinstance(value, str):
                resolved_params[name] = float(value) if "." in value else int(value)
            elif expected == "boolean" and isinstance(value, str):
                resolved_params[name] = value.lower() in ("true", "1", "yes")
        except (ValueError, TypeError):
            pass  # leave as-is; step will report the error with context


def _evaluate_condition(condition: str, context: PipelineContext) -> bool:
    """Evaluate a ``when`` condition expression safely."""
    resolved = condition

    # Replace ${var} placeholders
    def _replace_var(m: re.Match) -> str:
        val = context.variables.get(m.group(1), "")
        return repr(val)

    resolved = re.sub(r"\$\{(\w+)\}", _replace_var, resolved)

    # Replace $step_id.attr and bare $step_id references
    def _replace_ref(m: re.Match) -> str:
        try:
            return repr(context.resolve(m.group(0)))
        except Exception:
            return repr(None)

    resolved = re.sub(r"\$(\w[\w-]*)(?:\.(\w+))?", _replace_ref, resolved)

    # AST validation
    try:
        tree = ast.parse(resolved, mode="eval")
    except SyntaxError:
        logger.warning("Cannot parse when='%s' (resolved='%s'), treating as False", condition, resolved)
        return False

    unsafe = validate_condition_ast(tree)
    if unsafe:
        logger.warning("%s in when='%s', treating as False", unsafe, condition)
        return False

    try:
        return bool(eval(compile(tree, "<when>", "eval"), {"__builtins__": {}}, {}))  # noqa: S307
    except Exception:
        logger.warning("Cannot evaluate when='%s' (resolved='%s'), treating as False", condition, resolved)
        return False


def _suggest_fix(step_use: str, error: Exception) -> str | None:
    """Generate an AI-friendly fix suggestion based on the error."""
    msg = str(error).lower()

    patterns = [
        (lambda m: "crs" in m and ("mismatch" in m or "degree" in m),
         "Add a vector.reproject step before this step to convert to a projected CRS."),
        (lambda m: "crs" in m and "none" in m,
         "The input data has no CRS. Set it with vector.reproject or ensure the source file has CRS metadata."),
        (lambda m: "file not found" in m or "no such file" in m,
         "Check that the input file path is correct and the file exists."),
        (lambda m: "permission" in m,
         "Check file permissions for the input/output paths."),
        (lambda m: "driver" in m or ("unsupported" in m and "format" in m),
         "Check the file format. Supported vector: GeoJSON, Shapefile, GPKG. Supported raster: GeoTIFF."),
        (lambda m: "self-intersection" in m or "invalid geometry" in m,
         "Add a qc.geometry_validity step with auto_fix=true before this step."),
        (lambda m: "empty geometry" in m,
         "Filter out features with empty geometries using vector.query before this step."),
        (lambda m: "keyerror" in m or ("column" in m and "not found" in m),
         "Check that the referenced column/field name exists. Use io.read_vector stats to see available columns."),
        (lambda m: "could not convert" in m or "dtype" in m,
         "Check that the field has the expected data type."),
        (lambda m: "ogr2ogr" in m or "gdal" in m,
         "The GDAL CLI backend encountered an error. Try using the native_python backend instead."),
        (lambda m: "qgis_process" in m,
         "The QGIS Process backend encountered an error. Try using the native_python backend instead."),
    ]

    for check, suggestion in patterns:
        if check(msg):
            return suggestion
    return None


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
        return type(value).__name__
