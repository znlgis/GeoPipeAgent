"""Task management router — submit, track, and manage background tasks."""
from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from ..models.schemas import PipelineExecuteRequest
from ..services import pipeline_service, task_queue

router = APIRouter(prefix="/api/task", tags=["task"])

# Polling interval (seconds) when streaming task progress via SSE
TASK_POLL_INTERVAL = 0.5


# ── Submit a pipeline execution as a background task ─────────────────────────


@router.post("/submit")
async def submit_task(req: PipelineExecuteRequest):
    """Submit a pipeline for background execution.

    Returns immediately with a task ID. Use ``GET /api/task/{task_id}``
    to poll status or ``GET /api/task/{task_id}/stream`` for SSE updates.
    """
    if not req.yaml_content.strip():
        raise HTTPException(status_code=400, detail="Pipeline YAML cannot be empty")

    task_id = task_queue.create_task(
        task_type="pipeline_execute",
        params={"yaml_content": req.yaml_content},
    )

    # Start background execution
    asyncio.create_task(_run_pipeline_task(task_id, req.yaml_content))

    return {
        "task_id": task_id,
        "status": "pending",
        "message": "Task submitted for background execution",
    }


async def _run_pipeline_task(task_id: str, yaml_content: str) -> None:
    """Execute pipeline in background, updating task status along the way."""
    task_queue.update_task(task_id, status="running", progress=0, message="Starting…")

    try:
        async for event in pipeline_service.execute_pipeline_stream(yaml_content):
            event_type = event.get("event", "")
            data = json.loads(event.get("data", "{}"))

            if event_type == "progress":
                task_queue.update_task(
                    task_id,
                    status="running",
                    progress=data.get("percent", 0),
                    message=data.get("message", ""),
                )
            elif event_type == "done":
                task_queue.update_task(
                    task_id,
                    status="completed",
                    progress=100,
                    message="Pipeline execution completed",
                    result=data.get("report"),
                )
            elif event_type == "error":
                task_queue.update_task(
                    task_id,
                    status="failed",
                    error=data.get("error", "Unknown error"),
                )
    except Exception as exc:
        task_queue.update_task(
            task_id,
            status="failed",
            error=str(exc),
        )


# ── Geodata extraction helpers ────────────────────────────────────────────────


def _looks_like_wkt(text: str) -> bool:
    """Check if a string looks like a WKT geometry.

    Performs a basic heuristic: the string must start with a known WKT
    type keyword followed by an opening parenthesis (with optional
    whitespace).  This is not a full validation—false positives are
    possible for unusual strings, but unlikely in pipeline results.
    """
    import re
    text = text.strip()
    wkt_pattern = re.compile(
        r"^(POINT|LINESTRING|POLYGON|MULTIPOINT|MULTILINESTRING|"
        r"MULTIPOLYGON|GEOMETRYCOLLECTION)\s*\(",
        re.IGNORECASE,
    )
    return bool(wkt_pattern.match(text))


def _extract_geodata(result: dict[str, Any]) -> dict[str, Any] | None:
    """Extract spatial data from a pipeline execution result.

    Searches common locations in the result structure for GeoJSON data.
    Returns a dict with 'type' ('geojson' or 'wkt'), 'data', and optional 'layers'.
    """
    layers: list[dict[str, Any]] = []

    # Direct GeoJSON result
    if isinstance(result, dict):
        if result.get("type") in ("FeatureCollection", "Feature", "Point", "LineString",
                                   "Polygon", "MultiPoint", "MultiLineString", "MultiPolygon",
                                   "GeometryCollection"):
            layers.append({"name": "result", "type": "geojson", "data": result})

        # Check nested locations
        for key in ("geojson", "geodata", "output", "geometry", "features"):
            nested = result.get(key)
            if isinstance(nested, dict) and nested.get("type") in (
                "FeatureCollection", "Feature", "Point", "LineString",
                "Polygon", "MultiPoint", "MultiLineString", "MultiPolygon",
                "GeometryCollection",
            ):
                layers.append({"name": key, "type": "geojson", "data": nested})

        # Check step results for spatial data
        steps = result.get("steps", [])
        if isinstance(steps, list):
            for step in steps:
                if not isinstance(step, dict):
                    continue
                step_output = step.get("output") or step.get("result")
                if isinstance(step_output, dict) and step_output.get("type") in (
                    "FeatureCollection", "Feature",
                ):
                    step_name = step.get("id", step.get("name", "step"))
                    layers.append({"name": step_name, "type": "geojson", "data": step_output})

                # Check for WKT strings in outputs
                for k, v in step.items():
                    if isinstance(v, str) and _looks_like_wkt(v):
                        step_name = step.get("id", step.get("name", "step"))
                        layers.append({"name": f"{step_name}_{k}", "type": "wkt", "data": v})

    if not layers:
        return None

    return {
        "layers": layers,
        "layer_count": len(layers),
    }


# ── Task status & management ─────────────────────────────────────────────────


@router.get("/list")
async def list_tasks(limit: int = 50):
    """List recent tasks."""
    return task_queue.list_tasks(limit=limit)


@router.get("/{task_id}")
async def get_task(task_id: str):
    """Get task status and result."""
    task = task_queue.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/{task_id}/geodata")
async def get_task_geodata(task_id: str):
    """Extract GeoJSON/WKT spatial data from a completed task's result.

    Searches the task result for spatial data in common locations and returns
    it in a format suitable for map visualization.
    """
    task = task_queue.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Task is not completed yet")

    result = task.get("result")
    if result is None:
        raise HTTPException(status_code=404, detail="No result data available")

    geodata = _extract_geodata(result)
    if geodata is None:
        raise HTTPException(status_code=404, detail="No spatial data found in task result")

    return geodata


@router.get("/{task_id}/stream")
async def stream_task(task_id: str):
    """Stream task progress via SSE until completion."""
    task = task_queue.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    async def _event_generator():
        last_progress = -1
        while True:
            current = task_queue.get_task(task_id)
            if current is None:
                yield {"event": "error", "data": json.dumps({"error": "Task not found"})}
                return

            # Only emit when progress changes
            if current.get("progress", 0) != last_progress:
                last_progress = current.get("progress", 0)
                yield {
                    "event": "progress",
                    "data": json.dumps({
                        "status": current["status"],
                        "progress": current["progress"],
                        "message": current.get("message", ""),
                    }),
                }

            status = current.get("status", "")
            if status == "completed":
                yield {
                    "event": "done",
                    "data": json.dumps({
                        "status": "completed",
                        "progress": 100,
                        "result": current.get("result"),
                    }),
                }
                return
            elif status == "failed":
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "status": "failed",
                        "error": current.get("error", "Unknown error"),
                    }),
                }
                return

            await asyncio.sleep(TASK_POLL_INTERVAL)

    return EventSourceResponse(_event_generator())


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """Delete a task record."""
    deleted = task_queue.delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted"}


@router.get("/queue/status")
async def queue_status():
    """Check task queue health status."""
    return {
        "queue_available": task_queue.is_queue_available(),
        "backend": "redis" if task_queue.is_queue_available() else "in-memory",
    }
