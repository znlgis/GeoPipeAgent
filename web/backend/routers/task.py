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

            await asyncio.sleep(0.5)

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
