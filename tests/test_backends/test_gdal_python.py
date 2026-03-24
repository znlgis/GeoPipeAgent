"""Tests for GdalPythonBackend."""

import pytest
import geopandas as gpd
from shapely.geometry import Point, Polygon

from geopipe_agent.backends.gdal_python import GdalPythonBackend


class TestGdalPythonBackend:
    @pytest.fixture
    def backend(self):
        return GdalPythonBackend()

    def test_name(self, backend):
        assert backend.name() == "gdal_python"

    def test_is_available(self, backend):
        assert backend.is_available()

    def test_buffer(self, backend, sample_points_gdf):
        result = backend.buffer(sample_points_gdf, 0.1)
        assert len(result) == 3
        assert all(g.geom_type == "Polygon" for g in result.geometry)

    def test_buffer_cap_style(self, backend, sample_points_gdf):
        result = backend.buffer(sample_points_gdf, 0.1, cap_style="square")
        assert len(result) == 3

    def test_clip(self, backend, sample_polygons_gdf, sample_clip_gdf):
        result = backend.clip(sample_polygons_gdf, sample_clip_gdf)
        assert len(result) > 0

    def test_reproject(self, backend, sample_points_gdf):
        result = backend.reproject(sample_points_gdf, "EPSG:3857")
        assert str(result.crs) == "EPSG:3857"

    def test_dissolve(self, backend, sample_polygons_gdf):
        result = backend.dissolve(sample_polygons_gdf)
        assert len(result) == 1

    def test_dissolve_by_column(self, backend, sample_polygons_gdf):
        result = backend.dissolve(sample_polygons_gdf, by="name")
        assert len(result) == 2

    def test_simplify(self, backend, sample_polygons_gdf):
        result = backend.simplify(sample_polygons_gdf, tolerance=0.01)
        assert len(result) == len(sample_polygons_gdf)

    def test_overlay(self, backend, sample_polygons_gdf, sample_clip_gdf):
        result = backend.overlay(sample_polygons_gdf, sample_clip_gdf, how="intersection")
        assert len(result) > 0
