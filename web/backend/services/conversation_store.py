"""Conversation persistence service.

Each conversation is stored as a JSON file under ``data/conversations/{id}.json``.
"""
from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import CONVERSATIONS_DIR

logger = logging.getLogger(__name__)

# Per-conversation locks to prevent concurrent writes to the same file
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _get_lock(conversation_id: str) -> threading.Lock:
    """Get or create a lock for a specific conversation."""
    with _locks_guard:
        if conversation_id not in _locks:
            _locks[conversation_id] = threading.Lock()
        return _locks[conversation_id]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _conversation_path(conversation_id: str) -> Path:
    return CONVERSATIONS_DIR / f"{conversation_id}.json"


def new_conversation_id() -> str:
    """Generate a unique conversation id."""
    return uuid.uuid4().hex[:12]


# ── CRUD ──────────────────────────────────────────────────────────────────────


def create_conversation(title: str = "New Conversation") -> dict[str, Any]:
    """Create a new conversation and persist it."""
    now = _now_iso()
    conversation: dict[str, Any] = {
        "id": uuid.uuid4().hex[:12],
        "title": title,
        "created_at": now,
        "updated_at": now,
        "config": {},
        "messages": [],
    }
    _save(conversation)
    return conversation


def get_conversation(conversation_id: str) -> dict[str, Any] | None:
    """Load a conversation by id, or return None."""
    path = _conversation_path(conversation_id)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_conversations() -> list[dict[str, Any]]:
    """Return lightweight summaries of all conversations, newest first."""
    results: list[dict[str, Any]] = []
    for path in sorted(CONVERSATIONS_DIR.glob("*.json"), reverse=True):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            results.append({
                "id": data["id"],
                "title": data.get("title", "Untitled"),
                "created_at": data["created_at"],
                "updated_at": data["updated_at"],
                "message_count": len(data.get("messages", [])),
            })
        except (json.JSONDecodeError, KeyError, PermissionError, OSError) as exc:
            logger.warning("Skipping corrupted conversation %s: %s", path, exc)
    return results


def add_message(
    conversation_id: str,
    role: str,
    content: str,
    token_usage: dict[str, int] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append a message and return the updated conversation."""
    lock = _get_lock(conversation_id)
    with lock:
        conversation = get_conversation(conversation_id)
        if conversation is None:
            # Create conversation with the requested id directly to avoid orphan files
            now = _now_iso()
            conversation = {
                "id": conversation_id,
                "title": "Auto-created",
                "created_at": now,
                "updated_at": now,
                "config": {},
                "messages": [],
            }
        message: dict[str, Any] = {
            "role": role,
            "content": content,
            "timestamp": _now_iso(),
        }
        if token_usage:
            message["token_usage"] = token_usage
        if metadata:
            message["metadata"] = metadata
        conversation["messages"].append(message)
        conversation["updated_at"] = _now_iso()
        _save(conversation)
        return conversation


def delete_conversation(conversation_id: str) -> bool:
    """Delete a conversation file.  Returns True if it existed."""
    path = _conversation_path(conversation_id)
    if path.exists():
        path.unlink()
        return True
    return False


def update_conversation(conversation_id: str, **fields: Any) -> dict[str, Any] | None:
    """Update top-level fields of a conversation (e.g. title).

    Returns the updated conversation or *None* if not found.
    """
    lock = _get_lock(conversation_id)
    with lock:
        conversation = get_conversation(conversation_id)
        if conversation is None:
            return None
        for key, value in fields.items():
            if key in ("title", "config"):
                conversation[key] = value
        conversation["updated_at"] = _now_iso()
        _save(conversation)
        return conversation


# ── Export helpers ────────────────────────────────────────────────────────────


def export_as_json(conversation_id: str) -> str | None:
    """Return the conversation as a pretty-printed JSON string."""
    conversation = get_conversation(conversation_id)
    if conversation is None:
        return None
    return json.dumps(conversation, ensure_ascii=False, indent=2)


def export_as_markdown(conversation_id: str) -> str | None:
    """Return the conversation formatted as Markdown."""
    conversation = get_conversation(conversation_id)
    if conversation is None:
        return None

    lines: list[str] = [
        f"# {conversation.get('title', 'Conversation')}",
        "",
        f"*Created: {conversation['created_at']}*  ",
        f"*Updated: {conversation['updated_at']}*",
        "",
        "---",
        "",
    ]
    for msg in conversation.get("messages", []):
        role = msg["role"].capitalize()
        lines.append(f"### {role}")
        lines.append("")
        lines.append(msg["content"])
        lines.append("")
        if msg.get("token_usage"):
            lines.append(f"*Tokens: {msg['token_usage']}*")
            lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


# ── Internal ──────────────────────────────────────────────────────────────────


def _save(conversation: dict[str, Any]) -> None:
    path = _conversation_path(conversation["id"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(conversation, f, ensure_ascii=False, indent=2)
