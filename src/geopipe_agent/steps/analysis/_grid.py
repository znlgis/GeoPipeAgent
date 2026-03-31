"""Shared grid/bounds utilities for analysis step implementations."""

from __future__ import annotations

from typing import Any


def normalize_bounds(
    total_bounds: tuple[float, float, float, float],
) -> tuple[float, float, float, float, float, float]:
    """Ensure bounding box has non-zero extent in both axes.

    Returns ``(minx, miny, maxx, maxy, dx, dy)`` with guaranteed ``dx > 0``
    and ``dy > 0``.  When an axis has zero extent a padding of 0.5 is applied.
    """
    minx, miny, maxx, maxy = total_bounds
    dx = maxx - minx
    dy = maxy - miny

    if dx == 0:
        dx = 1.0
        minx -= 0.5
        maxx += 0.5
    if dy == 0:
        dy = 1.0
        miny -= 0.5
        maxy += 0.5

    return minx, miny, maxx, maxy, dx, dy


def compute_grid_dims(
    resolution: int, dx: float, dy: float
) -> tuple[int, int]:
    """Compute (width, height) from *resolution* and extent ratios."""
    width = resolution
    height = max(1, int(resolution * dy / dx))
    return width, height
