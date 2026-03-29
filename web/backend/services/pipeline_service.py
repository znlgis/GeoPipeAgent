"""Pipeline engine integration service."""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator

from ..config import PIPELINES_DIR

logger = logging.getLogger(__name__)

# ── Engine imports ────────────────────────────────────────────────────────────

from geopipe_agent.steps.registry import (  # noqa: E402
    categories,
    get as get_step,
    list_all,
    list_by_category,
)
from geopipe_agent.engine.parser import parse_yaml  # noqa: E402
from geopipe_agent.engine.executor import (  # noqa: E402
    execute_pipeline as _engine_execute,
)


# ── Public helpers ────────────────────────────────────────────────────────────


def get_all_steps() -> list[dict[str, Any]]:
    """Return every registered step as a serializable dict."""
    return [step.to_dict() for step in list_all()]


def get_step_detail(step_id: str) -> dict[str, Any] | None:
    """Return detailed info for a single step, or *None* if not found."""
    info = get_step(step_id)
    if info is None:
        return None
    return info.to_dict()


def get_categories() -> list[str]:
    """Return sorted list of step categories."""
    return categories()


def get_steps_by_category(category: str) -> list[dict[str, Any]]:
    """Return steps belonging to *category*."""
    return [step.to_dict() for step in list_by_category(category)]


# ── Validation ────────────────────────────────────────────────────────────────


def validate_pipeline(yaml_content: str) -> tuple[bool, list[str]]:
    """Validate a YAML pipeline definition.

    Returns:
        A tuple of (is_valid, error_messages).
    """
    try:
        parse_yaml(yaml_content)
        return True, []
    except Exception as exc:
        return False, [str(exc)]


# ── Execution (async generator for SSE) ──────────────────────────────────────


async def execute_pipeline_stream(yaml_content: str) -> AsyncGenerator[dict[str, Any], None]:
    """Parse, execute, and stream progress/result as SSE-friendly dicts.

    Yields dicts with keys ``event`` and ``data``.
    """
    # 1. Parse
    try:
        pipeline_def = parse_yaml(yaml_content)
    except Exception as exc:
        yield {"event": "error", "data": json.dumps({"error": f"Parse error: {exc}"})}
        return

    yield {
        "event": "progress",
        "data": json.dumps({"message": "Pipeline parsed successfully", "percent": 5}),
    }

    # 2. Execute in a thread so we don't block the event loop
    try:
        yield {
            "event": "progress",
            "data": json.dumps({"message": "Executing pipeline…", "percent": 10}),
        }
        loop = asyncio.get_running_loop()
        report = await loop.run_in_executor(None, _engine_execute, pipeline_def)
    except Exception as exc:
        yield {"event": "error", "data": json.dumps({"error": f"Execution error: {exc}"})}
        return

    # 3. Emit step-level progress from report
    step_reports = report.get("steps", [])
    total = max(len(step_reports), 1)
    for idx, step_report in enumerate(step_reports):
        percent = int(10 + 85 * (idx + 1) / total)
        yield {
            "event": "progress",
            "data": json.dumps({
                "message": f"Step '{step_report.get('id', idx)}' — {step_report.get('status', 'done')}",
                "percent": percent,
                "step": step_report,
            }),
        }

    # 4. Done
    yield {
        "event": "done",
        "data": json.dumps({"report": report, "percent": 100}),
    }


# ── Persistence ───────────────────────────────────────────────────────────────


def save_pipeline(name: str, yaml_content: str) -> str:
    """Persist a pipeline YAML to disk and return its id."""
    pipeline_id = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()
    meta = {
        "id": pipeline_id,
        "name": name,
        "created_at": now,
        "updated_at": now,
    }
    dest = PIPELINES_DIR / f"{pipeline_id}.yaml"
    dest.write_text(yaml_content, encoding="utf-8")

    meta_path = PIPELINES_DIR / f"{pipeline_id}.meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return pipeline_id


def list_pipelines() -> list[dict[str, Any]]:
    """Return metadata for all saved pipelines, newest first."""
    results: list[dict[str, Any]] = []
    for meta_path in sorted(PIPELINES_DIR.glob("*.meta.json"), reverse=True):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                results.append(json.load(f))
        except (json.JSONDecodeError, PermissionError, OSError) as exc:
            logger.warning("Skipping corrupted pipeline meta %s: %s", meta_path, exc)
    return results


def load_pipeline(pipeline_id: str) -> dict[str, Any] | None:
    """Load a saved pipeline by id.  Returns dict with meta + yaml_content."""
    yaml_path = PIPELINES_DIR / f"{pipeline_id}.yaml"
    meta_path = PIPELINES_DIR / f"{pipeline_id}.meta.json"
    if not yaml_path.exists() or not meta_path.exists():
        return None
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    meta["yaml_content"] = yaml_path.read_text(encoding="utf-8")
    return meta
