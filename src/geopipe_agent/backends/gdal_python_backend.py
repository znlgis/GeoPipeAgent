"""GDAL Python backend — vector operations via GDAL/OGR Python bindings."""

from __future__ import annotations

import os
import tempfile
from typing import Any

from geopipe_agent.backends.base import GeoBackend


class GdalPythonBackend(GeoBackend):
    """Backend using GDAL/OGR Python bindings for vector operations."""

    def name(self) -> str:
        return "gdal_python"

    def is_available(self) -> bool:
        try:
            from osgeo import ogr, osr, gdal  # noqa: F401
            return True
        except ImportError:
            return False

    # -- internal helpers -----------------------------------------------------

    @staticmethod
    def _gdf_to_ogr_ds(gdf: Any) -> Any:
        """Write a GeoDataFrame to a temporary GeoJSON file and open as OGR DataSource."""
        from osgeo import ogr
        fd, path = tempfile.mkstemp(suffix=".geojson")
        os.close(fd)
        gdf.to_file(path, driver="GeoJSON")
        ds = ogr.Open(path, 0)
        # attach path so caller can clean up
        ds._tmp_path = path  # type: ignore[attr-defined]
        return ds

    @staticmethod
    def _ogr_ds_to_gdf(path: str) -> Any:
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

    # -- public API -----------------------------------------------------------

    def buffer(self, gdf: Any, distance: float, **kwargs) -> Any:
        from osgeo import ogr, osr

        src_ds = self._gdf_to_ogr_ds(gdf)
        src_tmp = getattr(src_ds, "_tmp_path", None)
        src_layer = src_ds.GetLayer()

        dst_path = self._make_tmp_path()
        drv = ogr.GetDriverByName("GeoJSON")
        dst_ds = drv.CreateDataSource(dst_path)

        srs = src_layer.GetSpatialRef()
        dst_layer = dst_ds.CreateLayer("buffered", srs=srs, geom_type=ogr.wkbPolygon)

        # Copy field definitions
        layer_defn = src_layer.GetLayerDefn()
        for i in range(layer_defn.GetFieldCount()):
            dst_layer.CreateField(layer_defn.GetFieldDefn(i))

        for feat in src_layer:
            geom = feat.GetGeometryRef()
            if geom is not None:
                buffered = geom.Buffer(float(distance))
                out_feat = ogr.Feature(dst_layer.GetLayerDefn())
                out_feat.SetGeometry(buffered)
                for i in range(layer_defn.GetFieldCount()):
                    out_feat.SetField(i, feat.GetField(i))
                dst_layer.CreateFeature(out_feat)

        dst_ds = None  # flush
        src_ds = None

        result = self._ogr_ds_to_gdf(dst_path)
        paths_to_clean = [dst_path]
        if src_tmp:
            paths_to_clean.append(src_tmp)
        self._cleanup(*paths_to_clean)
        return result

    def clip(self, input_gdf: Any, clip_gdf: Any, **kwargs) -> Any:
        from osgeo import ogr

        src_ds = self._gdf_to_ogr_ds(input_gdf)
        clip_ds = self._gdf_to_ogr_ds(clip_gdf)
        src_layer = src_ds.GetLayer()
        clip_layer = clip_ds.GetLayer()

        dst_path = self._make_tmp_path()
        drv = ogr.GetDriverByName("GeoJSON")
        dst_ds = drv.CreateDataSource(dst_path)

        srs = src_layer.GetSpatialRef()
        dst_layer = dst_ds.CreateLayer("clipped", srs=srs, geom_type=src_layer.GetGeomType())

        layer_defn = src_layer.GetLayerDefn()
        for i in range(layer_defn.GetFieldCount()):
            dst_layer.CreateField(layer_defn.GetFieldDefn(i))

        src_layer.Clip(clip_layer, dst_layer)

        dst_ds = None
        src_tmp = getattr(src_ds, "_tmp_path", None)
        clip_tmp = getattr(clip_ds, "_tmp_path", None)
        src_ds = None
        clip_ds = None

        result = self._ogr_ds_to_gdf(dst_path)
        paths_to_clean = [dst_path]
        if src_tmp:
            paths_to_clean.append(src_tmp)
        if clip_tmp:
            paths_to_clean.append(clip_tmp)
        self._cleanup(*paths_to_clean)
        return result

    def reproject(self, gdf: Any, target_crs: str, **kwargs) -> Any:
        from osgeo import ogr, osr

        src_ds = self._gdf_to_ogr_ds(gdf)
        src_layer = src_ds.GetLayer()

        # Build coordinate transformation
        src_srs = src_layer.GetSpatialRef()
        if src_srs is None:
            src_srs = osr.SpatialReference()
            src_srs.SetFromUserInput("EPSG:4326")

        dst_srs = osr.SpatialReference()
        dst_srs.SetFromUserInput(target_crs)

        transform = osr.CoordinateTransformation(src_srs, dst_srs)

        dst_path = self._make_tmp_path()
        drv = ogr.GetDriverByName("GeoJSON")
        dst_ds = drv.CreateDataSource(dst_path)
        dst_layer = dst_ds.CreateLayer("reprojected", srs=dst_srs, geom_type=src_layer.GetGeomType())

        layer_defn = src_layer.GetLayerDefn()
        for i in range(layer_defn.GetFieldCount()):
            dst_layer.CreateField(layer_defn.GetFieldDefn(i))

        for feat in src_layer:
            geom = feat.GetGeometryRef()
            if geom is not None:
                geom.Transform(transform)
            out_feat = ogr.Feature(dst_layer.GetLayerDefn())
            out_feat.SetGeometry(geom)
            for i in range(layer_defn.GetFieldCount()):
                out_feat.SetField(i, feat.GetField(i))
            dst_layer.CreateFeature(out_feat)

        dst_ds = None
        src_tmp = getattr(src_ds, "_tmp_path", None)
        src_ds = None

        result = self._ogr_ds_to_gdf(dst_path)
        paths_to_clean = [dst_path]
        if src_tmp:
            paths_to_clean.append(src_tmp)
        self._cleanup(*paths_to_clean)
        return result

    def dissolve(self, gdf: Any, by: str | None = None, **kwargs) -> Any:
        from osgeo import ogr

        src_ds = self._gdf_to_ogr_ds(gdf)
        src_layer = src_ds.GetLayer()

        dst_path = self._make_tmp_path()
        drv = ogr.GetDriverByName("GeoJSON")
        dst_ds = drv.CreateDataSource(dst_path)

        srs = src_layer.GetSpatialRef()
        dst_layer = dst_ds.CreateLayer("dissolved", srs=srs, geom_type=ogr.wkbMultiPolygon)

        if by:
            # Group features by field value and union geometries
            layer_defn = src_layer.GetLayerDefn()
            field_idx = layer_defn.GetFieldIndex(by)
            if field_idx < 0:
                raise ValueError(f"Field '{by}' not found in layer")

            dst_layer.CreateField(layer_defn.GetFieldDefn(field_idx))

            groups: dict[Any, Any] = {}
            for feat in src_layer:
                key = feat.GetField(by)
                geom = feat.GetGeometryRef()
                if geom is not None:
                    geom = geom.Clone()
                    if key in groups:
                        groups[key] = groups[key].Union(geom)
                    else:
                        groups[key] = geom

            for key, union_geom in groups.items():
                out_feat = ogr.Feature(dst_layer.GetLayerDefn())
                out_feat.SetGeometry(union_geom)
                out_feat.SetField(by, key)
                dst_layer.CreateFeature(out_feat)
        else:
            # Union all geometries
            union_geom = None
            for feat in src_layer:
                geom = feat.GetGeometryRef()
                if geom is not None:
                    geom = geom.Clone()
                    if union_geom is None:
                        union_geom = geom
                    else:
                        union_geom = union_geom.Union(geom)

            if union_geom is not None:
                out_feat = ogr.Feature(dst_layer.GetLayerDefn())
                out_feat.SetGeometry(union_geom)
                dst_layer.CreateFeature(out_feat)

        dst_ds = None
        src_tmp = getattr(src_ds, "_tmp_path", None)
        src_ds = None

        result = self._ogr_ds_to_gdf(dst_path)
        paths_to_clean = [dst_path]
        if src_tmp:
            paths_to_clean.append(src_tmp)
        self._cleanup(*paths_to_clean)
        return result

    def simplify(self, gdf: Any, tolerance: float, **kwargs) -> Any:
        from osgeo import ogr

        src_ds = self._gdf_to_ogr_ds(gdf)
        src_layer = src_ds.GetLayer()

        dst_path = self._make_tmp_path()
        drv = ogr.GetDriverByName("GeoJSON")
        dst_ds = drv.CreateDataSource(dst_path)

        srs = src_layer.GetSpatialRef()
        dst_layer = dst_ds.CreateLayer("simplified", srs=srs, geom_type=src_layer.GetGeomType())

        layer_defn = src_layer.GetLayerDefn()
        for i in range(layer_defn.GetFieldCount()):
            dst_layer.CreateField(layer_defn.GetFieldDefn(i))

        preserve_topology = kwargs.get("preserve_topology", True)
        for feat in src_layer:
            geom = feat.GetGeometryRef()
            if geom is not None:
                if preserve_topology:
                    simplified = geom.SimplifyPreserveTopology(float(tolerance))
                else:
                    simplified = geom.Simplify(float(tolerance))
            else:
                simplified = None

            out_feat = ogr.Feature(dst_layer.GetLayerDefn())
            out_feat.SetGeometry(simplified)
            for i in range(layer_defn.GetFieldCount()):
                out_feat.SetField(i, feat.GetField(i))
            dst_layer.CreateFeature(out_feat)

        dst_ds = None
        src_tmp = getattr(src_ds, "_tmp_path", None)
        src_ds = None

        result = self._ogr_ds_to_gdf(dst_path)
        paths_to_clean = [dst_path]
        if src_tmp:
            paths_to_clean.append(src_tmp)
        self._cleanup(*paths_to_clean)
        return result

    def overlay(self, gdf1: Any, gdf2: Any, how: str = "intersection", **kwargs) -> Any:
        from osgeo import ogr

        src1_ds = self._gdf_to_ogr_ds(gdf1)
        src2_ds = self._gdf_to_ogr_ds(gdf2)
        src1_layer = src1_ds.GetLayer()
        src2_layer = src2_ds.GetLayer()

        dst_path = self._make_tmp_path()
        drv = ogr.GetDriverByName("GeoJSON")
        dst_ds = drv.CreateDataSource(dst_path)

        srs = src1_layer.GetSpatialRef()
        dst_layer = dst_ds.CreateLayer("overlay", srs=srs, geom_type=ogr.wkbGeometryCollection)

        op_map = {
            "intersection": "Intersection",
            "union": "Union",
            "difference": "Difference",
            "symmetric_difference": "SymDifference",
        }

        method = op_map.get(how)
        if method is None:
            raise ValueError(
                f"Unsupported overlay method '{how}'. "
                f"Supported: {list(op_map.keys())}"
            )

        # Use OGR layer-level operations
        ogr_method = getattr(src1_layer, method, None)
        if ogr_method is not None:
            ogr_method(src2_layer, dst_layer)
        else:
            raise ValueError(f"OGR layer does not support '{method}' operation")

        dst_ds = None
        src1_tmp = getattr(src1_ds, "_tmp_path", None)
        src2_tmp = getattr(src2_ds, "_tmp_path", None)
        src1_ds = None
        src2_ds = None

        result = self._ogr_ds_to_gdf(dst_path)
        paths_to_clean = [dst_path]
        if src1_tmp:
            paths_to_clean.append(src1_tmp)
        if src2_tmp:
            paths_to_clean.append(src2_tmp)
        self._cleanup(*paths_to_clean)
        return result
