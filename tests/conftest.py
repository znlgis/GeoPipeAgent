"""Shared test fixtures."""

from __future__ import annotations

import importlib
import pytest
import geopandas as gpd
from shapely.geometry import Point, Polygon

from geopipe_agent.steps.registry import StepRegistry


def _reload_builtin_steps():
    """Force-reload all step modules to re-trigger @step decorators."""
    import geopipe_agent.steps.io.read_vector
    import geopipe_agent.steps.io.write_vector
    import geopipe_agent.steps.io.read_raster
    import geopipe_agent.steps.io.write_raster
    import geopipe_agent.steps.vector.buffer
    import geopipe_agent.steps.vector.clip
    import geopipe_agent.steps.vector.reproject
    import geopipe_agent.steps.vector.dissolve
    import geopipe_agent.steps.vector.simplify
    import geopipe_agent.steps.vector.query
    import geopipe_agent.steps.vector.overlay

    importlib.reload(geopipe_agent.steps.io.read_vector)
    importlib.reload(geopipe_agent.steps.io.write_vector)
    importlib.reload(geopipe_agent.steps.io.read_raster)
    importlib.reload(geopipe_agent.steps.io.write_raster)
    importlib.reload(geopipe_agent.steps.vector.buffer)
    importlib.reload(geopipe_agent.steps.vector.clip)
    importlib.reload(geopipe_agent.steps.vector.reproject)
    importlib.reload(geopipe_agent.steps.vector.dissolve)
    importlib.reload(geopipe_agent.steps.vector.simplify)
    importlib.reload(geopipe_agent.steps.vector.query)
    importlib.reload(geopipe_agent.steps.vector.overlay)


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset the step registry before each test and reload built-in steps."""
    StepRegistry.reset()
    _reload_builtin_steps()
    yield


@pytest.fixture
def sample_points_gdf():
    """Create a sample GeoDataFrame with point geometries."""
    points = [Point(0, 0), Point(1, 1), Point(2, 2)]
    return gpd.GeoDataFrame(
        {"name": ["A", "B", "C"], "value": [10, 20, 30]},
        geometry=points,
        crs="EPSG:4326",
    )


@pytest.fixture
def sample_polygons_gdf():
    """Create a sample GeoDataFrame with polygon geometries."""
    polys = [
        Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
        Polygon([(1, 1), (2, 1), (2, 2), (1, 2)]),
    ]
    return gpd.GeoDataFrame(
        {"name": ["P1", "P2"], "area_val": [100, 200]},
        geometry=polys,
        crs="EPSG:4326",
    )


@pytest.fixture
def sample_clip_gdf():
    """Create a clip boundary GeoDataFrame."""
    clip_poly = Polygon([(0.5, 0.5), (1.5, 0.5), (1.5, 1.5), (0.5, 1.5)])
    return gpd.GeoDataFrame(
        {"name": ["clip"]},
        geometry=[clip_poly],
        crs="EPSG:4326",
    )
