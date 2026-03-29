"""Pipeline CRUD and execution router."""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from ..models.schemas import (
    PipelineExecuteRequest,
    PipelineInfo,
    PipelineSaveRequest,
    PipelineValidateRequest,
    PipelineValidateResponse,
    StepParamSchema,
    StepSchema,
)
from ..services import pipeline_service

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


# ── Type mapping helper ───────────────────────────────────────────────────────


def _map_param_type(engine_type: str, enum_values: list[str] | None = None) -> str:
    """Map engine parameter types to frontend-friendly types."""
    if enum_values:
        return "enum"
    mapping = {"geodataframe": "layer"}
    return mapping.get(engine_type, engine_type)


def _map_step(raw: dict[str, Any]) -> dict[str, Any]:
    """Transform a raw step dict for frontend consumption."""
    mapped_params: dict[str, dict[str, Any]] = {}
    for param_name, param_info in raw.get("params", {}).items():
        if isinstance(param_info, dict):
            ptype = param_info.get("type", "string")
            enum_vals = param_info.get("enum")
            mapped_params[param_name] = {
                "type": _map_param_type(ptype, enum_vals),
                "required": param_info.get("required", False),
                "description": param_info.get("description", ""),
                "default": param_info.get("default"),
                "enum": enum_vals,
            }
        else:
            mapped_params[param_name] = {
                "type": str(param_info),
                "required": False,
                "description": "",
                "default": None,
                "enum": None,
            }

    return {
        "id": raw.get("id", ""),
        "name": raw.get("name", raw.get("id", "")),
        "category": raw.get("category", ""),
        "description": raw.get("description", ""),
        "params": mapped_params,
        "outputs": raw.get("outputs", {}),
        "backends": raw.get("backends", []),
        "examples": raw.get("examples", []),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/steps", response_model=dict[str, list[StepSchema]])
async def list_steps():
    """List all steps grouped by category."""
    all_steps = pipeline_service.get_all_steps()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for step in all_steps:
        mapped = _map_step(step)
        cat = mapped.get("category", "other") or "other"
        grouped.setdefault(cat, []).append(mapped)
    return grouped


@router.get("/steps/{name}", response_model=StepSchema)
async def get_step(name: str):
    """Get detailed info for a single step."""
    detail = pipeline_service.get_step_detail(name)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Step '{name}' not found")
    return _map_step(detail)


@router.post("/validate", response_model=PipelineValidateResponse)
async def validate_pipeline(req: PipelineValidateRequest):
    """Validate a YAML pipeline definition."""
    valid, errors = pipeline_service.validate_pipeline(req.yaml_content)
    return PipelineValidateResponse(valid=valid, errors=errors)


@router.post("/execute")
async def execute_pipeline(req: PipelineExecuteRequest):
    """Execute a pipeline and stream progress via SSE."""

    async def _event_generator():
        async for event in pipeline_service.execute_pipeline_stream(req.yaml_content):
            yield event

    return EventSourceResponse(_event_generator())


@router.post("/save")
async def save_pipeline(req: PipelineSaveRequest):
    """Save a pipeline YAML to disk."""
    pipeline_id = pipeline_service.save_pipeline(req.name, req.yaml_content)
    return {"id": pipeline_id, "message": "Pipeline saved"}


@router.get("/list", response_model=list[PipelineInfo])
async def list_pipelines():
    """List all saved pipelines."""
    return pipeline_service.list_pipelines()


@router.get("/{pipeline_id}")
async def get_pipeline(pipeline_id: str):
    """Load a saved pipeline by id."""
    result = pipeline_service.load_pipeline(pipeline_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return result


@router.delete("/{pipeline_id}")
async def delete_pipeline(pipeline_id: str):
    """Delete a saved pipeline by id."""
    deleted = pipeline_service.delete_pipeline(pipeline_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return {"message": "Pipeline deleted"}
