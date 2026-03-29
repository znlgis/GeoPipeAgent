"""GDAL CLI backend — large-file processing via ogr2ogr / gdal_translate CLI tools."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import Any

from geopipe_agent.backends.base import GeoBackend, tmp_io, read_gdf


class GdalCliBackend(GeoBackend):
    """Backend using GDAL/OGR command-line tools (ogr2ogr, gdal_translate, etc.).

    Suitable for large datasets where CLI tools outperform Python bindings.
    Data is written to temporary GeoJSON files, processed via ogr2ogr/ogrinfo,
    and results are read back into GeoDataFrames.
    """

    def name(self) -> str:
        return "gdal_cli"

    def is_available(self) -> bool:
        return shutil.which("ogr2ogr") is not None

    # Default timeout for CLI commands (seconds)
    _TIMEOUT = 300

    @staticmethod
    def _run(cmd: list[str], timeout: int | None = None) -> subprocess.CompletedProcess:
        effective_timeout = timeout or GdalCliBackend._TIMEOUT
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=effective_timeout)
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(
                f"GDAL CLI command timed out after {effective_timeout}s: {' '.join(cmd)}"
            ) from e
        if result.returncode != 0:
            raise RuntimeError(
                f"GDAL CLI command failed: {' '.join(cmd)}\n"
                f"stderr: {result.stderr}"
            )
        return result

    @staticmethod
    def _sanitize_identifier(name: str) -> str:
        """Sanitize a field/column name for use in SQL to prevent injection."""
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise ValueError(
                f"Invalid identifier '{name}': only letters, digits, and underscores are allowed."
            )
        return name

    @staticmethod
    def _layer_name(path: str) -> str:
        """Extract the layer name from a file path (basename without extension)."""
        return os.path.splitext(os.path.basename(path))[0]

    # -- public API -----------------------------------------------------------

    def buffer(self, gdf: Any, distance: float, **kwargs) -> Any:
        safe_distance = float(distance)
        with tmp_io(gdf) as (src, dst):
            layer = self._layer_name(src)
            self._run([
                "ogr2ogr", "-f", "GeoJSON", dst, src,
                "-dialect", "sqlite",
                "-sql",
                f'SELECT ST_Buffer(geometry, {safe_distance}) AS geometry FROM "{layer}"',
            ])
            result = read_gdf(dst)
            # Restore non-geometry columns from original data
            for col in gdf.columns:
                if col != "geometry":
                    result[col] = gdf[col].values[:len(result)]
            return result

    def clip(self, input_gdf: Any, clip_gdf: Any, **kwargs) -> Any:
        with tmp_io(input_gdf, clip_gdf) as (src, clip_src, dst):
            self._run([
                "ogr2ogr", "-f", "GeoJSON", dst, src,
                "-clipsrc", clip_src,
            ])
            return read_gdf(dst)

    def reproject(self, gdf: Any, target_crs: str, **kwargs) -> Any:
        with tmp_io(gdf) as (src, dst):
            src_crs = str(gdf.crs) if gdf.crs else "EPSG:4326"
            self._run([
                "ogr2ogr", "-f", "GeoJSON", dst, src,
                "-s_srs", src_crs,
                "-t_srs", target_crs,
            ])
            return read_gdf(dst)

    def dissolve(self, gdf: Any, by: str | None = None, **kwargs) -> Any:
        with tmp_io(gdf) as (src, dst):
            layer = self._layer_name(src)
            if by:
                safe_by = self._sanitize_identifier(by)
                sql = (
                    f'SELECT ST_Union(geometry) AS geometry, "{safe_by}" '
                    f'FROM "{layer}" GROUP BY "{safe_by}"'
                )
            else:
                sql = f'SELECT ST_Union(geometry) AS geometry FROM "{layer}"'
            self._run([
                "ogr2ogr", "-f", "GeoJSON", dst, src,
                "-dialect", "sqlite",
                "-sql", sql,
            ])
            return read_gdf(dst)

    def simplify(self, gdf: Any, tolerance: float, **kwargs) -> Any:
        with tmp_io(gdf) as (src, dst):
            self._run([
                "ogr2ogr", "-f", "GeoJSON", dst, src,
                "-simplify", str(tolerance),
            ])
            return read_gdf(dst)

    def overlay(self, gdf1: Any, gdf2: Any, how: str = "intersection", **kwargs) -> Any:
        op_map = {
            "intersection": "ST_Intersection",
            "union": "ST_Union",
            "difference": "ST_Difference",
            "symmetric_difference": "ST_SymDifference",
        }
        func = op_map.get(how)
        if func is None:
            raise ValueError(
                f"Unsupported overlay method '{how}'. "
                f"Supported: {list(op_map.keys())}"
            )
        with tmp_io(gdf1, gdf2) as (src1, src2, dst):
            layer1 = self._layer_name(src1)
            layer2 = self._layer_name(src2)
            sql = (
                f'SELECT {func}(a.geometry, b.geometry) AS geometry '
                f'FROM "{layer1}" a, "{layer2}" b '
                f'WHERE ST_Intersects(a.geometry, b.geometry)'
            )
            self._run([
                "ogr2ogr", "-f", "GeoJSON", dst, src1,
                "-dialect", "sqlite",
                "-sql", sql,
            ])
            return read_gdf(dst)
