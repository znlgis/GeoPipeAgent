"""Step package — auto-imports all built-in step modules to trigger registration."""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

from geopipe_agent.steps.registry import (
    StepInfo,
    step,
    register,
    get,
    list_all,
    list_by_category,
    has,
    categories,
    reset,
)

_SKIP_MODULES = {"registry"}


def _iter_step_modules():
    """Yield fully-qualified module names for all built-in step sub-packages."""
    package_dir = str(Path(__file__).resolve().parent)
    prefix = "geopipe_agent.steps."
    for _importer, modname, ispkg in pkgutil.walk_packages(
        [package_dir], prefix=prefix
    ):
        short = modname[len(prefix):]
        # Skip non-step helper modules at the top level
        if short in _SKIP_MODULES:
            continue
        # Skip sub-package __init__ files (they're empty)
        if ispkg:
            continue
        yield modname


def load_builtin_steps() -> None:
    """Import all built-in step modules so they register with the step registry."""
    for modname in _iter_step_modules():
        importlib.import_module(modname)


def reload_builtin_steps() -> None:
    """Force-reload all step modules (useful for testing after registry reset)."""
    import sys

    for modname in _iter_step_modules():
        mod = sys.modules.get(modname)
        if mod is not None:
            importlib.reload(mod)
        else:
            importlib.import_module(modname)


__all__ = [
    "StepInfo",
    "step",
    "register",
    "get",
    "list_all",
    "list_by_category",
    "has",
    "categories",
    "reset",
    "load_builtin_steps",
    "reload_builtin_steps",
]
