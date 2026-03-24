"""QGIS Process backend — placeholder for qgis_process CLI integration."""

from __future__ import annotations

import shutil
from typing import Any

from geopipe_agent.backends.base import GeoBackend


class QgisProcessBackend(GeoBackend):
    """Backend using qgis_process CLI for advanced GIS algorithms.

    This is a placeholder implementation — methods raise NotImplementedError.
    """

    def name(self) -> str:
        return "qgis_process"

    def is_available(self) -> bool:
        return shutil.which("qgis_process") is not None

    def buffer(self, gdf: Any, distance: float, **kwargs) -> Any:
        raise NotImplementedError("QgisProcessBackend.buffer is not yet implemented")

    def clip(self, input_gdf: Any, clip_gdf: Any, **kwargs) -> Any:
        raise NotImplementedError("QgisProcessBackend.clip is not yet implemented")

    def reproject(self, gdf: Any, target_crs: str, **kwargs) -> Any:
        raise NotImplementedError("QgisProcessBackend.reproject is not yet implemented")

    def dissolve(self, gdf: Any, by: str | None = None, **kwargs) -> Any:
        raise NotImplementedError("QgisProcessBackend.dissolve is not yet implemented")

    def simplify(self, gdf: Any, tolerance: float, **kwargs) -> Any:
        raise NotImplementedError("QgisProcessBackend.simplify is not yet implemented")

    def overlay(self, gdf1: Any, gdf2: Any, how: str = "intersection", **kwargs) -> Any:
        raise NotImplementedError("QgisProcessBackend.overlay is not yet implemented")
