"""Shared test fixtures."""

from __future__ import annotations

import pytest
import geopandas as gpd
from shapely.geometry import Point, Polygon

from geopipe_agent.steps import registry, reload_builtin_steps


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset the step registry before each test and reload built-in steps."""
    registry.reset()
    reload_builtin_steps()
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
