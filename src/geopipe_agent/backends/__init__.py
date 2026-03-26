"""Backend package — manager and all backend implementations."""

from __future__ import annotations

from geopipe_agent.backends.base import GeoBackend
from geopipe_agent.backends.native_python_backend import NativePythonBackend
from geopipe_agent.backends.gdal_cli import GdalCliBackend
from geopipe_agent.backends.qgis_process import QgisProcessBackend
from geopipe_agent.backends.gdal_python_backend import GdalPythonBackend
from geopipe_agent.backends.pyqgis_backend import PyQgisBackend
from geopipe_agent.errors import BackendNotAvailableError

_BACKEND_CLASSES = [NativePythonBackend, GdalCliBackend, QgisProcessBackend, GdalPythonBackend, PyQgisBackend]


class BackendManager:
    """Detect and manage available GIS backends."""

    def __init__(self) -> None:
        all_backends = [cls() for cls in _BACKEND_CLASSES]
        self.backends: list[GeoBackend] = [
            b for b in all_backends if b.is_available()
        ]

    def get(self, preferred: str | None = None) -> GeoBackend:
        """Get a backend by name, or the default (first available).

        Raises:
            BackendNotAvailableError: If no backend is available or the
                preferred backend is not found.
        """
        if preferred:
            for b in self.backends:
                if b.name() == preferred:
                    return b
            raise BackendNotAvailableError(
                f"Backend '{preferred}' is not available. "
                f"Available: {[b.name() for b in self.backends]}"
            )
        if not self.backends:
            raise BackendNotAvailableError(
                "No GIS backends available. Install geopandas+shapely (native_python), "
                "GDAL CLI tools (gdal_cli), GDAL Python bindings (gdal_python), "
                "qgis_process, or PyQGIS (pyqgis)."
            )
        return self.backends[0]


__all__ = [
    "GeoBackend",
    "NativePythonBackend",
    "GdalCliBackend",
    "QgisProcessBackend",
    "GdalPythonBackend",
    "PyQgisBackend",
    "BackendManager",
]
