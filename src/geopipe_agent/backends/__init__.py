"""Backend package — manager and all backend implementations."""

from __future__ import annotations

from geopipe_agent.backends.base import GeoBackend
from geopipe_agent.backends.gdal_python import GdalPythonBackend
from geopipe_agent.backends.gdal_cli import GdalCliBackend
from geopipe_agent.backends.qgis_process import QgisProcessBackend
from geopipe_agent.errors import BackendNotAvailableError


class BackendManager:
    """Detect and manage available GIS backends."""

    def __init__(self) -> None:
        self.backends: list[GeoBackend] = []
        self._detect_available()

    def _detect_available(self) -> None:
        for backend_cls in [GdalPythonBackend, GdalCliBackend, QgisProcessBackend]:
            backend = backend_cls()
            if backend.is_available():
                self.backends.append(backend)

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
                f"Available backends: {[b.name() for b in self.backends]}"
            )
        if not self.backends:
            raise BackendNotAvailableError(
                "No GIS backends available. Install geopandas+shapely (gdal_python), "
                "GDAL CLI tools (gdal_cli), or qgis_process."
            )
        return self.backends[0]

    def list_available(self) -> list[dict]:
        """List available backends as dicts (for CLI/reporting)."""
        return [{"name": b.name(), "available": True} for b in self.backends]


__all__ = [
    "GeoBackend",
    "GdalPythonBackend",
    "GdalCliBackend",
    "QgisProcessBackend",
    "BackendManager",
]
