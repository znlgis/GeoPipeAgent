"""Tests for the template API router."""
from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_list_templates(client):
    """Template list returns all pre-built templates."""
    response = await client.get("/api/template/list")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 7  # 7 cookbook templates
    # Each entry should have expected fields
    first = data[0]
    assert "id" in first
    assert "name_en" in first
    assert "name_zh" in first
    assert "category" in first
    assert "tags" in first
    assert "difficulty" in first
    assert "available" in first


@pytest.mark.anyio
async def test_get_template(client):
    """Get a specific template by ID returns YAML content."""
    response = await client.get("/api/template/buffer-analysis")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "buffer-analysis"
    assert "yaml_content" in data
    assert "pipeline:" in data["yaml_content"]
    assert "prompt_en" in data
    assert "prompt_zh" in data


@pytest.mark.anyio
async def test_get_template_not_found(client):
    """Non-existent template returns 404."""
    response = await client.get("/api/template/nonexistent-template")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_template_has_categories(client):
    """Templates span multiple categories."""
    response = await client.get("/api/template/list")
    data = response.json()
    categories = {tpl["category"] for tpl in data}
    assert len(categories) >= 3  # analysis, io, qc, vector


@pytest.mark.anyio
async def test_template_difficulty_levels(client):
    """Templates include multiple difficulty levels."""
    response = await client.get("/api/template/list")
    data = response.json()
    difficulties = {tpl["difficulty"] for tpl in data}
    assert "beginner" in difficulties
