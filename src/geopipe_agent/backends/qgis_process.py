"""QGIS Process backend — qgis_process CLI integration."""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any

from geopipe_agent.backends.base import GeoBackend, tmp_io, read_gdf


class QgisProcessBackend(GeoBackend):
    """Backend using qgis_process CLI for advanced GIS algorithms.

    Data is written to temporary files, processed via ``qgis_process run``,
    and results are read back into GeoDataFrames.
    """

    def name(self) -> str:
        return "qgis_process"

    def is_available(self) -> bool:
        return shutil.which("qgis_process") is not None

    @staticmethod
    def _run_qgis(algorithm: str, params: dict) -> dict:
        """Run a qgis_process algorithm and return the parsed JSON output."""
        cmd = ["qgis_process", "run", algorithm, "--json"]
        for key, value in params.items():
            cmd.append(f"--{key}={value}")

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
        with tmp_io(gdf) as (src, dst):
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
            return read_gdf(dst)

    def clip(self, input_gdf: Any, clip_gdf: Any, **kwargs) -> Any:
        with tmp_io(input_gdf, clip_gdf) as (src, overlay_src, dst):
            self._run_qgis("native:clip", {
                "INPUT": src,
                "OVERLAY": overlay_src,
                "OUTPUT": dst,
            })
            return read_gdf(dst)

    def reproject(self, gdf: Any, target_crs: str, **kwargs) -> Any:
        with tmp_io(gdf) as (src, dst):
            self._run_qgis("native:reprojectlayer", {
                "INPUT": src,
                "TARGET_CRS": target_crs,
                "OUTPUT": dst,
            })
            return read_gdf(dst)

    def dissolve(self, gdf: Any, by: str | None = None, **kwargs) -> Any:
        with tmp_io(gdf) as (src, dst):
            params: dict[str, Any] = {
                "INPUT": src,
                "OUTPUT": dst,
            }
            if by:
                params["FIELD"] = by
            self._run_qgis("native:dissolve", params)
            return read_gdf(dst)

    def simplify(self, gdf: Any, tolerance: float, **kwargs) -> Any:
        with tmp_io(gdf) as (src, dst):
            self._run_qgis("native:simplifygeometries", {
                "INPUT": src,
                "METHOD": 0,  # Douglas-Peucker
                "TOLERANCE": tolerance,
                "OUTPUT": dst,
            })
            return read_gdf(dst)

    def overlay(self, gdf1: Any, gdf2: Any, how: str = "intersection", **kwargs) -> Any:
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
        with tmp_io(gdf1, gdf2) as (src1, src2, dst):
            self._run_qgis(algo, {
                "INPUT": src1,
                "OVERLAY": src2,
                "OUTPUT": dst,
            })
            return read_gdf(dst)
