"""Skill management router.

Provides endpoints to generate, view, and manage GeoPipeAgent skill documents
that enhance AI conversations with complete framework knowledge.
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from geopipe_agent.skillgen.generator import (
    generate_pipeline_schema_doc,
    generate_skill_file,
    generate_steps_reference,
    write_skill_files,
)

from ..config import BASE_DIR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/skill", tags=["skill"])

# Default output directory for generated skill files
SKILL_OUTPUT_DIR = BASE_DIR / "skills" / "geopipe-agent"


# ── Response schemas ─────────────────────────────────────────────────────────


class SkillModule(BaseModel):
    """Describes an available skill module."""

    id: str = Field(description="Module identifier")
    name: str = Field(description="Human-readable name")
    description: str = Field(description="What this module provides")
    token_estimate: int = Field(description="Estimated token cost when enabled")


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
            raise ValueError(f"Unknown skill module: {module}")
    return _SKILL_CACHE[module]


def clear_skill_cache() -> None:
    """Clear the skill content cache (useful after step registration changes)."""
    _SKILL_CACHE.clear()


def get_combined_skill_content(modules: list[str] | None = None) -> str:
    """Get combined skill content for the given modules.

    Args:
        modules: List of module IDs to include. If None, includes all modules.

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

AVAILABLE_MODULES: list[dict] = [
    {
        "id": "skill",
        "name": "Skill Overview",
        "description": "GeoPipeAgent framework overview, usage guide, key concepts, and step categories",
        "token_estimate": 500,
    },
    {
        "id": "steps-reference",
        "name": "Steps Reference",
        "description": "Complete reference of all pipeline steps with parameters, outputs, examples, and backends",
        "token_estimate": 3000,
    },
    {
        "id": "pipeline-schema",
        "name": "Pipeline Schema",
        "description": "YAML pipeline schema documentation including reference syntax, conditional execution, and error handling",
        "token_estimate": 600,
    },
]


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/modules", response_model=SkillModulesResponse)
async def list_modules():
    """List all available skill modules with metadata."""
    modules = [SkillModule(**m) for m in AVAILABLE_MODULES]
    return SkillModulesResponse(modules=modules)


@router.get("/content/{module_id}", response_model=SkillContentResponse)
async def get_module_content(module_id: str):
    """Get the Markdown content of a specific skill module."""
    valid_ids = {m["id"] for m in AVAILABLE_MODULES}
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
    """Get the content of all skill modules."""
    results = []
    for m in AVAILABLE_MODULES:
        content = _get_skill_content(m["id"])
        results.append(SkillContentResponse(
            module=m["id"],
            content=content,
            char_count=len(content),
        ))
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
