"""Export router for conversations."""
from __future__ import annotations

import io
import json
import zipfile
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from ..models.schemas import ExportRequest
from ..services import conversation_store

router = APIRouter(prefix="/api/export", tags=["export"])


# ── Single conversation export ────────────────────────────────────────────────


@router.get("/conversation/{conversation_id}")
async def export_conversation(
    conversation_id: str,
    format: str = Query(default="json", description="Export format: json or markdown"),
):
    """Export a conversation as JSON or Markdown."""
    if format == "markdown":
        content = conversation_store.export_as_markdown(conversation_id)
        if content is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return Response(
            content=content,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="{conversation_id}.md"'
            },
        )

    content = conversation_store.export_as_json(conversation_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{conversation_id}.json"'
        },
    )


# ── Messages-only export ─────────────────────────────────────────────────────


@router.get("/conversation/{conversation_id}/messages")
async def export_messages(conversation_id: str):
    """Export only the messages of a conversation as JSON."""
    conversation = conversation_store.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = conversation.get("messages", [])
    payload = json.dumps(messages, ensure_ascii=False, indent=2)
    return Response(
        content=payload,
        media_type="application/json",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{conversation_id}_messages.json"'
            )
        },
    )


# ── Batch export (ZIP) ───────────────────────────────────────────────────────


@router.post("/batch")
async def batch_export(req: ExportRequest):
    """Export multiple conversations as a ZIP archive."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for cid in req.conversation_ids:
            if req.format == "markdown":
                content = conversation_store.export_as_markdown(cid)
                ext = "md"
            else:
                content = conversation_store.export_as_json(cid)
                ext = "json"

            if content is not None:
                zf.writestr(f"{cid}.{ext}", content)

    buf.seek(0)
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="conversations_export.zip"'
        },
    )
