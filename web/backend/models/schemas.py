"""Pydantic v2 models for GeoPipeAgent Web UI request/response types."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Step schemas ──────────────────────────────────────────────────────────────

class StepParamSchema(BaseModel):
    """Schema for a single step parameter."""

    type: str = Field(description="Parameter type (e.g. string, number, layer, enum)")
    required: bool = Field(default=False, description="Whether the parameter is required")
    description: str = Field(default="", description="Human-readable description")
    default: Any = Field(default=None, description="Default value if any")
    enum: Optional[list[str]] = Field(default=None, description="Allowed values for enum type")


class StepSchema(BaseModel):
    """Schema describing a pipeline step."""

    id: str = Field(description="Unique step identifier")
    name: str = Field(description="Human-readable step name")
    category: str = Field(default="", description="Step category")
    description: str = Field(default="", description="What this step does")
    params: dict[str, StepParamSchema] = Field(
        default_factory=dict, description="Parameter definitions"
    )
    outputs: dict[str, str] = Field(
        default_factory=dict, description="Output definitions"
    )
    backends: list[str] = Field(
        default_factory=list, description="Supported backend engines"
    )
    examples: list[dict[str, Any]] = Field(
        default_factory=list, description="Usage examples"
    )


# ── Pipeline schemas ──────────────────────────────────────────────────────────

class PipelineValidateRequest(BaseModel):
    """Request body for pipeline YAML validation."""

    yaml_content: str = Field(description="Raw YAML pipeline definition")


class PipelineValidateResponse(BaseModel):
    """Response body for pipeline validation."""

    valid: bool = Field(description="Whether the pipeline YAML is valid")
    errors: list[str] = Field(default_factory=list, description="Validation error messages")


class PipelineExecuteRequest(BaseModel):
    """Request body for pipeline execution."""

    yaml_content: str = Field(description="Raw YAML pipeline definition to execute")


class PipelineSaveRequest(BaseModel):
    """Request body for saving a pipeline."""

    name: str = Field(description="Name for the saved pipeline")
    yaml_content: str = Field(description="Raw YAML pipeline definition")


class PipelineInfo(BaseModel):
    """Summary of a saved pipeline."""

    id: str = Field(description="Pipeline identifier")
    name: str = Field(description="Pipeline name")
    version: int = Field(default=1, description="Pipeline version number")
    created_at: str = Field(description="ISO-8601 creation timestamp")
    updated_at: str = Field(description="ISO-8601 last-update timestamp")


# ── LLM / Chat schemas ───────────────────────────────────────────────────────

class LlmChatRequest(BaseModel):
    """Request body for LLM chat interaction."""

    conversation_id: Optional[str] = Field(
        default=None, description="Existing conversation to continue"
    )
    message: str = Field(description="User message content")
    mode: str = Field(default="chat", description="Interaction mode (chat, generate, analyze)")


class LlmGenerateRequest(BaseModel):
    """Request body for pipeline generation via LLM."""

    description: str = Field(description="Natural-language pipeline description")
    conversation_id: Optional[str] = Field(
        default=None, description="Existing conversation to continue"
    )


class LlmAnalyzeRequest(BaseModel):
    """Request body for execution result analysis."""

    report: dict[str, Any] = Field(description="Pipeline execution report to analyze")
    conversation_id: Optional[str] = Field(
        default=None, description="Existing conversation to continue"
    )


class LlmConfigUpdate(BaseModel):
    """Request body for updating LLM configuration (all fields optional)."""

    api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    base_url: Optional[str] = Field(default=None, description="API base URL")
    model: Optional[str] = Field(default=None, description="Model name")
    temperature: Optional[float] = Field(default=None, description="Sampling temperature")
    max_tokens: Optional[int] = Field(default=None, description="Max tokens per response")
    system_prompt_extra: Optional[str] = Field(
        default=None, description="Extra system prompt text"
    )


class LlmConfigResponse(BaseModel):
    """Response body for LLM configuration (API key masked)."""

    api_key: str = Field(description="Masked API key")
    base_url: str = Field(description="API base URL")
    model: str = Field(description="Model name")
    temperature: float = Field(description="Sampling temperature")
    max_tokens: int = Field(description="Max tokens per response")
    system_prompt_extra: str = Field(default="", description="Extra system prompt text")


# ── Conversation schemas ─────────────────────────────────────────────────────

class MessageSchema(BaseModel):
    """A single conversation message."""

    role: str = Field(description="Message role (user, assistant, system)")
    content: str = Field(description="Message content")
    timestamp: str = Field(description="ISO-8601 timestamp")
    token_usage: Optional[dict[str, int]] = Field(
        default=None, description="Token usage statistics"
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None, description="Additional metadata"
    )


class ConversationSummary(BaseModel):
    """Lightweight summary of a conversation."""

    id: str = Field(description="Conversation identifier")
    title: str = Field(description="Conversation title")
    created_at: str = Field(description="ISO-8601 creation timestamp")
    updated_at: str = Field(description="ISO-8601 last-update timestamp")
    message_count: int = Field(default=0, description="Number of messages")


class ConversationDetail(BaseModel):
    """Full conversation with messages."""

    id: str = Field(description="Conversation identifier")
    title: str = Field(description="Conversation title")
    created_at: str = Field(description="ISO-8601 creation timestamp")
    updated_at: str = Field(description="ISO-8601 last-update timestamp")
    config: dict[str, Any] = Field(default_factory=dict, description="Conversation config")
    messages: list[MessageSchema] = Field(
        default_factory=list, description="Ordered messages"
    )


# ── Export schemas ────────────────────────────────────────────────────────────

class CreateConversationRequest(BaseModel):
    """Request body for creating a new conversation."""

    title: str = Field(default="New Conversation", description="Conversation title")


class ExportRequest(BaseModel):
    """Request body for batch export."""

    conversation_ids: list[str] = Field(description="IDs of conversations to export")
    format: str = Field(default="json", description="Export format (json or markdown)")
