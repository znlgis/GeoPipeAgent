"""Tests for the task queue API router."""
from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_task_queue_status(client):
    """Queue status endpoint returns backend type."""
    response = await client.get("/api/task/queue/status")
    assert response.status_code == 200
    data = response.json()
    assert "queue_available" in data
    assert "backend" in data
    assert data["backend"] in ("redis", "in-memory")


@pytest.mark.anyio
async def test_list_tasks_empty(client):
    """List tasks returns empty list when no tasks exist."""
    response = await client.get("/api/task/list")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.anyio
async def test_get_task_not_found(client):
    """Non-existent task returns 404."""
    response = await client.get("/api/task/nonexistent-task-id")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_delete_task_not_found(client):
    """Deleting non-existent task returns 404."""
    response = await client.delete("/api/task/nonexistent-task-id")
    assert response.status_code == 404
