"""GDAL CLI backend — large-file processing via ogr2ogr / gdal_translate CLI tools."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from typing import Any

from geopipe_agent.backends.base import GeoBackend


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

    # -- internal helpers -----------------------------------------------------

    @staticmethod
    def _write_tmp(gdf: Any, suffix: str = ".geojson") -> str:
        """Write a GeoDataFrame to a temp file and return its path."""
        fd, path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        gdf.to_file(path, driver="GeoJSON")
        return path

    @staticmethod
    def _read_result(path: str) -> Any:
        import geopandas as gpd

        return gpd.read_file(path)

    @staticmethod
    def _run(cmd: list[str]) -> subprocess.CompletedProcess:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"GDAL CLI command failed: {' '.join(cmd)}\n"
                f"stderr: {result.stderr}"
            )
        return result

    @staticmethod
    def _sanitize_identifier(name: str) -> str:
        """Sanitize a field/column name for use in SQL to prevent injection."""
        import re

        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise ValueError(
                f"Invalid identifier '{name}': only letters, digits, and underscores are allowed."
            )
        return name

    # -- public API -----------------------------------------------------------

    def buffer(self, gdf: Any, distance: float, **kwargs) -> Any:
        src = self._write_tmp(gdf)
        fd, dst = tempfile.mkstemp(suffix=".geojson")
        os.close(fd)
        # Validate distance is a real number
        safe_distance = float(distance)
        try:
            self._run([
                "ogr2ogr", "-f", "GeoJSON", dst, src,
                "-dialect", "sqlite",
                "-sql",
                f"SELECT ST_Buffer(geometry, {safe_distance}) AS geometry, * FROM \"{os.path.splitext(os.path.basename(src))[0]}\"",
            ])
            return self._read_result(dst)
        finally:
            os.unlink(src)
            if os.path.exists(dst):
                os.unlink(dst)

    def clip(self, input_gdf: Any, clip_gdf: Any, **kwargs) -> Any:
        src = self._write_tmp(input_gdf)
        clip_src = self._write_tmp(clip_gdf)
        fd, dst = tempfile.mkstemp(suffix=".geojson")
        os.close(fd)
        try:
            self._run([
                "ogr2ogr", "-f", "GeoJSON", dst, src,
                "-clipsrc", clip_src,
            ])
            return self._read_result(dst)
        finally:
            os.unlink(src)
            os.unlink(clip_src)
            if os.path.exists(dst):
                os.unlink(dst)

    def reproject(self, gdf: Any, target_crs: str, **kwargs) -> Any:
        src = self._write_tmp(gdf)
        fd, dst = tempfile.mkstemp(suffix=".geojson")
        os.close(fd)
        try:
            src_crs = str(gdf.crs) if gdf.crs else "EPSG:4326"
            self._run([
                "ogr2ogr", "-f", "GeoJSON", dst, src,
                "-s_srs", src_crs,
                "-t_srs", target_crs,
            ])
            return self._read_result(dst)
        finally:
            os.unlink(src)
            if os.path.exists(dst):
                os.unlink(dst)

    def dissolve(self, gdf: Any, by: str | None = None, **kwargs) -> Any:
        src = self._write_tmp(gdf)
        fd, dst = tempfile.mkstemp(suffix=".geojson")
        os.close(fd)
        layer_name = os.path.splitext(os.path.basename(src))[0]
        try:
            if by:
                safe_by = self._sanitize_identifier(by)
                sql = (
                    f"SELECT ST_Union(geometry) AS geometry, \"{safe_by}\" "
                    f"FROM \"{layer_name}\" GROUP BY \"{safe_by}\""
                )
            else:
                sql = f"SELECT ST_Union(geometry) AS geometry FROM \"{layer_name}\""
            self._run([
                "ogr2ogr", "-f", "GeoJSON", dst, src,
                "-dialect", "sqlite",
                "-sql", sql,
            ])
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
            self._run([
                "ogr2ogr", "-f", "GeoJSON", dst, src,
                "-simplify", str(tolerance),
            ])
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
        layer1 = os.path.splitext(os.path.basename(src1))[0]
        layer2 = os.path.splitext(os.path.basename(src2))[0]
        try:
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

            sql = (
                f"SELECT {func}(a.geometry, b.geometry) AS geometry "
                f"FROM \"{layer1}\" a, \"{layer2}\" b"
            )
            self._run([
                "ogr2ogr", "-f", "GeoJSON", dst, src1,
                "-dialect", "sqlite",
                "-sql", sql,
            ])
            return self._read_result(dst)
        finally:
            os.unlink(src1)
            os.unlink(src2)
            if os.path.exists(dst):
                os.unlink(dst)
