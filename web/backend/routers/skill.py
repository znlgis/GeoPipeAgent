"""Skill management router.

Provides endpoints to generate, view, and manage GeoPipeAgent skill documents
that enhance AI conversations with complete framework knowledge.
Supports importing external skill modules from text content or URLs.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from geopipe_agent.skillgen.generator import (
    generate_pipeline_schema_doc,
    generate_skill_file,
    generate_steps_reference,
    write_skill_files,
)

from ..config import BASE_DIR, EXTERNAL_SKILLS_DIR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/skill", tags=["skill"])

# Default output directory for generated skill files
SKILL_OUTPUT_DIR = BASE_DIR / "skills" / "geopipe-agent"

# External skills metadata file
_EXTERNAL_SKILLS_META = EXTERNAL_SKILLS_DIR / "_meta.json"


# ── Response / Request schemas ───────────────────────────────────────────────


class SkillModule(BaseModel):
    """Describes an available skill module."""

    id: str = Field(description="Module identifier")
    name: str = Field(description="Human-readable name")
    description: str = Field(description="What this module provides")
    token_estimate: int = Field(description="Estimated token cost when enabled")
    source: str = Field(default="builtin", description="Module source: builtin or external")


class SkillContentResponse(BaseModel):
    """Response with skill document content."""

    module: str = Field(description="Module identifier")
    content: str = Field(description="Markdown content of the skill document")
    char_count: int = Field(description="Character count")


class SkillGenerateResponse(BaseModel):
    """Response from skill file generation."""

    files: list[str] = Field(description="List of generated file paths")
    output_dir: str = Field(description="Output directory path")


class SkillModulesResponse(BaseModel):
    """Response listing all available skill modules."""

    modules: list[SkillModule] = Field(description="Available skill modules")


class SkillImportRequest(BaseModel):
    """Request body for importing a skill module from text content."""

    name: str = Field(description="Human-readable name for the skill module")
    description: str = Field(default="", description="Description of the skill module")
    content: str = Field(description="Markdown content of the skill module")


class SkillImportUrlRequest(BaseModel):
    """Request body for importing a skill module from a URL."""

    name: str = Field(description="Human-readable name for the skill module")
    description: str = Field(default="", description="Description of the skill module")
    url: str = Field(description="URL to fetch skill content from")


class SkillImportResponse(BaseModel):
    """Response from a skill import operation."""

    id: str = Field(description="Assigned module identifier")
    name: str = Field(description="Module name")
    token_estimate: int = Field(description="Estimated token cost")
    char_count: int = Field(description="Character count")


class SkillUpdateRequest(BaseModel):
    """Request body for updating an external skill module."""

    name: Optional[str] = Field(default=None, description="Updated name")
    description: Optional[str] = Field(default=None, description="Updated description")
    content: Optional[str] = Field(default=None, description="Updated content")


# ── Skill content cache ──────────────────────────────────────────────────────

_SKILL_CACHE: dict[str, str] = {}


def _get_skill_content(module: str) -> str:
    """Get the content for a skill module, using cache."""
    if module not in _SKILL_CACHE:
        if module == "skill":
            _SKILL_CACHE[module] = generate_skill_file()
        elif module == "steps-reference":
            _SKILL_CACHE[module] = generate_steps_reference()
        elif module == "pipeline-schema":
            _SKILL_CACHE[module] = generate_pipeline_schema_doc()
        else:
            # Try loading from external skills
            ext_content = _load_external_skill_content(module)
            if ext_content is not None:
                _SKILL_CACHE[module] = ext_content
            else:
                raise ValueError(f"Unknown skill module: {module}")
    return _SKILL_CACHE[module]


def clear_skill_cache() -> None:
    """Clear the skill content cache (useful after step registration changes)."""
    _SKILL_CACHE.clear()


def get_combined_skill_content(modules: list[str] | None = None) -> str:
    """Get combined skill content for the given modules.

    Args:
        modules: List of module IDs to include. If None, includes all builtin modules.

    Returns:
        Combined Markdown content from all requested modules.
    """
    if modules is None:
        modules = ["skill", "steps-reference", "pipeline-schema"]

    parts: list[str] = []
    for module_id in modules:
        try:
            content = _get_skill_content(module_id)
            parts.append(content)
        except ValueError:
            logger.warning("Unknown skill module requested: %s", module_id)
    return "\n\n---\n\n".join(parts)


# ── Available modules definition ─────────────────────────────────────────────

BUILTIN_MODULES: list[dict] = [
    {
        "id": "skill",
        "name": "Skill Overview",
        "description": "GeoPipeAgent framework overview, usage guide, key concepts, and step categories",
        "token_estimate": 500,
        "source": "builtin",
    },
    {
        "id": "steps-reference",
        "name": "Steps Reference",
        "description": "Complete reference of all pipeline steps with parameters, outputs, examples, and backends",
        "token_estimate": 3000,
        "source": "builtin",
    },
    {
        "id": "pipeline-schema",
        "name": "Pipeline Schema",
        "description": "YAML pipeline schema documentation including reference syntax, conditional execution, and error handling",
        "token_estimate": 600,
        "source": "builtin",
    },
]

# Keep backward-compatible alias
AVAILABLE_MODULES = BUILTIN_MODULES


# ── External skills persistence ──────────────────────────────────────────────

def _estimate_tokens(content: str) -> int:
    """Rough token estimate: ~4 chars per token for mixed CJK/English text."""
    return max(1, len(content) // 4)


def _sanitize_id(name: str) -> str:
    """Generate a filesystem-safe ASCII module ID from a name."""
    slug = re.sub(r"[^a-zA-Z0-9_-]", "_", name.strip())
    slug = re.sub(r"_+", "_", slug).strip("_")
    if not slug:
        slug = "external"
    return f"ext-{slug}"


def _load_external_skills_meta() -> list[dict]:
    """Load external skills metadata from disk."""
    if not _EXTERNAL_SKILLS_META.exists():
        return []
    try:
        with open(_EXTERNAL_SKILLS_META, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.warning("Failed to load external skills metadata")
        return []


def _save_external_skills_meta(meta: list[dict]) -> None:
    """Save external skills metadata to disk."""
    EXTERNAL_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    with open(_EXTERNAL_SKILLS_META, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def _load_external_skill_content(module_id: str) -> str | None:
    """Load content of a single external skill module from disk."""
    content_path = EXTERNAL_SKILLS_DIR / f"{module_id}.md"
    if not content_path.exists():
        return None
    try:
        return content_path.read_text(encoding="utf-8")
    except OSError:
        logger.warning("Failed to read external skill file: %s", content_path)
        return None


def _save_external_skill_content(module_id: str, content: str) -> None:
    """Save content of an external skill module to disk."""
    EXTERNAL_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    content_path = EXTERNAL_SKILLS_DIR / f"{module_id}.md"
    content_path.write_text(content, encoding="utf-8")


def _delete_external_skill_files(module_id: str) -> None:
    """Delete the content file for an external skill module."""
    content_path = EXTERNAL_SKILLS_DIR / f"{module_id}.md"
    if content_path.exists():
        content_path.unlink()


def _get_all_modules() -> list[dict]:
    """Get all modules (builtin + external)."""
    external = _load_external_skills_meta()
    return BUILTIN_MODULES + external


def _ensure_unique_id(base_id: str) -> str:
    """Ensure the module ID is unique across all modules."""
    existing_ids = {m["id"] for m in _get_all_modules()}
    if base_id not in existing_ids:
        return base_id
    # Append a suffix to make it unique (8 hex chars for ~4B combinations)
    suffix = uuid.uuid4().hex[:8]
    return f"{base_id}-{suffix}"


def _validate_url(url: str) -> None:
    """Validate that a URL is safe to fetch (SSRF prevention).

    Allows only http/https schemes and blocks private/internal IP addresses.

    Raises:
        HTTPException: If the URL is invalid or points to a private address.
    """
    import ipaddress
    import socket
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=400,
            detail="Only http and https URLs are supported",
        )

    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=400, detail="URL has no hostname")

    # Resolve hostname and check for private/loopback addresses
    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail=f"Cannot resolve hostname: {hostname}")

    for _family, _type, _proto, _canonname, sockaddr in addr_infos:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise HTTPException(
                status_code=400,
                detail="URLs pointing to private or internal addresses are not allowed",
            )


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/modules", response_model=SkillModulesResponse)
async def list_modules():
    """List all available skill modules with metadata (builtin + external)."""
    all_modules = _get_all_modules()
    modules = [SkillModule(**m) for m in all_modules]
    return SkillModulesResponse(modules=modules)


@router.get("/content/{module_id}", response_model=SkillContentResponse)
async def get_module_content(module_id: str):
    """Get the Markdown content of a specific skill module."""
    valid_ids = {m["id"] for m in _get_all_modules()}
    if module_id not in valid_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown skill module '{module_id}'. Valid modules: {', '.join(valid_ids)}",
        )
    content = _get_skill_content(module_id)
    return SkillContentResponse(
        module=module_id,
        content=content,
        char_count=len(content),
    )


@router.get("/content", response_model=list[SkillContentResponse])
async def get_all_content():
    """Get the content of all skill modules (builtin + external)."""
    results = []
    for m in _get_all_modules():
        try:
            content = _get_skill_content(m["id"])
            results.append(SkillContentResponse(
                module=m["id"],
                content=content,
                char_count=len(content),
            ))
        except ValueError:
            logger.warning("Skipping unavailable module: %s", m["id"])
    return results


@router.post("/generate", response_model=SkillGenerateResponse)
async def generate_skill_files(output_dir: str | None = None):
    """Generate skill files to disk.

    If output_dir is not specified, uses the default location under the project root.
    """
    target_dir = Path(output_dir) if output_dir else SKILL_OUTPUT_DIR
    try:
        files = write_skill_files(str(target_dir))
        # Clear cache so next request picks up fresh content
        clear_skill_cache()
        return SkillGenerateResponse(
            files=files,
            output_dir=str(target_dir),
        )
    except Exception as exc:
        logger.exception("Failed to generate skill files")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/clear-cache")
async def clear_cache():
    """Clear the skill content cache to force regeneration."""
    clear_skill_cache()
    return {"message": "Skill cache cleared"}


# ── External skill import endpoints ──────────────────────────────────────────


@router.post("/import", response_model=SkillImportResponse)
async def import_skill(req: SkillImportRequest):
    """Import an external skill module from text content."""
    content = req.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Skill content cannot be empty")
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="Skill name cannot be empty")

    base_id = _sanitize_id(req.name)
    module_id = _ensure_unique_id(base_id)
    token_est = _estimate_tokens(content)

    _save_external_skill_content(module_id, content)

    meta = _load_external_skills_meta()
    meta.append({
        "id": module_id,
        "name": req.name.strip(),
        "description": req.description.strip() or f"External skill: {req.name.strip()}",
        "token_estimate": token_est,
        "source": "external",
    })
    _save_external_skills_meta(meta)
    _SKILL_CACHE.pop(module_id, None)

    return SkillImportResponse(
        id=module_id,
        name=req.name.strip(),
        token_estimate=token_est,
        char_count=len(content),
    )


@router.post("/import-url", response_model=SkillImportResponse)
async def import_skill_from_url(req: SkillImportUrlRequest):
    """Import an external skill module by fetching content from a URL."""
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL cannot be empty")
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="Skill name cannot be empty")

    # Validate URL to prevent SSRF attacks
    _validate_url(url)

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)  # codql[py/full-ssrf] - URL is validated above
            response.raise_for_status()
            content = response.text.strip()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to fetch URL (HTTP {exc.response.status_code}): {url}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to fetch URL: {exc}",
        ) from exc

    if not content:
        raise HTTPException(status_code=400, detail="Fetched content is empty")

    base_id = _sanitize_id(req.name)
    module_id = _ensure_unique_id(base_id)
    token_est = _estimate_tokens(content)

    _save_external_skill_content(module_id, content)

    meta = _load_external_skills_meta()
    meta.append({
        "id": module_id,
        "name": req.name.strip(),
        "description": req.description.strip() or f"Imported from: {url}",
        "token_estimate": token_est,
        "source": "external",
    })
    _save_external_skills_meta(meta)
    _SKILL_CACHE.pop(module_id, None)

    return SkillImportResponse(
        id=module_id,
        name=req.name.strip(),
        token_estimate=token_est,
        char_count=len(content),
    )


@router.put("/external/{module_id}", response_model=SkillImportResponse)
async def update_external_skill(module_id: str, req: SkillUpdateRequest):
    """Update an existing external skill module."""
    meta = _load_external_skills_meta()
    idx = next((i for i, m in enumerate(meta) if m["id"] == module_id), None)
    if idx is None:
        raise HTTPException(
            status_code=404,
            detail=f"External skill module '{module_id}' not found",
        )

    entry = meta[idx]
    if req.name is not None:
        entry["name"] = req.name.strip()
    if req.description is not None:
        entry["description"] = req.description.strip()
    if req.content is not None:
        content = req.content.strip()
        if not content:
            raise HTTPException(status_code=400, detail="Skill content cannot be empty")
        _save_external_skill_content(module_id, content)
        entry["token_estimate"] = _estimate_tokens(content)

    meta[idx] = entry
    _save_external_skills_meta(meta)
    _SKILL_CACHE.pop(module_id, None)

    current_content = _load_external_skill_content(module_id) or ""

    return SkillImportResponse(
        id=module_id,
        name=entry["name"],
        token_estimate=entry["token_estimate"],
        char_count=len(current_content),
    )


@router.delete("/external/{module_id}")
async def delete_external_skill(module_id: str):
    """Delete an external skill module."""
    meta = _load_external_skills_meta()
    new_meta = [m for m in meta if m["id"] != module_id]
    if len(new_meta) == len(meta):
        raise HTTPException(
            status_code=404,
            detail=f"External skill module '{module_id}' not found",
        )

    _delete_external_skill_files(module_id)
    _SKILL_CACHE.pop(module_id, None)
    _save_external_skills_meta(new_meta)
    return {"message": f"External skill module '{module_id}' deleted"}
