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


@pytest.mark.anyio
async def test_get_geodata_task_not_found(client):
    """Geodata for non-existent task returns 404."""
    response = await client.get("/api/task/nonexistent-id/geodata")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_get_geodata_not_completed(client):
    """Geodata for a non-completed task returns 400."""
    from web.backend.services import task_queue
    task_id = task_queue.create_task("test", {"yaml_content": "test"})
    response = await client.get(f"/api/task/{task_id}/geodata")
    assert response.status_code == 400
    task_queue.delete_task(task_id)


@pytest.mark.anyio
async def test_get_geodata_no_spatial_data(client):
    """Geodata for completed task with no spatial data returns 404."""
    from web.backend.services import task_queue
    task_id = task_queue.create_task("test", {"yaml_content": "test"})
    task_queue.update_task(task_id, status="completed", result={"message": "done"})
    response = await client.get(f"/api/task/{task_id}/geodata")
    assert response.status_code == 404
    task_queue.delete_task(task_id)


@pytest.mark.anyio
async def test_get_geodata_with_geojson(client):
    """Geodata for completed task with GeoJSON returns layers."""
    from web.backend.services import task_queue
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [0, 0]}, "properties": {}}
        ]
    }
    task_id = task_queue.create_task("test", {"yaml_content": "test"})
    task_queue.update_task(task_id, status="completed", result={"geojson": geojson})
    response = await client.get(f"/api/task/{task_id}/geodata")
    assert response.status_code == 200
    data = response.json()
    assert "layers" in data
    assert data["layer_count"] >= 1
    assert data["layers"][0]["type"] == "geojson"
    task_queue.delete_task(task_id)
