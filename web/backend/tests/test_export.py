"""Tests for export API endpoints."""
from __future__ import annotations

import json

import pytest
from httpx import AsyncClient


@pytest.fixture
async def conversation_id(client: AsyncClient) -> str:
    """Create a conversation with messages for export tests."""
    # Create conversation
    create_resp = await client.post(
        "/api/llm/conversations",
        json={"title": "Export test"},
    )
    conv_id = create_resp.json()["id"]

    # Add messages directly via conversation store
    from web.backend.services import conversation_store

    conversation_store.add_message(conv_id, "user", "Hello")
    conversation_store.add_message(conv_id, "assistant", "Hi there!")
    return conv_id


@pytest.mark.anyio
async def test_export_json(client: AsyncClient, conversation_id: str):
    """GET /api/export/conversation/{id}?format=json returns JSON."""
    response = await client.get(
        f"/api/export/conversation/{conversation_id}?format=json"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    data = json.loads(response.text)
    assert data["id"] == conversation_id
    assert len(data["messages"]) == 2


@pytest.mark.anyio
async def test_export_markdown(client: AsyncClient, conversation_id: str):
    """GET /api/export/conversation/{id}?format=markdown returns Markdown."""
    response = await client.get(
        f"/api/export/conversation/{conversation_id}?format=markdown"
    )
    assert response.status_code == 200
    assert "text/markdown" in response.headers["content-type"]
    assert "Export test" in response.text
    assert "Hello" in response.text


@pytest.mark.anyio
async def test_export_messages_only(client: AsyncClient, conversation_id: str):
    """GET /api/export/conversation/{id}/messages returns only messages."""
    response = await client.get(
        f"/api/export/conversation/{conversation_id}/messages"
    )
    assert response.status_code == 200
    messages = json.loads(response.text)
    assert isinstance(messages, list)
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


@pytest.mark.anyio
async def test_export_not_found(client: AsyncClient):
    """Export nonexistent conversation returns 404."""
    response = await client.get("/api/export/conversation/nonexistent")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_batch_export(client: AsyncClient, conversation_id: str):
    """POST /api/export/batch returns a ZIP file."""
    response = await client.post(
        "/api/export/batch",
        json={"conversation_ids": [conversation_id], "format": "json"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert len(response.content) > 0


@pytest.mark.anyio
async def test_batch_export_markdown(client: AsyncClient, conversation_id: str):
    """POST /api/export/batch with markdown format returns ZIP."""
    response = await client.post(
        "/api/export/batch",
        json={"conversation_ids": [conversation_id], "format": "markdown"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
