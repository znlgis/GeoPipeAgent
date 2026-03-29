"""Tests for LLM and conversation API endpoints."""
from __future__ import annotations

import json
from unittest import mock

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_get_llm_config(client: AsyncClient):
    """GET /api/llm/config returns masked config."""
    response = await client.get("/api/llm/config")
    assert response.status_code == 200
    data = response.json()
    assert "api_key" in data
    assert "model" in data
    assert "temperature" in data
    assert "max_tokens" in data


@pytest.mark.anyio
async def test_update_llm_config(client: AsyncClient):
    """PUT /api/llm/config updates configuration."""
    response = await client.put(
        "/api/llm/config",
        json={"model": "gpt-3.5-turbo", "temperature": 0.5},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "gpt-3.5-turbo"
    assert data["temperature"] == 0.5


@pytest.mark.anyio
async def test_update_llm_config_invalid_temperature(client: AsyncClient):
    """PUT /api/llm/config rejects invalid temperature."""
    response = await client.put(
        "/api/llm/config",
        json={"temperature": 5.0},
    )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_update_llm_config_invalid_max_tokens(client: AsyncClient):
    """PUT /api/llm/config rejects negative max_tokens."""
    response = await client.put(
        "/api/llm/config",
        json={"max_tokens": -1},
    )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_create_conversation(client: AsyncClient):
    """POST /api/llm/conversations creates a new conversation."""
    response = await client.post(
        "/api/llm/conversations",
        json={"title": "Test conversation"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test conversation"
    assert data["id"]
    assert data["messages"] == []


@pytest.mark.anyio
async def test_list_conversations(client: AsyncClient):
    """GET /api/llm/conversations lists conversations."""
    # Create one first
    await client.post(
        "/api/llm/conversations",
        json={"title": "List test"},
    )
    response = await client.get("/api/llm/conversations")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.anyio
async def test_get_conversation(client: AsyncClient):
    """GET /api/llm/conversations/{id} returns full conversation."""
    create_resp = await client.post(
        "/api/llm/conversations",
        json={"title": "Detail test"},
    )
    conv_id = create_resp.json()["id"]

    response = await client.get(f"/api/llm/conversations/{conv_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == conv_id
    assert data["title"] == "Detail test"


@pytest.mark.anyio
async def test_get_conversation_not_found(client: AsyncClient):
    """GET /api/llm/conversations/{id} returns 404 for unknown ID."""
    response = await client.get("/api/llm/conversations/nonexistent")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_delete_conversation(client: AsyncClient):
    """DELETE /api/llm/conversations/{id} removes a conversation."""
    create_resp = await client.post(
        "/api/llm/conversations",
        json={"title": "Delete me"},
    )
    conv_id = create_resp.json()["id"]

    response = await client.delete(f"/api/llm/conversations/{conv_id}")
    assert response.status_code == 200

    # Verify it's gone
    response = await client.get(f"/api/llm/conversations/{conv_id}")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_delete_conversation_not_found(client: AsyncClient):
    """DELETE nonexistent conversation returns 404."""
    response = await client.delete("/api/llm/conversations/nonexistent")
    assert response.status_code == 404
