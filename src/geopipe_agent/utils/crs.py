"""CRS utility helpers."""

from __future__ import annotations


def normalize_crs(crs_string: str) -> str:
    """Normalize a CRS string to a standard format.

    Args:
        crs_string: CRS string like 'EPSG:4326', 'epsg:4326', '4326'.

    Returns:
        Normalized CRS string like 'EPSG:4326'.
    """
    s = crs_string.strip().upper()
    if s.startswith("EPSG:"):
        return s
    # If it's just a number, assume EPSG
    try:
        code = int(s)
        return f"EPSG:{code}"
    except ValueError:
        return crs_string
