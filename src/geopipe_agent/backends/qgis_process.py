"""QGIS Process backend — qgis_process CLI integration."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from typing import Any

from geopipe_agent.backends.base import GeoBackend


class QgisProcessBackend(GeoBackend):
    """Backend using qgis_process CLI for advanced GIS algorithms.

    Data is written to temporary files, processed via ``qgis_process run``,
    and results are read back into GeoDataFrames.
    """

    def name(self) -> str:
        return "qgis_process"

    def is_available(self) -> bool:
        return shutil.which("qgis_process") is not None

    # -- internal helpers -----------------------------------------------------

    @staticmethod
    def _write_tmp(gdf: Any, suffix: str = ".geojson") -> str:
        fd, path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        gdf.to_file(path, driver="GeoJSON")
        return path

    @staticmethod
    def _read_result(path: str) -> Any:
        import geopandas as gpd

        return gpd.read_file(path)

    @staticmethod
    def _run_qgis(algorithm: str, params: dict) -> dict:
        """Run a qgis_process algorithm and return the parsed JSON output."""
        cmd = [
            "qgis_process", "run", algorithm,
            "--json",
        ]
        for key, value in params.items():
            cmd.extend([f"--{key}={value}"])

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"qgis_process failed for '{algorithm}':\n{result.stderr}"
            )
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {}

    # -- public API -----------------------------------------------------------

    def buffer(self, gdf: Any, distance: float, **kwargs) -> Any:
        src = self._write_tmp(gdf)
        fd, dst = tempfile.mkstemp(suffix=".geojson")
        os.close(fd)
        try:
            self._run_qgis("native:buffer", {
                "INPUT": src,
                "DISTANCE": distance,
                "SEGMENTS": kwargs.get("segments", 5),
                "END_CAP_STYLE": {"round": 0, "flat": 1, "square": 2}.get(
                    kwargs.get("cap_style", "round"), 0
                ),
                "JOIN_STYLE": 0,
                "MITER_LIMIT": 2,
                "DISSOLVE": "false",
                "OUTPUT": dst,
            })
            return self._read_result(dst)
        finally:
            os.unlink(src)
            if os.path.exists(dst):
                os.unlink(dst)

    def clip(self, input_gdf: Any, clip_gdf: Any, **kwargs) -> Any:
        src = self._write_tmp(input_gdf)
        overlay = self._write_tmp(clip_gdf)
        fd, dst = tempfile.mkstemp(suffix=".geojson")
        os.close(fd)
        try:
            self._run_qgis("native:clip", {
                "INPUT": src,
                "OVERLAY": overlay,
                "OUTPUT": dst,
            })
            return self._read_result(dst)
        finally:
            os.unlink(src)
            os.unlink(overlay)
            if os.path.exists(dst):
                os.unlink(dst)

    def reproject(self, gdf: Any, target_crs: str, **kwargs) -> Any:
        src = self._write_tmp(gdf)
        fd, dst = tempfile.mkstemp(suffix=".geojson")
        os.close(fd)
        try:
            self._run_qgis("native:reprojectlayer", {
                "INPUT": src,
                "TARGET_CRS": target_crs,
                "OUTPUT": dst,
            })
            return self._read_result(dst)
        finally:
            os.unlink(src)
            if os.path.exists(dst):
                os.unlink(dst)

    def dissolve(self, gdf: Any, by: str | None = None, **kwargs) -> Any:
        src = self._write_tmp(gdf)
        fd, dst = tempfile.mkstemp(suffix=".geojson")
        os.close(fd)
        try:
            params: dict[str, Any] = {
                "INPUT": src,
                "OUTPUT": dst,
            }
            if by:
                params["FIELD"] = by
            self._run_qgis("native:dissolve", params)
            return self._read_result(dst)
        finally:
            os.unlink(src)
            if os.path.exists(dst):
                os.unlink(dst)

    def simplify(self, gdf: Any, tolerance: float, **kwargs) -> Any:
        src = self._write_tmp(gdf)
        fd, dst = tempfile.mkstemp(suffix=".geojson")
        os.close(fd)
        try:
            self._run_qgis("native:simplifygeometries", {
                "INPUT": src,
                "METHOD": 0,  # Douglas-Peucker
                "TOLERANCE": tolerance,
                "OUTPUT": dst,
            })
            return self._read_result(dst)
        finally:
            os.unlink(src)
            if os.path.exists(dst):
                os.unlink(dst)

    def overlay(self, gdf1: Any, gdf2: Any, how: str = "intersection", **kwargs) -> Any:
        src1 = self._write_tmp(gdf1)
        src2 = self._write_tmp(gdf2)
        fd, dst = tempfile.mkstemp(suffix=".geojson")
        os.close(fd)
        try:
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
            self._run_qgis(algo, {
                "INPUT": src1,
                "OVERLAY": src2,
                "OUTPUT": dst,
            })
            return self._read_result(dst)
        finally:
            os.unlink(src1)
            os.unlink(src2)
            if os.path.exists(dst):
                os.unlink(dst)
