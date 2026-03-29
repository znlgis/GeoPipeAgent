"""Shared test fixtures for backend API tests."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def _temp_data_dirs(tmp_path: Path):
    """Redirect all data directories to temp locations."""
    conversations_dir = tmp_path / "conversations"
    conversations_dir.mkdir()
    pipelines_dir = tmp_path / "pipelines"
    pipelines_dir.mkdir()
    llm_config_file = tmp_path / "llm_config.json"

    with mock.patch("web.backend.config.CONVERSATIONS_DIR", conversations_dir), \
         mock.patch("web.backend.config.PIPELINES_DIR", pipelines_dir), \
         mock.patch("web.backend.config.LLM_CONFIG_FILE", llm_config_file), \
         mock.patch("web.backend.config.DATA_DIR", tmp_path), \
         mock.patch("web.backend.services.conversation_store.CONVERSATIONS_DIR", conversations_dir), \
         mock.patch("web.backend.services.pipeline_service.PIPELINES_DIR", pipelines_dir):
        yield


@pytest.fixture
def app():
    """Create a fresh FastAPI app instance."""
    from web.backend.main import app
    return app


@pytest.fixture
async def client(app):
    """Async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
