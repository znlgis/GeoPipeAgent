"""Tests for raster steps."""

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_bounds
import geopandas as gpd
from shapely.geometry import Polygon

from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult


@pytest.fixture
def sample_raster():
    """Create a sample raster_info dict."""
    width, height = 10, 10
    data = np.arange(100, dtype=np.float64).reshape(1, height, width)
    transform = from_bounds(0, 0, 10, 10, width, height)
    profile = {
        "driver": "GTiff",
        "dtype": "float64",
        "width": width,
        "height": height,
        "count": 1,
        "crs": rasterio.crs.CRS.from_epsg(4326),
        "transform": transform,
    }
    return {
        "data": data,
        "transform": transform,
        "crs": rasterio.crs.CRS.from_epsg(4326),
        "profile": profile,
    }


@pytest.fixture
def sample_multiband_raster():
    """Create a sample multi-band raster."""
    width, height = 10, 10
    band1 = np.ones((height, width), dtype=np.float64) * 100
    band2 = np.ones((height, width), dtype=np.float64) * 200
    band3 = np.ones((height, width), dtype=np.float64) * 50
    band4 = np.ones((height, width), dtype=np.float64) * 150
    data = np.stack([band1, band2, band3, band4])
    transform = from_bounds(0, 0, 10, 10, width, height)
    profile = {
        "driver": "GTiff",
        "dtype": "float64",
        "width": width,
        "height": height,
        "count": 4,
        "crs": rasterio.crs.CRS.from_epsg(4326),
        "transform": transform,
    }
    return {
        "data": data,
        "transform": transform,
        "crs": rasterio.crs.CRS.from_epsg(4326),
        "profile": profile,
    }


class TestRasterStats:
    def test_basic_stats(self, sample_raster):
        from geopipe_agent.steps.raster.stats import raster_stats

        ctx = StepContext(params={"input": sample_raster, "band": 1})
        result = raster_stats(ctx)
        assert isinstance(result, StepResult)
        assert result.output["min"] == 0.0
        assert result.output["max"] == 99.0
        assert result.output["band"] == 1
        assert result.output["pixel_count"] == 100

    def test_default_band(self, sample_raster):
        from geopipe_agent.steps.raster.stats import raster_stats

        ctx = StepContext(params={"input": sample_raster})
        result = raster_stats(ctx)
        assert result.output["band"] == 1


class TestRasterReproject:
    def test_reproject(self, sample_raster):
        from geopipe_agent.steps.raster.reproject import raster_reproject

        ctx = StepContext(
            params={
                "input": sample_raster,
                "target_crs": "EPSG:3857",
                "resampling": "nearest",
            }
        )
        result = raster_reproject(ctx)
        assert isinstance(result, StepResult)
        assert result.output["crs"].to_epsg() == 3857
        assert result.stats["target_crs"] == "EPSG:3857"
        assert result.output["data"].shape[0] == 1  # still single band


class TestRasterClip:
    def test_clip(self, sample_raster):
        from geopipe_agent.steps.raster.clip import raster_clip

        # Create a clip polygon that covers part of the raster
        clip_poly = Polygon([(2, 2), (8, 2), (8, 8), (2, 8)])
        clip_gdf = gpd.GeoDataFrame(
            {"name": ["clip"]},
            geometry=[clip_poly],
            crs="EPSG:4326",
        )

        ctx = StepContext(
            params={"input": sample_raster, "mask": clip_gdf, "crop": True, "nodata": 0}
        )
        result = raster_clip(ctx)
        assert isinstance(result, StepResult)
        # Output should be smaller than input
        assert result.output["data"].shape[1] <= sample_raster["data"].shape[1]
        assert result.output["data"].shape[2] <= sample_raster["data"].shape[2]


class TestRasterCalc:
    def test_simple_expression(self, sample_multiband_raster):
        from geopipe_agent.steps.raster.calc import raster_calc

        ctx = StepContext(
            params={"input": sample_multiband_raster, "expression": "B1 + B2"}
        )
        result = raster_calc(ctx)
        assert isinstance(result, StepResult)
        # 100 + 200 = 300
        assert result.output["data"][0, 0, 0] == 300.0

    def test_ndvi_expression(self, sample_multiband_raster):
        from geopipe_agent.steps.raster.calc import raster_calc

        ctx = StepContext(
            params={
                "input": sample_multiband_raster,
                "expression": "(B4 - B3) / (B4 + B3)",
            }
        )
        result = raster_calc(ctx)
        assert isinstance(result, StepResult)
        # (150 - 50) / (150 + 50) = 0.5
        assert abs(result.output["data"][0, 0, 0] - 0.5) < 1e-10

    def test_unknown_band_raises(self, sample_multiband_raster):
        from geopipe_agent.steps.raster.calc import raster_calc

        ctx = StepContext(
            params={"input": sample_multiband_raster, "expression": "B1 + B10"}
        )
        with pytest.raises(ValueError, match="unknown bands"):
            raster_calc(ctx)


class TestRasterContour:
    def test_contour(self, sample_raster):
        from geopipe_agent.steps.raster.contour import raster_contour

        ctx = StepContext(
            params={"input": sample_raster, "interval": 20, "band": 1}
        )
        result = raster_contour(ctx)
        assert isinstance(result, StepResult)
        assert isinstance(result.output, gpd.GeoDataFrame)
        assert "elevation" in result.output.columns
        assert result.stats["interval"] == 20
