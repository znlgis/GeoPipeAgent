"""Tests for skill management endpoints including external skill import."""
from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def _temp_skill_dirs(tmp_path: Path):
    """Redirect external skills directory to temp location."""
    external_skills_dir = tmp_path / "external_skills"
    external_skills_dir.mkdir()

    with mock.patch(
        "web.backend.routers.skill.EXTERNAL_SKILLS_DIR", external_skills_dir
    ), mock.patch(
        "web.backend.routers.skill._EXTERNAL_SKILLS_META",
        external_skills_dir / "_meta.json",
    ):
        # Clear skill cache before each test
        from web.backend.routers.skill import clear_skill_cache

        clear_skill_cache()
        yield


@pytest.fixture
def app():
    from web.backend.main import app

    return app


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Builtin modules ─────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_list_modules(client: AsyncClient):
    """Should list at least the 3 builtin modules."""
    resp = await client.get("/api/skill/modules")
    assert resp.status_code == 200
    data = resp.json()
    ids = [m["id"] for m in data["modules"]]
    assert "skill" in ids
    assert "steps-reference" in ids
    assert "pipeline-schema" in ids


@pytest.mark.anyio
async def test_get_module_content(client: AsyncClient):
    """Should return content for a builtin module."""
    resp = await client.get("/api/skill/content/skill")
    assert resp.status_code == 200
    data = resp.json()
    assert data["module"] == "skill"
    assert data["char_count"] > 0
    assert len(data["content"]) > 0


@pytest.mark.anyio
async def test_get_module_content_not_found(client: AsyncClient):
    """Should return 404 for unknown module."""
    resp = await client.get("/api/skill/content/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_get_all_content(client: AsyncClient):
    """Should return content for all modules."""
    resp = await client.get("/api/skill/content")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 3


@pytest.mark.anyio
async def test_clear_cache(client: AsyncClient):
    """Should clear cache without error."""
    resp = await client.post("/api/skill/clear-cache")
    assert resp.status_code == 200
    assert "message" in resp.json()


# ── External skill import ────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_import_skill_from_text(client: AsyncClient):
    """Should import a skill from text content."""
    resp = await client.post("/api/skill/import", json={
        "name": "My Custom Skill",
        "description": "A test skill module",
        "content": "# My Custom Skill\n\nThis is a test skill with useful content.",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "My Custom Skill"
    assert data["id"].startswith("ext-")
    assert data["char_count"] > 0
    assert data["token_estimate"] > 0

    # Verify it appears in modules list
    modules_resp = await client.get("/api/skill/modules")
    ids = [m["id"] for m in modules_resp.json()["modules"]]
    assert data["id"] in ids

    # Verify content is accessible
    content_resp = await client.get(f"/api/skill/content/{data['id']}")
    assert content_resp.status_code == 200
    assert "My Custom Skill" in content_resp.json()["content"]


@pytest.mark.anyio
async def test_import_skill_empty_content(client: AsyncClient):
    """Should reject import with empty content."""
    resp = await client.post("/api/skill/import", json={
        "name": "Empty Skill",
        "content": "   ",
    })
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_import_skill_empty_name(client: AsyncClient):
    """Should reject import with empty name."""
    resp = await client.post("/api/skill/import", json={
        "name": "  ",
        "content": "Some content here",
    })
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_delete_external_skill(client: AsyncClient):
    """Should delete an imported external skill."""
    # Import first
    import_resp = await client.post("/api/skill/import", json={
        "name": "To Delete",
        "content": "# Will be deleted\n\nContent to remove.",
    })
    module_id = import_resp.json()["id"]

    # Delete
    del_resp = await client.delete(f"/api/skill/external/{module_id}")
    assert del_resp.status_code == 200

    # Verify it's gone from modules list
    modules_resp = await client.get("/api/skill/modules")
    ids = [m["id"] for m in modules_resp.json()["modules"]]
    assert module_id not in ids

    # Verify content is no longer accessible
    content_resp = await client.get(f"/api/skill/content/{module_id}")
    assert content_resp.status_code == 404


@pytest.mark.anyio
async def test_delete_nonexistent_external_skill(client: AsyncClient):
    """Should return 404 when deleting non-existent external skill."""
    resp = await client.delete("/api/skill/external/ext-nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_update_external_skill(client: AsyncClient):
    """Should update an external skill's name, description, and content."""
    # Import
    import_resp = await client.post("/api/skill/import", json={
        "name": "Original Name",
        "description": "Original desc",
        "content": "# Original Content",
    })
    module_id = import_resp.json()["id"]

    # Update
    update_resp = await client.put(f"/api/skill/external/{module_id}", json={
        "name": "Updated Name",
        "description": "Updated desc",
        "content": "# Updated Content\n\nNew stuff.",
    })
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["name"] == "Updated Name"

    # Verify updated content
    content_resp = await client.get(f"/api/skill/content/{module_id}")
    assert "Updated Content" in content_resp.json()["content"]


@pytest.mark.anyio
async def test_update_nonexistent_external_skill(client: AsyncClient):
    """Should return 404 when updating a non-existent module."""
    resp = await client.put("/api/skill/external/ext-ghost", json={
        "name": "Ghost",
    })
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_module_source_field(client: AsyncClient):
    """External modules should have source='external', builtins 'builtin'."""
    # Import an external skill
    await client.post("/api/skill/import", json={
        "name": "Source Test",
        "content": "# Source test content",
    })

    modules_resp = await client.get("/api/skill/modules")
    modules = modules_resp.json()["modules"]

    builtin_mod = next(m for m in modules if m["id"] == "skill")
    assert builtin_mod["source"] == "builtin"

    external_mod = next(m for m in modules if m["source"] == "external")
    assert external_mod["source"] == "external"


@pytest.mark.anyio
async def test_import_multiple_skills(client: AsyncClient):
    """Should handle importing multiple external skills."""
    for i in range(3):
        resp = await client.post("/api/skill/import", json={
            "name": f"Skill {i}",
            "content": f"# Skill {i}\n\nContent for skill {i}.",
        })
        assert resp.status_code == 200

    modules_resp = await client.get("/api/skill/modules")
    external_count = sum(
        1 for m in modules_resp.json()["modules"] if m.get("source") == "external"
    )
    assert external_count == 3


@pytest.mark.anyio
async def test_all_content_includes_external(client: AsyncClient):
    """GET /api/skill/content should include external modules."""
    await client.post("/api/skill/import", json={
        "name": "All Content Test",
        "content": "# All content test\n\nShould appear in get all.",
    })

    resp = await client.get("/api/skill/content")
    assert resp.status_code == 200
    modules_in_response = [item["module"] for item in resp.json()]
    assert any(m.startswith("ext-") for m in modules_in_response)
