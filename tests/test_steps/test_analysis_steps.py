"""Tests for analysis steps."""

import numpy as np
import pytest
import geopandas as gpd
from shapely.geometry import Point

from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult


@pytest.fixture
def many_points_gdf():
    """Create a GeoDataFrame with many points for analysis."""
    np.random.seed(42)
    n = 50
    xs = np.random.uniform(0, 10, n)
    ys = np.random.uniform(0, 10, n)
    points = [Point(x, y) for x, y in zip(xs, ys)]
    return gpd.GeoDataFrame(
        {"value": np.random.uniform(10, 100, n), "name": [f"P{i}" for i in range(n)]},
        geometry=points,
        crs="EPSG:4326",
    )


@pytest.fixture
def cluster_points_gdf():
    """Create clustered point data for clustering tests."""
    np.random.seed(123)
    # 3 clusters
    c1 = np.random.normal(loc=[0, 0], scale=0.1, size=(20, 2))
    c2 = np.random.normal(loc=[5, 5], scale=0.1, size=(20, 2))
    c3 = np.random.normal(loc=[10, 0], scale=0.1, size=(20, 2))
    coords = np.vstack([c1, c2, c3])
    points = [Point(x, y) for x, y in coords]
    return gpd.GeoDataFrame(
        {"id": list(range(60))},
        geometry=points,
        crs="EPSG:4326",
    )


class TestAnalysisVoronoi:
    def test_voronoi(self, many_points_gdf):
        from geopipe_agent.steps.analysis.voronoi import analysis_voronoi

        ctx = StepContext(params={"input": many_points_gdf})
        result = analysis_voronoi(ctx)
        assert isinstance(result, StepResult)
        assert isinstance(result.output, gpd.GeoDataFrame)
        assert len(result.output) == len(many_points_gdf)
        assert result.stats["polygon_count"] == len(many_points_gdf)

    def test_voronoi_too_few_points(self):
        from geopipe_agent.steps.analysis.voronoi import analysis_voronoi

        points = [Point(0, 0), Point(1, 1)]
        gdf = gpd.GeoDataFrame(
            {"name": ["A", "B"]}, geometry=points, crs="EPSG:4326"
        )
        ctx = StepContext(params={"input": gdf})
        with pytest.raises(ValueError, match="at least 3 points"):
            analysis_voronoi(ctx)


class TestAnalysisHeatmap:
    def test_heatmap(self, many_points_gdf):
        from geopipe_agent.steps.analysis.heatmap import analysis_heatmap

        ctx = StepContext(
            params={"input": many_points_gdf, "resolution": 50}
        )
        result = analysis_heatmap(ctx)
        assert isinstance(result, StepResult)
        assert result.output["data"].shape[0] == 1  # single band
        assert result.output["data"].shape[2] == 50  # width = resolution
        assert result.stats["point_count"] == len(many_points_gdf)
        assert result.stats["max_density"] > 0


class TestAnalysisInterpolate:
    def test_linear_interpolation(self, many_points_gdf):
        from geopipe_agent.steps.analysis.interpolate import analysis_interpolate

        ctx = StepContext(
            params={
                "input": many_points_gdf,
                "value_field": "value",
                "method": "linear",
                "resolution": 20,
            }
        )
        result = analysis_interpolate(ctx)
        assert isinstance(result, StepResult)
        assert result.output["data"].shape[0] == 1
        assert result.output["data"].shape[2] == 20
        assert result.stats["method"] == "linear"

    def test_idw_interpolation(self, many_points_gdf):
        from geopipe_agent.steps.analysis.interpolate import analysis_interpolate

        ctx = StepContext(
            params={
                "input": many_points_gdf,
                "value_field": "value",
                "method": "idw",
                "resolution": 10,
            }
        )
        result = analysis_interpolate(ctx)
        assert isinstance(result, StepResult)
        assert result.stats["method"] == "idw"

    def test_missing_field_raises(self, many_points_gdf):
        from geopipe_agent.steps.analysis.interpolate import analysis_interpolate

        ctx = StepContext(
            params={
                "input": many_points_gdf,
                "value_field": "nonexistent",
                "method": "linear",
            }
        )
        with pytest.raises(ValueError, match="not found"):
            analysis_interpolate(ctx)


class TestAnalysisCluster:
    def test_dbscan(self, cluster_points_gdf):
        from geopipe_agent.steps.analysis.cluster import analysis_cluster

        ctx = StepContext(
            params={
                "input": cluster_points_gdf,
                "method": "dbscan",
                "eps": 0.5,
                "min_samples": 3,
            }
        )
        result = analysis_cluster(ctx)
        assert isinstance(result, StepResult)
        assert "cluster" in result.output.columns
        assert result.stats["method"] == "dbscan"
        assert result.stats["n_clusters"] >= 2  # should find at least 2 clusters

    def test_kmeans(self, cluster_points_gdf):
        from geopipe_agent.steps.analysis.cluster import analysis_cluster

        ctx = StepContext(
            params={
                "input": cluster_points_gdf,
                "method": "kmeans",
                "n_clusters": 3,
            }
        )
        result = analysis_cluster(ctx)
        assert isinstance(result, StepResult)
        assert "cluster" in result.output.columns
        assert result.stats["method"] == "kmeans"
        assert result.stats["n_clusters"] == 3
