"""Abstract base class for GIS backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class GeoBackend(ABC):
    """Abstract GIS processing backend.

    Each backend wraps a specific GIS engine (GDAL Python, GDAL CLI, QGIS, etc.)
    and provides a uniform interface for spatial operations.
    """

    @abstractmethod
    def name(self) -> str:
        """Return the backend identifier string."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check whether this backend's dependencies are installed."""
        ...

    @abstractmethod
    def buffer(self, gdf: Any, distance: float, **kwargs) -> Any:
        """Generate buffer polygons around geometries."""
        ...

    @abstractmethod
    def clip(self, input_gdf: Any, clip_gdf: Any, **kwargs) -> Any:
        """Clip input geometries by clip geometries."""
        ...

    @abstractmethod
    def reproject(self, gdf: Any, target_crs: str, **kwargs) -> Any:
        """Reproject geometries to a different CRS."""
        ...

    @abstractmethod
    def dissolve(self, gdf: Any, by: str | None = None, **kwargs) -> Any:
        """Dissolve geometries, optionally grouped by a column."""
        ...

    @abstractmethod
    def simplify(self, gdf: Any, tolerance: float, **kwargs) -> Any:
        """Simplify geometries."""
        ...

    @abstractmethod
    def overlay(self, gdf1: Any, gdf2: Any, how: str = "intersection", **kwargs) -> Any:
        """Perform overlay analysis between two GeoDataFrames."""
        ...
