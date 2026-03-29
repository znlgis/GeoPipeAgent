"""LLM conversation router."""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from ..config import get_llm_config, mask_api_key, save_llm_config
from ..models.schemas import (
    ConversationDetail,
    ConversationSummary,
    CreateConversationRequest,
    LlmAnalyzeRequest,
    LlmChatRequest,
    LlmConfigResponse,
    LlmConfigUpdate,
    LlmGenerateRequest,
)
from ..services import conversation_store, llm_service
from ..services.conversation_store import new_conversation_id

router = APIRouter(prefix="/api/llm", tags=["llm"])


# ── Chat (SSE streaming) ─────────────────────────────────────────────────────


@router.post("/chat")
async def chat(req: LlmChatRequest):
    """Send a message and stream the response via SSE."""
    config = get_llm_config()
    conv_id = req.conversation_id or new_conversation_id()

    # Ensure conversation exists
    conversation = conversation_store.get_conversation(conv_id)
    if conversation is None:
        conversation = conversation_store.create_conversation(title=req.message[:60])
        conv_id = conversation["id"]

    # Persist user message
    conversation_store.add_message(conv_id, "user", req.message)

    # Build message history for the LLM
    conversation = conversation_store.get_conversation(conv_id)
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in (conversation or {}).get("messages", [])
    ]

    async def _event_generator():
        collected: list[str] = []
        async for chunk in llm_service.stream_chat(history, config, mode=req.mode):
            collected.append(chunk)
            yield {
                "event": "chunk",
                "data": json.dumps({"content": chunk, "conversation_id": conv_id}),
            }

        full_response = "".join(collected)
        conversation_store.add_message(conv_id, "assistant", full_response)
        yield {
            "event": "done",
            "data": json.dumps({
                "conversation_id": conv_id,
                "content": full_response,
            }),
        }

    return EventSourceResponse(_event_generator())


# ── Pipeline generation (SSE) ────────────────────────────────────────────────


@router.post("/generate-pipeline")
async def generate_pipeline(req: LlmGenerateRequest):
    """Generate a YAML pipeline from a natural-language description."""
    config = get_llm_config()
    conv_id = req.conversation_id or new_conversation_id()

    conversation = conversation_store.get_conversation(conv_id)
    if conversation is None:
        conversation = conversation_store.create_conversation(
            title=f"Generate: {req.description[:50]}"
        )
        conv_id = conversation["id"]

    conversation_store.add_message(conv_id, "user", req.description)

    async def _event_generator():
        collected: list[str] = []
        async for chunk in llm_service.generate_pipeline(req.description, config):
            collected.append(chunk)
            yield {
                "event": "chunk",
                "data": json.dumps({"content": chunk, "conversation_id": conv_id}),
            }
        full_response = "".join(collected)
        conversation_store.add_message(conv_id, "assistant", full_response)
        yield {
            "event": "done",
            "data": json.dumps({
                "conversation_id": conv_id,
                "content": full_response,
            }),
        }

    return EventSourceResponse(_event_generator())


# ── Result analysis (SSE) ────────────────────────────────────────────────────


@router.post("/analyze-result")
async def analyze_result(req: LlmAnalyzeRequest):
    """Analyze a pipeline execution report."""
    config = get_llm_config()
    conv_id = req.conversation_id or new_conversation_id()

    conversation = conversation_store.get_conversation(conv_id)
    if conversation is None:
        conversation = conversation_store.create_conversation(title="Result Analysis")
        conv_id = conversation["id"]

    report_summary = json.dumps(req.report, indent=2, default=str)
    conversation_store.add_message(
        conv_id, "user", f"Analyze this report:\n```json\n{report_summary}\n```"
    )

    async def _event_generator():
        collected: list[str] = []
        async for chunk in llm_service.analyze_result(req.report, config):
            collected.append(chunk)
            yield {
                "event": "chunk",
                "data": json.dumps({"content": chunk, "conversation_id": conv_id}),
            }
        full_response = "".join(collected)
        conversation_store.add_message(conv_id, "assistant", full_response)
        yield {
            "event": "done",
            "data": json.dumps({
                "conversation_id": conv_id,
                "content": full_response,
            }),
        }

    return EventSourceResponse(_event_generator())


# ── Conversation management ───────────────────────────────────────────────────


@router.get("/conversations", response_model=list[ConversationSummary])
async def list_conversations():
    """List all conversations."""
    return conversation_store.list_conversations()


@router.post("/conversations", response_model=ConversationDetail)
async def create_conversation(req: CreateConversationRequest):
    """Create a new empty conversation."""
    conversation = conversation_store.create_conversation(title=req.title)
    return conversation


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: str):
    """Get full conversation detail."""
    conversation = conversation_store.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation."""
    deleted = conversation_store.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"message": "Conversation deleted"}


# ── LLM configuration ────────────────────────────────────────────────────────


@router.get("/config", response_model=LlmConfigResponse)
async def get_config():
    """Get current LLM configuration (API key masked)."""
    config = get_llm_config()
    return LlmConfigResponse(
        api_key=mask_api_key(config.get("api_key", "")),
        base_url=config.get("base_url", ""),
        model=config.get("model", "gpt-4"),
        temperature=config.get("temperature", 0.7),
        max_tokens=config.get("max_tokens", 4096),
        system_prompt_extra=config.get("system_prompt_extra", ""),
    )


@router.put("/config", response_model=LlmConfigResponse)
async def update_config(req: LlmConfigUpdate):
    """Update LLM configuration."""
    # Validate temperature range
    if req.temperature is not None and not (0.0 <= req.temperature <= 2.0):
        raise HTTPException(
            status_code=400, detail="Temperature must be between 0.0 and 2.0"
        )
    # Validate max_tokens
    if req.max_tokens is not None and req.max_tokens < 1:
        raise HTTPException(
            status_code=400, detail="Max tokens must be a positive integer"
        )
    current = get_llm_config()
    update_data = req.model_dump(exclude_none=True)
    merged = {**current, **update_data}
    save_llm_config(merged)
    return LlmConfigResponse(
        api_key=mask_api_key(merged.get("api_key", "")),
        base_url=merged.get("base_url", ""),
        model=merged.get("model", "gpt-4"),
        temperature=merged.get("temperature", 0.7),
        max_tokens=merged.get("max_tokens", 4096),
        system_prompt_extra=merged.get("system_prompt_extra", ""),
    )
