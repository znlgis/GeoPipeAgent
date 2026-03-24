"""Tests for network steps."""

import pytest
import geopandas as gpd
from shapely.geometry import LineString, Point

from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult


@pytest.fixture
def road_network_gdf():
    """Create a simple road network as a GeoDataFrame."""
    lines = [
        LineString([(0, 0), (1, 0)]),
        LineString([(1, 0), (2, 0)]),
        LineString([(2, 0), (2, 1)]),
        LineString([(0, 0), (0, 1)]),
        LineString([(0, 1), (1, 1)]),
        LineString([(1, 1), (2, 1)]),
        LineString([(1, 0), (1, 1)]),
    ]
    return gpd.GeoDataFrame(
        {"road_id": list(range(len(lines)))},
        geometry=lines,
        crs="EPSG:4326",
    )


class TestNetworkShortestPath:
    def test_shortest_path(self, road_network_gdf):
        from geopipe_agent.steps.network.shortest_path import network_shortest_path

        ctx = StepContext(
            params={
                "input": road_network_gdf,
                "origin": [0, 0],
                "destination": [2, 1],
            }
        )
        result = network_shortest_path(ctx)
        assert isinstance(result, StepResult)
        assert isinstance(result.output, gpd.GeoDataFrame)
        assert len(result.output) == 1
        assert result.stats["path_cost"] > 0
        assert result.stats["node_count"] >= 2

    def test_no_path_raises(self):
        from geopipe_agent.steps.network.shortest_path import network_shortest_path

        # Two disconnected segments
        lines = [
            LineString([(0, 0), (1, 0)]),
            LineString([(10, 10), (11, 10)]),
        ]
        gdf = gpd.GeoDataFrame(
            {"road_id": [0, 1]},
            geometry=lines,
            crs="EPSG:4326",
        )
        ctx = StepContext(
            params={"input": gdf, "origin": [0, 0], "destination": [11, 10]}
        )
        with pytest.raises(ValueError, match="No path found"):
            network_shortest_path(ctx)


class TestNetworkServiceArea:
    def test_service_area(self, road_network_gdf):
        from geopipe_agent.steps.network.service_area import network_service_area

        ctx = StepContext(
            params={
                "input": road_network_gdf,
                "center": [0, 0],
                "cost_limit": 2.0,
            }
        )
        result = network_service_area(ctx)
        assert isinstance(result, StepResult)
        assert isinstance(result.output, gpd.GeoDataFrame)
        assert result.stats["reachable_nodes"] > 0
        assert result.stats["cost_limit"] == 2.0

    def test_small_service_area(self, road_network_gdf):
        from geopipe_agent.steps.network.service_area import network_service_area

        ctx = StepContext(
            params={
                "input": road_network_gdf,
                "center": [0, 0],
                "cost_limit": 0.5,
            }
        )
        result = network_service_area(ctx)
        assert isinstance(result, StepResult)
        # Small cost limit should yield fewer reachable nodes
        assert result.stats["reachable_nodes"] >= 1


class TestNetworkGeocode:
    def test_geocode_returns_geodataframe(self, monkeypatch):
        """Test geocode with mocked geopy to avoid network calls."""
        from geopipe_agent.steps.network.geocode import network_geocode
        from geopy.location import Location

        class FakeNominatim:
            def __init__(self, **kwargs):
                pass

            def geocode(self, address):
                if "Beijing" in address or "北京" in address:
                    return Location(
                        "Beijing, China", (39.9, 116.4), {"place_id": 1}
                    )
                return None

        import geopy.geocoders
        monkeypatch.setattr(geopy.geocoders, "Nominatim", FakeNominatim)

        ctx = StepContext(
            params={
                "addresses": ["Beijing", "unknown_place_xyz"],
                "provider": "nominatim",
            }
        )
        result = network_geocode(ctx)
        assert isinstance(result, StepResult)
        assert isinstance(result.output, gpd.GeoDataFrame)
        assert result.stats["total"] == 2
        assert result.stats["success"] == 1
        assert result.stats["failed"] == 1
