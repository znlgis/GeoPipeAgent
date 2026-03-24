"""Tests for vector steps."""

import pytest
import geopandas as gpd
from shapely.geometry import Point, Polygon

from geopipe_agent.engine.context import StepContext
from geopipe_agent.backends.gdal_python import GdalPythonBackend
from geopipe_agent.models.result import StepResult


class TestVectorBuffer:
    def test_buffer(self, sample_points_gdf):
        from geopipe_agent.steps.vector.buffer import vector_buffer

        backend = GdalPythonBackend()
        ctx = StepContext(
            params={"input": sample_points_gdf, "distance": 0.1, "cap_style": "round"},
            backend=backend,
        )
        result = vector_buffer(ctx)
        assert isinstance(result, StepResult)
        assert len(result.output) == 3
        assert result.stats["feature_count"] == 3
        assert result.stats["total_area"] > 0
        # All geometries should be polygons after buffer
        assert all(g.geom_type == "Polygon" for g in result.output.geometry)


class TestVectorClip:
    def test_clip(self, sample_polygons_gdf, sample_clip_gdf):
        from geopipe_agent.steps.vector.clip import vector_clip

        backend = GdalPythonBackend()
        ctx = StepContext(
            params={
                "input": sample_polygons_gdf,
                "clip_geometry": sample_clip_gdf,
            },
            backend=backend,
        )
        result = vector_clip(ctx)
        assert isinstance(result, StepResult)
        assert len(result.output) > 0


class TestVectorReproject:
    def test_reproject(self, sample_points_gdf):
        from geopipe_agent.steps.vector.reproject import vector_reproject

        backend = GdalPythonBackend()
        ctx = StepContext(
            params={"input": sample_points_gdf, "target_crs": "EPSG:3857"},
            backend=backend,
        )
        result = vector_reproject(ctx)
        assert isinstance(result, StepResult)
        assert str(result.output.crs) == "EPSG:3857"
        assert result.stats["target_crs"] == "EPSG:3857"


class TestVectorDissolve:
    def test_dissolve(self, sample_polygons_gdf):
        from geopipe_agent.steps.vector.dissolve import vector_dissolve

        backend = GdalPythonBackend()
        ctx = StepContext(
            params={"input": sample_polygons_gdf},
            backend=backend,
        )
        result = vector_dissolve(ctx)
        assert isinstance(result, StepResult)
        assert len(result.output) == 1  # All dissolved into one


class TestVectorSimplify:
    def test_simplify(self, sample_polygons_gdf):
        from geopipe_agent.steps.vector.simplify import vector_simplify

        backend = GdalPythonBackend()
        ctx = StepContext(
            params={"input": sample_polygons_gdf, "tolerance": 0.01},
            backend=backend,
        )
        result = vector_simplify(ctx)
        assert isinstance(result, StepResult)
        assert len(result.output) == len(sample_polygons_gdf)


class TestVectorQuery:
    def test_query(self, sample_points_gdf):
        from geopipe_agent.steps.vector.query import vector_query

        ctx = StepContext(
            params={"input": sample_points_gdf, "expression": "value > 15"},
        )
        result = vector_query(ctx)
        assert isinstance(result, StepResult)
        assert len(result.output) == 2
        assert result.stats["output_count"] == 2


class TestVectorOverlay:
    def test_overlay_intersection(self, sample_polygons_gdf, sample_clip_gdf):
        from geopipe_agent.steps.vector.overlay import vector_overlay

        backend = GdalPythonBackend()
        ctx = StepContext(
            params={
                "input": sample_polygons_gdf,
                "overlay_layer": sample_clip_gdf,
                "how": "intersection",
            },
            backend=backend,
        )
        result = vector_overlay(ctx)
        assert isinstance(result, StepResult)
        assert len(result.output) > 0
        assert result.stats["overlay_method"] == "intersection"
