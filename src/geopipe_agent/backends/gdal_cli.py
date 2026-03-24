"""GDAL CLI backend — placeholder for large-file processing via CLI tools."""

from __future__ import annotations

import shutil
from typing import Any

from geopipe_agent.backends.base import GeoBackend


class GdalCliBackend(GeoBackend):
    """Backend using GDAL/OGR command-line tools (ogr2ogr, gdal_translate, etc.).

    Suitable for large datasets where CLI tools outperform Python bindings.
    This is a placeholder implementation — methods raise NotImplementedError.
    """

    def name(self) -> str:
        return "gdal_cli"

    def is_available(self) -> bool:
        return shutil.which("ogr2ogr") is not None

    def buffer(self, gdf: Any, distance: float, **kwargs) -> Any:
        raise NotImplementedError("GdalCliBackend.buffer is not yet implemented")

    def clip(self, input_gdf: Any, clip_gdf: Any, **kwargs) -> Any:
        raise NotImplementedError("GdalCliBackend.clip is not yet implemented")

    def reproject(self, gdf: Any, target_crs: str, **kwargs) -> Any:
        raise NotImplementedError("GdalCliBackend.reproject is not yet implemented")

    def dissolve(self, gdf: Any, by: str | None = None, **kwargs) -> Any:
        raise NotImplementedError("GdalCliBackend.dissolve is not yet implemented")

    def simplify(self, gdf: Any, tolerance: float, **kwargs) -> Any:
        raise NotImplementedError("GdalCliBackend.simplify is not yet implemented")

    def overlay(self, gdf1: Any, gdf2: Any, how: str = "intersection", **kwargs) -> Any:
        raise NotImplementedError("GdalCliBackend.overlay is not yet implemented")
