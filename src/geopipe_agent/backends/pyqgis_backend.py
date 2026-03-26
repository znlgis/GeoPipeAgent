"""PyQGIS backend — vector operations via QGIS Python API (PyQGIS)."""

from __future__ import annotations

import os
import tempfile
from typing import Any

from geopipe_agent.backends.base import GeoBackend


class PyQgisBackend(GeoBackend):
    """Backend using PyQGIS for vector operations.

    Requires a QGIS installation with Python bindings available.
    Uses QgsVectorLayer and QGIS processing algorithms via the Python API.
    """

    def name(self) -> str:
        return "pyqgis"

    def is_available(self) -> bool:
        try:
            from qgis.core import QgsApplication  # noqa: F401
            return True
        except ImportError:
            return False

    # -- internal helpers -----------------------------------------------------

    @staticmethod
    def _ensure_qgis_app() -> Any:
        """Ensure QgsApplication is initialized (for standalone scripts)."""
        from qgis.core import QgsApplication
        app = QgsApplication.instance()
        if app is None:
            app = QgsApplication([], False)
            app.initQgis()
        return app

    @staticmethod
    def _gdf_to_layer(gdf: Any, name: str = "input") -> tuple[Any, str]:
        """Write a GeoDataFrame to a temp GeoJSON file and load as QgsVectorLayer."""
        from qgis.core import QgsVectorLayer

        fd, path = tempfile.mkstemp(suffix=".geojson")
        os.close(fd)
        gdf.to_file(path, driver="GeoJSON")
        layer = QgsVectorLayer(path, name, "ogr")
        if not layer.isValid():
            raise RuntimeError(f"Failed to load layer from {path}")
        return layer, path

    @staticmethod
    def _layer_to_gdf(path: str) -> Any:
        """Read a GeoJSON file into a GeoDataFrame."""
        import geopandas as gpd
        return gpd.read_file(path)

    @staticmethod
    def _make_tmp_path(suffix: str = ".geojson") -> str:
        fd, path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        return path

    @staticmethod
    def _cleanup(*paths: str) -> None:
        for p in paths:
            try:
                os.unlink(p)
            except OSError:
                pass

    @staticmethod
    def _run_processing(algorithm: str, params: dict) -> dict:
        """Run a QGIS processing algorithm and return the result dict."""
        import processing
        return processing.run(algorithm, params)

    # -- public API -----------------------------------------------------------

    def buffer(self, gdf: Any, distance: float, **kwargs) -> Any:
        self._ensure_qgis_app()
        layer, src_path = self._gdf_to_layer(gdf, "buffer_input")
        dst_path = self._make_tmp_path()

        cap_style_map = {"round": 0, "flat": 1, "square": 2}
        cap_style = cap_style_map.get(kwargs.get("cap_style", "round"), 0)

        try:
            self._run_processing("native:buffer", {
                "INPUT": layer,
                "DISTANCE": float(distance),
                "SEGMENTS": kwargs.get("segments", 5),
                "END_CAP_STYLE": cap_style,
                "JOIN_STYLE": 0,
                "MITER_LIMIT": 2,
                "DISSOLVE": False,
                "OUTPUT": dst_path,
            })
            return self._layer_to_gdf(dst_path)
        finally:
            self._cleanup(src_path, dst_path)

    def clip(self, input_gdf: Any, clip_gdf: Any, **kwargs) -> Any:
        self._ensure_qgis_app()
        input_layer, src_path = self._gdf_to_layer(input_gdf, "clip_input")
        clip_layer, clip_path = self._gdf_to_layer(clip_gdf, "clip_overlay")
        dst_path = self._make_tmp_path()

        try:
            self._run_processing("native:clip", {
                "INPUT": input_layer,
                "OVERLAY": clip_layer,
                "OUTPUT": dst_path,
            })
            return self._layer_to_gdf(dst_path)
        finally:
            self._cleanup(src_path, clip_path, dst_path)

    def reproject(self, gdf: Any, target_crs: str, **kwargs) -> Any:
        self._ensure_qgis_app()
        layer, src_path = self._gdf_to_layer(gdf, "reproject_input")
        dst_path = self._make_tmp_path()

        try:
            self._run_processing("native:reprojectlayer", {
                "INPUT": layer,
                "TARGET_CRS": target_crs,
                "OUTPUT": dst_path,
            })
            return self._layer_to_gdf(dst_path)
        finally:
            self._cleanup(src_path, dst_path)

    def dissolve(self, gdf: Any, by: str | None = None, **kwargs) -> Any:
        self._ensure_qgis_app()
        layer, src_path = self._gdf_to_layer(gdf, "dissolve_input")
        dst_path = self._make_tmp_path()

        params: dict[str, Any] = {
            "INPUT": layer,
            "OUTPUT": dst_path,
        }
        if by:
            params["FIELD"] = [by]

        try:
            self._run_processing("native:dissolve", params)
            return self._layer_to_gdf(dst_path)
        finally:
            self._cleanup(src_path, dst_path)

    def simplify(self, gdf: Any, tolerance: float, **kwargs) -> Any:
        self._ensure_qgis_app()
        layer, src_path = self._gdf_to_layer(gdf, "simplify_input")
        dst_path = self._make_tmp_path()

        try:
            self._run_processing("native:simplifygeometries", {
                "INPUT": layer,
                "METHOD": 0,  # Douglas-Peucker
                "TOLERANCE": float(tolerance),
                "OUTPUT": dst_path,
            })
            return self._layer_to_gdf(dst_path)
        finally:
            self._cleanup(src_path, dst_path)

    def overlay(self, gdf1: Any, gdf2: Any, how: str = "intersection", **kwargs) -> Any:
        self._ensure_qgis_app()
        algo_map = {
            "intersection": "native:intersection",
            "union": "native:union",
            "difference": "native:difference",
            "symmetric_difference": "native:symmetricaldifference",
        }
        algo = algo_map.get(how)
        if algo is None:
            raise ValueError(
                f"Unsupported overlay method '{how}'. "
                f"Supported: {list(algo_map.keys())}"
            )

        layer1, src1_path = self._gdf_to_layer(gdf1, "overlay_input")
        layer2, src2_path = self._gdf_to_layer(gdf2, "overlay_layer")
        dst_path = self._make_tmp_path()

        try:
            self._run_processing(algo, {
                "INPUT": layer1,
                "OVERLAY": layer2,
                "OUTPUT": dst_path,
            })
            return self._layer_to_gdf(dst_path)
        finally:
            self._cleanup(src1_path, src2_path, dst_path)
