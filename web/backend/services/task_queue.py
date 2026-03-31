"""Async task queue service using Redis Queue (RQ).

Provides background pipeline execution with task status tracking.
Falls back to in-process execution when Redis is not available.
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Task time-to-live in Redis (seconds). Default: 24 hours.
TASK_TTL_SECONDS = int(os.environ.get("TASK_TTL_SECONDS", "86400"))

# In-memory task store fallback (when Redis is unavailable)
_task_store: dict[str, dict[str, Any]] = {}

# ── Redis connection (lazy) ──────────────────────────────────────────────────

_redis_conn = None
_rq_available = False


def _get_redis():
    """Lazy Redis connection. Returns None if Redis is unavailable."""
    global _redis_conn, _rq_available
    if _redis_conn is not None:
        return _redis_conn
    try:
        import redis
        conn = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        conn.ping()
        _redis_conn = conn
        _rq_available = True
        logger.info("Redis connected at %s", REDIS_URL)
        return conn
    except Exception as exc:
        logger.warning("Redis not available (%s), using in-memory task store", exc)
        _rq_available = False
        return None


def is_queue_available() -> bool:
    """Check if the task queue backend (Redis) is available."""
    _get_redis()
    return _rq_available


# ── Task lifecycle ───────────────────────────────────────────────────────────


def create_task(task_type: str, params: dict[str, Any]) -> str:
    """Create a new task and return its ID.

    The task starts in 'pending' status. Call ``start_task`` to begin execution.
    """
    task_id = uuid.uuid4().hex[:16]
    now = datetime.now(timezone.utc).isoformat()

    task = {
        "id": task_id,
        "type": task_type,
        "status": "pending",
        "params": params,
        "created_at": now,
        "updated_at": now,
        "progress": 0,
        "message": "",
        "result": None,
        "error": None,
    }

    r = _get_redis()
    if r is not None:
        r.set(f"task:{task_id}", json.dumps(task, default=str), ex=TASK_TTL_SECONDS)
    else:
        _task_store[task_id] = task

    return task_id


def update_task(
    task_id: str,
    *,
    status: str | None = None,
    progress: int | None = None,
    message: str | None = None,
    result: Any = None,
    error: str | None = None,
) -> dict[str, Any] | None:
    """Update task fields and return the updated task."""
    task = get_task(task_id)
    if task is None:
        return None

    if status is not None:
        task["status"] = status
    if progress is not None:
        task["progress"] = progress
    if message is not None:
        task["message"] = message
    if result is not None:
        task["result"] = result
    if error is not None:
        task["error"] = error
    task["updated_at"] = datetime.now(timezone.utc).isoformat()

    r = _get_redis()
    if r is not None:
        r.set(f"task:{task_id}", json.dumps(task, default=str), ex=TASK_TTL_SECONDS)
    else:
        _task_store[task_id] = task

    return task


def get_task(task_id: str) -> dict[str, Any] | None:
    """Retrieve task by ID."""
    r = _get_redis()
    if r is not None:
        raw = r.get(f"task:{task_id}")
        if raw is None:
            return None
        return json.loads(raw)
    return _task_store.get(task_id)


def list_tasks(limit: int = 50) -> list[dict[str, Any]]:
    """List recent tasks, newest first."""
    r = _get_redis()
    if r is not None:
        keys = r.keys("task:*")
        tasks = []
        for key in keys:
            raw = r.get(key)
            if raw:
                tasks.append(json.loads(raw))
        tasks.sort(key=lambda t: t.get("created_at", ""), reverse=True)
        return tasks[:limit]
    else:
        tasks = sorted(
            _task_store.values(),
            key=lambda t: t.get("created_at", ""),
            reverse=True,
        )
        return tasks[:limit]


def delete_task(task_id: str) -> bool:
    """Delete a task. Returns True if it existed."""
    r = _get_redis()
    if r is not None:
        return r.delete(f"task:{task_id}") > 0
    if task_id in _task_store:
        del _task_store[task_id]
        return True
    return False
