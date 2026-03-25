"""Tests for QC (quality check) steps."""

from __future__ import annotations

import numpy as np
import pytest
import geopandas as gpd
from shapely.geometry import Point, Polygon, LineString, box

from geopipe_agent.engine.context import StepContext, PipelineContext
from geopipe_agent.models.result import StepResult
from geopipe_agent.models.qc import QcIssue
from geopipe_agent.steps import registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ctx(params: dict) -> StepContext:
    """Create a StepContext with the given params (no backend)."""
    return StepContext(params=params, backend=None, pipeline_context=PipelineContext())


# ---------------------------------------------------------------------------
# QcIssue model tests
# ---------------------------------------------------------------------------

class TestQcIssue:

    def test_to_dict_minimal(self):
        issue = QcIssue(rule_id="test", severity="error", message="bad")
        d = issue.to_dict()
        assert d["rule_id"] == "test"
        assert d["severity"] == "error"
        assert d["message"] == "bad"
        assert "feature_index" not in d
        assert "details" not in d

    def test_to_dict_full(self):
        issue = QcIssue(
            rule_id="test",
            severity="warning",
            feature_index=5,
            message="some issue",
            details={"extra": "info"},
        )
        d = issue.to_dict()
        assert d["feature_index"] == 5
        assert d["details"] == {"extra": "info"}


# ---------------------------------------------------------------------------
# StepResult issues extension tests
# ---------------------------------------------------------------------------

class TestStepResultIssues:

    def test_issues_default_empty(self):
        result = StepResult(output="data")
        assert result.issues == []

    def test_summary_without_issues(self):
        result = StepResult(output=[1, 2, 3])
        summary = result.summary()
        assert "issues_count" not in summary

    def test_summary_with_issues(self):
        issues = [
            QcIssue(rule_id="r1", severity="error", message="a"),
            QcIssue(rule_id="r1", severity="error", message="b"),
            QcIssue(rule_id="r2", severity="warning", message="c"),
        ]
        result = StepResult(output=None, issues=issues)
        summary = result.summary()
        assert summary["issues_count"] == 3
        assert summary["issues_by_severity"] == {"error": 2, "warning": 1}


# ---------------------------------------------------------------------------
# qc.geometry_validity
# ---------------------------------------------------------------------------

class TestGeometryValidity:

    def test_valid_geometries(self, sample_polygons_gdf):
        ctx = _make_ctx({"input": sample_polygons_gdf})
        step_info = registry.get("qc.geometry_validity")
        result = step_info.func(ctx)

        assert isinstance(result, StepResult)
        assert result.issues == []
        assert result.stats["issues_count"] == 0
        assert result.stats["valid_count"] == len(sample_polygons_gdf)
        # Output should be the same data (passthrough)
        assert len(result.output) == len(sample_polygons_gdf)

    def test_invalid_geometry_detected(self):
        # A self-intersecting polygon (bowtie)
        bowtie = Polygon([(0, 0), (1, 1), (1, 0), (0, 1)])
        gdf = gpd.GeoDataFrame(
            {"name": ["bad"]},
            geometry=[bowtie],
            crs="EPSG:4326",
        )
        ctx = _make_ctx({"input": gdf, "severity": "error"})
        result = registry.get("qc.geometry_validity").func(ctx)

        assert len(result.issues) == 1
        assert result.issues[0].rule_id == "geometry_validity"
        assert result.issues[0].severity == "error"
        assert result.issues[0].feature_index == 0
        assert result.stats["issues_count"] == 1

    def test_empty_geometry_detected(self):
        from shapely.geometry import Point
        from shapely import wkt
        empty = wkt.loads("GEOMETRYCOLLECTION EMPTY")
        gdf = gpd.GeoDataFrame(
            {"name": ["empty"]},
            geometry=[empty],
            crs="EPSG:4326",
        )
        ctx = _make_ctx({"input": gdf})
        result = registry.get("qc.geometry_validity").func(ctx)

        assert len(result.issues) == 1
        assert "empty" in result.issues[0].message.lower()

    def test_auto_fix(self):
        bowtie = Polygon([(0, 0), (1, 1), (1, 0), (0, 1)])
        gdf = gpd.GeoDataFrame(
            {"name": ["bad"]},
            geometry=[bowtie],
            crs="EPSG:4326",
        )
        ctx = _make_ctx({"input": gdf, "auto_fix": True})
        result = registry.get("qc.geometry_validity").func(ctx)

        # Issues are still reported but output is fixed
        assert len(result.issues) == 1
        assert result.output.geometry.iloc[0].is_valid

    def test_issues_gdf_populated(self):
        bowtie = Polygon([(0, 0), (1, 1), (1, 0), (0, 1)])
        valid = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        gdf = gpd.GeoDataFrame(
            {"name": ["bad", "good"]},
            geometry=[bowtie, valid],
            crs="EPSG:4326",
        )
        ctx = _make_ctx({"input": gdf})
        result = registry.get("qc.geometry_validity").func(ctx)

        issues_gdf = result.metadata["issues_gdf"]
        assert len(issues_gdf) == 1
        assert issues_gdf.iloc[0]["name"] == "bad"


# ---------------------------------------------------------------------------
# qc.attribute_completeness
# ---------------------------------------------------------------------------

class TestAttributeCompleteness:

    def test_all_complete(self, sample_polygons_gdf):
        ctx = _make_ctx({
            "input": sample_polygons_gdf,
            "required_fields": ["name"],
        })
        result = registry.get("qc.attribute_completeness").func(ctx)

        assert result.issues == []
        assert result.stats["issues_count"] == 0

    def test_missing_column(self, sample_polygons_gdf):
        ctx = _make_ctx({
            "input": sample_polygons_gdf,
            "required_fields": ["name", "nonexistent"],
        })
        result = registry.get("qc.attribute_completeness").func(ctx)

        assert len(result.issues) == 1
        assert "nonexistent" in result.issues[0].message
        assert result.stats["missing_columns"] == ["nonexistent"]

    def test_null_values_detected(self):
        gdf = gpd.GeoDataFrame(
            {"name": ["A", None, "C"], "value": [1, 2, 3]},
            geometry=[Point(0, 0), Point(1, 1), Point(2, 2)],
            crs="EPSG:4326",
        )
        ctx = _make_ctx({
            "input": gdf,
            "required_fields": ["name"],
            "severity": "warning",
        })
        result = registry.get("qc.attribute_completeness").func(ctx)

        assert len(result.issues) == 1
        assert result.issues[0].feature_index == 1

    def test_empty_string_detected(self):
        gdf = gpd.GeoDataFrame(
            {"name": ["A", "  ", "C"]},
            geometry=[Point(0, 0), Point(1, 1), Point(2, 2)],
            crs="EPSG:4326",
        )
        ctx = _make_ctx({
            "input": gdf,
            "required_fields": ["name"],
            "allow_empty": False,
        })
        result = registry.get("qc.attribute_completeness").func(ctx)

        assert len(result.issues) == 1


# ---------------------------------------------------------------------------
# qc.crs_check
# ---------------------------------------------------------------------------

class TestCrsCheck:

    def test_correct_crs(self, sample_polygons_gdf):
        ctx = _make_ctx({
            "input": sample_polygons_gdf,
            "expected_crs": "EPSG:4326",
        })
        result = registry.get("qc.crs_check").func(ctx)

        assert result.issues == []

    def test_wrong_crs(self, sample_polygons_gdf):
        ctx = _make_ctx({
            "input": sample_polygons_gdf,
            "expected_crs": "EPSG:3857",
        })
        result = registry.get("qc.crs_check").func(ctx)

        assert len(result.issues) == 1
        assert "mismatch" in result.issues[0].message.lower()

    def test_missing_crs(self):
        gdf = gpd.GeoDataFrame(
            {"name": ["A"]},
            geometry=[Point(0, 0)],
            crs=None,
        )
        ctx = _make_ctx({"input": gdf})
        result = registry.get("qc.crs_check").func(ctx)

        assert len(result.issues) == 1
        assert "no crs" in result.issues[0].message.lower()


# ---------------------------------------------------------------------------
# qc.value_range
# ---------------------------------------------------------------------------

class TestValueRange:

    def test_all_in_range(self, sample_points_gdf):
        ctx = _make_ctx({
            "input": sample_points_gdf,
            "field": "value",
            "min": 0,
            "max": 100,
        })
        result = registry.get("qc.value_range").func(ctx)

        assert result.issues == []

    def test_below_min(self, sample_points_gdf):
        ctx = _make_ctx({
            "input": sample_points_gdf,
            "field": "value",
            "min": 15,
        })
        result = registry.get("qc.value_range").func(ctx)

        # value=10 is below min=15
        assert len(result.issues) == 1
        assert result.issues[0].feature_index == 0

    def test_above_max(self, sample_points_gdf):
        ctx = _make_ctx({
            "input": sample_points_gdf,
            "field": "value",
            "max": 25,
        })
        result = registry.get("qc.value_range").func(ctx)

        # value=30 exceeds max=25
        assert len(result.issues) == 1
        assert result.issues[0].feature_index == 2

    def test_missing_field(self, sample_points_gdf):
        ctx = _make_ctx({
            "input": sample_points_gdf,
            "field": "nonexistent",
            "min": 0,
        })
        result = registry.get("qc.value_range").func(ctx)

        assert len(result.issues) == 1
        assert "does not exist" in result.issues[0].message


# ---------------------------------------------------------------------------
# qc.topology
# ---------------------------------------------------------------------------

class TestTopology:

    def test_no_overlaps_clean(self):
        """Non-overlapping polygons should produce no issues."""
        polys = [
            Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
            Polygon([(2, 2), (3, 2), (3, 3), (2, 3)]),
        ]
        gdf = gpd.GeoDataFrame(geometry=polys, crs="EPSG:4326")
        ctx = _make_ctx({"input": gdf, "rules": ["no_overlaps"], "tolerance": 0.0})
        result = registry.get("qc.topology").func(ctx)

        assert result.issues == []

    def test_overlaps_detected(self):
        """Overlapping polygons should be detected."""
        polys = [
            Polygon([(0, 0), (2, 0), (2, 2), (0, 2)]),
            Polygon([(1, 1), (3, 1), (3, 3), (1, 3)]),
        ]
        gdf = gpd.GeoDataFrame(geometry=polys, crs="EPSG:4326")
        ctx = _make_ctx({"input": gdf, "rules": ["no_overlaps"], "tolerance": 0.0})
        result = registry.get("qc.topology").func(ctx)

        assert len(result.issues) >= 1
        assert "overlap" in result.issues[0].message.lower()

    def test_dangles_detected(self):
        """Dangling line endpoints should be detected."""
        lines = [
            LineString([(0, 0), (1, 1)]),
            LineString([(1, 1), (2, 0)]),
            LineString([(5, 5), (6, 6)]),  # isolated: both endpoints are dangles
        ]
        gdf = gpd.GeoDataFrame(geometry=lines, crs="EPSG:4326")
        ctx = _make_ctx({"input": gdf, "rules": ["no_dangles"]})
        result = registry.get("qc.topology").func(ctx)

        # (0,0), (2,0), (5,5), (6,6) are all dangles
        assert len(result.issues) == 4


# ---------------------------------------------------------------------------
# qc.duplicate_check
# ---------------------------------------------------------------------------

class TestDuplicateCheck:

    def test_no_duplicates(self, sample_polygons_gdf):
        ctx = _make_ctx({
            "input": sample_polygons_gdf,
            "check_geometry": True,
        })
        result = registry.get("qc.duplicate_check").func(ctx)

        assert result.issues == []

    def test_geometry_duplicate_detected(self):
        poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        gdf = gpd.GeoDataFrame(
            {"name": ["A", "B"]},
            geometry=[poly, poly],
            crs="EPSG:4326",
        )
        ctx = _make_ctx({"input": gdf, "check_geometry": True})
        result = registry.get("qc.duplicate_check").func(ctx)

        assert len(result.issues) == 1
        assert result.issues[0].rule_id == "duplicate_geometry"

    def test_attribute_duplicate_detected(self):
        gdf = gpd.GeoDataFrame(
            {"name": ["same", "same", "diff"]},
            geometry=[Point(0, 0), Point(1, 1), Point(2, 2)],
            crs="EPSG:4326",
        )
        ctx = _make_ctx({
            "input": gdf,
            "check_geometry": False,
            "check_fields": ["name"],
        })
        result = registry.get("qc.duplicate_check").func(ctx)

        assert len(result.issues) == 1
        assert result.issues[0].rule_id == "duplicate_attributes"


# ---------------------------------------------------------------------------
# qc.attribute_domain
# ---------------------------------------------------------------------------

class TestAttributeDomain:

    def test_valid_values(self):
        gdf = gpd.GeoDataFrame(
            {"type": ["A", "B", "C"]},
            geometry=[Point(0, 0), Point(1, 1), Point(2, 2)],
            crs="EPSG:4326",
        )
        ctx = _make_ctx({
            "input": gdf,
            "field": "type",
            "allowed_values": ["A", "B", "C"],
        })
        result = registry.get("qc.attribute_domain").func(ctx)

        assert result.issues == []

    def test_invalid_value_detected(self):
        gdf = gpd.GeoDataFrame(
            {"type": ["A", "X", "C"]},
            geometry=[Point(0, 0), Point(1, 1), Point(2, 2)],
            crs="EPSG:4326",
        )
        ctx = _make_ctx({
            "input": gdf,
            "field": "type",
            "allowed_values": ["A", "B", "C"],
        })
        result = registry.get("qc.attribute_domain").func(ctx)

        assert len(result.issues) == 1
        assert result.issues[0].feature_index == 1

    def test_pattern_validation(self):
        gdf = gpd.GeoDataFrame(
            {"code": ["AB-001", "CD-002", "invalid"]},
            geometry=[Point(0, 0), Point(1, 1), Point(2, 2)],
            crs="EPSG:4326",
        )
        ctx = _make_ctx({
            "input": gdf,
            "field": "code",
            "pattern": r"[A-Z]{2}-\d{3}",
        })
        result = registry.get("qc.attribute_domain").func(ctx)

        assert len(result.issues) == 1
        assert result.issues[0].feature_index == 2


# ---------------------------------------------------------------------------
# qc.raster_nodata
# ---------------------------------------------------------------------------

class TestRasterNodata:

    def _make_raster(self, nodata=None, data=None):
        if data is None:
            data = np.array([[1, 2], [3, -9999]], dtype=np.float32)
        profile = {"nodata": nodata, "dtype": "float32"}
        return {"data": data, "transform": [1, 0, 0, 0, -1, 10], "crs": "EPSG:4326", "profile": profile}

    def test_nodata_defined_and_ok(self):
        raster = self._make_raster(nodata=-9999)
        ctx = _make_ctx({"input": raster, "expected_nodata": -9999, "max_nodata_ratio": 0.5})
        result = registry.get("qc.raster_nodata").func(ctx)

        assert result.issues == []

    def test_nodata_not_defined(self):
        raster = self._make_raster(nodata=None)
        ctx = _make_ctx({"input": raster})
        result = registry.get("qc.raster_nodata").func(ctx)

        assert len(result.issues) == 1
        assert "no nodata" in result.issues[0].message.lower()

    def test_nodata_value_mismatch(self):
        raster = self._make_raster(nodata=-9999)
        ctx = _make_ctx({"input": raster, "expected_nodata": -999})
        result = registry.get("qc.raster_nodata").func(ctx)

        assert len(result.issues) >= 1
        assert any("mismatch" in i.message.lower() for i in result.issues)

    def test_nodata_ratio_exceeded(self):
        data = np.array([[-9999, -9999], [-9999, 1]], dtype=np.float32)
        raster = self._make_raster(nodata=-9999, data=data)
        ctx = _make_ctx({"input": raster, "max_nodata_ratio": 0.5})
        result = registry.get("qc.raster_nodata").func(ctx)

        # 3/4 = 75% > 50%
        assert any("ratio" in i.message.lower() for i in result.issues)


# ---------------------------------------------------------------------------
# qc.raster_value_range
# ---------------------------------------------------------------------------

class TestRasterValueRange:

    def _make_raster(self):
        data = np.array([[0.5, 0.8], [-0.2, 1.5]], dtype=np.float32)
        profile = {"nodata": None}
        return {"data": data, "transform": [1, 0, 0, 0, -1, 10], "crs": "EPSG:4326", "profile": profile}

    def test_all_in_range(self):
        raster = self._make_raster()
        ctx = _make_ctx({"input": raster, "min": -1, "max": 2})
        result = registry.get("qc.raster_value_range").func(ctx)

        assert result.issues == []

    def test_below_min(self):
        raster = self._make_raster()
        ctx = _make_ctx({"input": raster, "min": 0})
        result = registry.get("qc.raster_value_range").func(ctx)

        assert len(result.issues) == 1
        assert "below" in result.issues[0].message.lower()

    def test_above_max(self):
        raster = self._make_raster()
        ctx = _make_ctx({"input": raster, "max": 1.0})
        result = registry.get("qc.raster_value_range").func(ctx)

        assert len(result.issues) == 1
        assert "above" in result.issues[0].message.lower()


# ---------------------------------------------------------------------------
# qc.raster_resolution
# ---------------------------------------------------------------------------

class TestRasterResolution:

    def _make_raster(self, res_x=30, res_y=-30):
        data = np.array([[1, 2], [3, 4]], dtype=np.float32)
        transform = [res_x, 0, 100, 0, res_y, 200]
        profile = {"nodata": None}
        return {"data": data, "transform": transform, "crs": "EPSG:4326", "profile": profile}

    def test_correct_resolution(self):
        raster = self._make_raster(30, -30)
        ctx = _make_ctx({
            "input": raster,
            "expected_x": 30,
            "expected_y": 30,
            "tolerance": 0.5,
        })
        result = registry.get("qc.raster_resolution").func(ctx)

        assert result.issues == []

    def test_wrong_resolution(self):
        raster = self._make_raster(10, -10)
        ctx = _make_ctx({
            "input": raster,
            "expected_x": 30,
            "expected_y": 30,
            "tolerance": 0.5,
        })
        result = registry.get("qc.raster_resolution").func(ctx)

        assert len(result.issues) == 2  # X and Y both wrong

    def test_missing_transform(self):
        raster = {"data": np.array([[1]]), "profile": {}}
        ctx = _make_ctx({
            "input": raster,
            "expected_x": 30,
            "expected_y": 30,
        })
        result = registry.get("qc.raster_resolution").func(ctx)

        assert len(result.issues) == 1
        assert "no transform" in result.issues[0].message.lower()


# ---------------------------------------------------------------------------
# Reporter QC summary integration test
# ---------------------------------------------------------------------------

class TestReporterQcSummary:

    def test_build_report_with_qc_summary(self):
        from geopipe_agent.engine.reporter import build_report

        step_reports = [
            {"id": "s1", "status": "success"},
            {
                "id": "s2",
                "status": "success",
                "issues_count": 2,
                "issues": [
                    {"rule_id": "geometry_validity", "severity": "error", "message": "a"},
                    {"rule_id": "geometry_validity", "severity": "warning", "message": "b"},
                ],
            },
            {
                "id": "s3",
                "status": "success",
                "issues_count": 1,
                "issues": [
                    {"rule_id": "attribute_completeness", "severity": "warning", "message": "c"},
                ],
            },
        ]

        report = build_report(
            pipeline_name="test-qc",
            status="success",
            duration=1.0,
            step_reports=step_reports,
        )

        assert "qc_summary" in report
        qc = report["qc_summary"]
        assert qc["total_issues"] == 3
        assert qc["by_severity"] == {"error": 1, "warning": 2}
        assert qc["by_rule"] == {"geometry_validity": 2, "attribute_completeness": 1}

    def test_build_report_without_qc(self):
        from geopipe_agent.engine.reporter import build_report

        step_reports = [{"id": "s1", "status": "success"}]
        report = build_report(
            pipeline_name="test",
            status="success",
            duration=1.0,
            step_reports=step_reports,
        )

        assert "qc_summary" not in report


# ---------------------------------------------------------------------------
# Registry integration: all QC steps registered
# ---------------------------------------------------------------------------

class TestQcStepsRegistered:

    def test_all_qc_steps_in_registry(self):
        expected_ids = [
            "qc.geometry_validity",
            "qc.topology",
            "qc.attribute_completeness",
            "qc.attribute_domain",
            "qc.value_range",
            "qc.duplicate_check",
            "qc.crs_check",
            "qc.raster_nodata",
            "qc.raster_value_range",
            "qc.raster_resolution",
        ]
        for step_id in expected_ids:
            assert registry.has(step_id), f"Step '{step_id}' not found in registry"

    def test_qc_category_count(self):
        qc_steps = registry.list_by_category("qc")
        assert len(qc_steps) == 10
