"""Abstract base class for GIS backends."""

from __future__ import annotations

import os
import tempfile
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any


class GeoBackend(ABC):
    """Abstract GIS processing backend.

    Each backend wraps a specific GIS engine (GDAL Python, GDAL CLI, QGIS, etc.)
    and provides a uniform interface for spatial operations.

    Backends that do not support a particular GIS operation inherit the default
    ``NotImplementedError`` provided by this base class.
    """

    @abstractmethod
    def name(self) -> str:
        """Return the backend identifier string."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check whether this backend's dependencies are installed."""
        ...

    # -- GIS operations with default "not supported" implementations ----------

    def buffer(self, gdf: Any, distance: float, **kwargs) -> Any:
        """Generate buffer polygons around geometries."""
        self._not_supported("buffer")

    def clip(self, input_gdf: Any, clip_gdf: Any, **kwargs) -> Any:
        """Clip input geometries by clip geometries."""
        self._not_supported("clip")

    def reproject(self, gdf: Any, target_crs: str, **kwargs) -> Any:
        """Reproject geometries to a different CRS."""
        self._not_supported("reproject")

    def dissolve(self, gdf: Any, by: str | None = None, **kwargs) -> Any:
        """Dissolve geometries, optionally grouped by a column."""
        self._not_supported("dissolve")

    def simplify(self, gdf: Any, tolerance: float, **kwargs) -> Any:
        """Simplify geometries."""
        self._not_supported("simplify")

    def overlay(self, gdf1: Any, gdf2: Any, how: str = "intersection", **kwargs) -> Any:
        """Perform overlay analysis between two GeoDataFrames."""
        self._not_supported("overlay")

    def _not_supported(self, operation: str) -> None:
        raise NotImplementedError(
            f"GIS operation '{operation}' is not supported by the {self.name()} backend. "
            "Use native_python, gdal_cli, or another GIS backend instead."
        )


# ---------------------------------------------------------------------------
# Shared utilities for CLI-based backends (GDAL CLI, QGIS Process)
# ---------------------------------------------------------------------------

def write_tmp_gdf(gdf: Any, suffix: str = ".geojson") -> str:
    """Write a GeoDataFrame to a temp file and return its path."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    gdf.to_file(path, driver="GeoJSON")
    return path


def make_tmp_path(suffix: str = ".geojson") -> str:
    """Create a temp file path for output and return it."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    return path


def read_gdf(path: str) -> Any:
    """Read a GeoDataFrame from a file."""
    import geopandas as gpd
    return gpd.read_file(path)


@contextmanager
def tmp_io(*gdfs: Any, suffix: str = ".geojson"):
    """Context manager for CLI backend operations.

    Writes input GeoDataFrames to temp files, creates an output temp file,
    yields (input_paths..., output_path), and cleans up all temp files on exit.

    Usage::

        with tmp_io(gdf1, gdf2) as (src1, src2, dst):
            run_command(src1, src2, dst)
            result = read_gdf(dst)
    """
    src_paths = [write_tmp_gdf(gdf, suffix) for gdf in gdfs]
    dst_path = make_tmp_path(suffix)
    try:
        yield (*src_paths, dst_path)
    finally:
        for p in [*src_paths, dst_path]:
            try:
                os.unlink(p)
            except OSError:
                pass
