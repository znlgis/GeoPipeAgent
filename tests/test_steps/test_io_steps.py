"""Tests for IO steps."""

import pytest
import geopandas as gpd
from shapely.geometry import Point

from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult


class TestIOReadVector:
    def test_read_geojson(self, tmp_path, sample_points_gdf):
        from geopipe_agent.steps.io.read_vector import io_read_vector

        path = tmp_path / "test.geojson"
        sample_points_gdf.to_file(str(path), driver="GeoJSON")

        ctx = StepContext(params={"path": str(path)})
        result = io_read_vector(ctx)

        assert isinstance(result, StepResult)
        assert len(result.output) == 3
        assert result.stats["feature_count"] == 3
        assert "EPSG:4326" in str(result.stats["crs"])

    def test_read_nonexistent_raises(self, tmp_path):
        from geopipe_agent.steps.io.read_vector import io_read_vector

        ctx = StepContext(params={"path": str(tmp_path / "missing.shp")})
        with pytest.raises(Exception):
            io_read_vector(ctx)


class TestIOWriteVector:
    def test_write_geojson(self, tmp_path, sample_points_gdf):
        from geopipe_agent.steps.io.write_vector import io_write_vector

        path = tmp_path / "output.geojson"
        ctx = StepContext(
            params={"input": sample_points_gdf, "path": str(path), "format": "GeoJSON"}
        )
        result = io_write_vector(ctx)

        assert isinstance(result, StepResult)
        assert result.output == str(path)
        assert path.exists()
        assert result.stats["feature_count"] == 3

    def test_write_creates_directory(self, tmp_path, sample_points_gdf):
        from geopipe_agent.steps.io.write_vector import io_write_vector

        path = tmp_path / "subdir" / "output.geojson"
        ctx = StepContext(
            params={"input": sample_points_gdf, "path": str(path)}
        )
        result = io_write_vector(ctx)
        assert path.exists()
