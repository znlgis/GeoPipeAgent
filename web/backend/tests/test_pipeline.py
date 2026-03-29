"""Tests for pipeline API endpoints."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns ok."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.anyio
async def test_list_steps(client: AsyncClient):
    """GET /api/pipeline/steps returns grouped steps."""
    response = await client.get("/api/pipeline/steps")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    # Should have at least one category
    assert len(data) > 0
    # Each category should be a list
    for category, steps in data.items():
        assert isinstance(steps, list)
        for step in steps:
            assert "name" in step
            assert "category" in step


@pytest.mark.anyio
async def test_get_step_detail(client: AsyncClient):
    """GET /api/pipeline/steps/{name} returns step detail."""
    # First get all steps to find a valid registry ID
    response = await client.get("/api/pipeline/steps")
    data = response.json()
    first_step = None
    for steps in data.values():
        if steps:
            first_step = steps[0]
            break

    assert first_step is not None
    # Use the 'id' field (registry ID like "io.read_vector"), not the display name
    step_id = first_step["id"]
    response = await client.get(f"/api/pipeline/steps/{step_id}")
    assert response.status_code == 200
    detail = response.json()
    assert detail["id"] == step_id


@pytest.mark.anyio
async def test_get_step_not_found(client: AsyncClient):
    """GET /api/pipeline/steps/{name} returns 404 for unknown step."""
    response = await client.get("/api/pipeline/steps/nonexistent.step")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_validate_pipeline_valid(client: AsyncClient):
    """POST /api/pipeline/validate accepts valid YAML."""
    yaml_content = """
pipeline:
  name: "test"
  steps:
    - id: read
      use: io.read_vector
      params:
        path: "test.shp"
"""
    response = await client.post(
        "/api/pipeline/validate",
        json={"yaml_content": yaml_content},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["errors"] == []


@pytest.mark.anyio
async def test_validate_pipeline_invalid(client: AsyncClient):
    """POST /api/pipeline/validate rejects invalid YAML."""
    response = await client.post(
        "/api/pipeline/validate",
        json={"yaml_content": "not valid yaml: [[["},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert len(data["errors"]) > 0


@pytest.mark.anyio
async def test_save_and_list_pipelines(client: AsyncClient):
    """POST /api/pipeline/save and GET /api/pipeline/list work together."""
    yaml_content = """
pipeline:
  name: "test-save"
  steps:
    - id: read
      use: io.read_vector
      params:
        path: "test.shp"
"""
    # Save
    response = await client.post(
        "/api/pipeline/save",
        json={"name": "test-pipeline", "yaml_content": yaml_content},
    )
    assert response.status_code == 200
    data = response.json()
    pipeline_id = data["id"]
    assert pipeline_id

    # List
    response = await client.get("/api/pipeline/list")
    assert response.status_code == 200
    pipelines = response.json()
    assert any(p["id"] == pipeline_id for p in pipelines)

    # Get
    response = await client.get(f"/api/pipeline/{pipeline_id}")
    assert response.status_code == 200
    detail = response.json()
    assert detail["name"] == "test-pipeline"
    assert "yaml_content" in detail


@pytest.mark.anyio
async def test_save_pipeline_version_increment(client: AsyncClient):
    """Saving with the same name increments version."""
    yaml_content = "pipeline:\n  name: versioned\n  steps: []\n"

    # Save first version
    response = await client.post(
        "/api/pipeline/save",
        json={"name": "versioned-pipe", "yaml_content": yaml_content},
    )
    assert response.status_code == 200
    first_id = response.json()["id"]

    # Save second version (same name)
    response = await client.post(
        "/api/pipeline/save",
        json={"name": "versioned-pipe", "yaml_content": yaml_content + "# v2"},
    )
    assert response.status_code == 200
    second_id = response.json()["id"]

    # Same pipeline ID, version incremented
    assert first_id == second_id
    detail = (await client.get(f"/api/pipeline/{second_id}")).json()
    assert detail.get("version", 1) == 2


@pytest.mark.anyio
async def test_save_pipeline_empty_name(client: AsyncClient):
    """Saving with empty name returns 400."""
    response = await client.post(
        "/api/pipeline/save",
        json={"name": "   ", "yaml_content": "pipeline: {}"},
    )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_delete_pipeline(client: AsyncClient):
    """DELETE /api/pipeline/{id} removes a saved pipeline."""
    yaml_content = "pipeline:\n  name: delete-me\n  steps: []\n"
    save_resp = await client.post(
        "/api/pipeline/save",
        json={"name": "delete-me", "yaml_content": yaml_content},
    )
    pipeline_id = save_resp.json()["id"]

    # Delete
    response = await client.delete(f"/api/pipeline/{pipeline_id}")
    assert response.status_code == 200

    # Verify it's gone
    response = await client.get(f"/api/pipeline/{pipeline_id}")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_delete_pipeline_not_found(client: AsyncClient):
    """DELETE nonexistent pipeline returns 404."""
    response = await client.delete("/api/pipeline/nonexistent")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_get_pipeline_not_found(client: AsyncClient):
    """GET nonexistent pipeline returns 404."""
    response = await client.get("/api/pipeline/nonexistent")
    assert response.status_code == 404
