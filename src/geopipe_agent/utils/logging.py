"""Structured logging utilities for GeoPipeAgent."""

from __future__ import annotations

import json
import logging
import sys


class JsonFormatter(logging.Formatter):
    """JSON log formatter for machine-readable log output."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = str(record.exc_info[1])
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(level: str = "INFO", json_format: bool = False) -> None:
    """Configure logging for GeoPipeAgent.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR).
        json_format: If True, use JSON log format.
    """
    logger = logging.getLogger("geopipe_agent")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        if json_format:
            handler.setFormatter(JsonFormatter())
        else:
            handler.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
            )
        logger.addHandler(handler)
