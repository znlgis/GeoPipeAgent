"""Tests for pipeline executor — end-to-end pipeline execution."""

import pytest
import geopandas as gpd
from shapely.geometry import Point

from geopipe_agent.engine.parser import parse_yaml
from geopipe_agent.engine.validator import validate_pipeline
from geopipe_agent.engine.executor import execute_pipeline
from geopipe_agent.errors import StepExecutionError


class TestExecutePipeline:
    def test_read_buffer_write_pipeline(self, tmp_path, sample_points_gdf):
        """End-to-end test: read → buffer → write."""
        # Write test data
        input_path = tmp_path / "input.geojson"
        sample_points_gdf.to_file(str(input_path), driver="GeoJSON")

        output_path = tmp_path / "output.geojson"

        yaml_str = f"""
pipeline:
  name: "E2E Test"
  steps:
    - id: read
      use: io.read_vector
      params:
        path: "{input_path}"
    - id: buffer
      use: vector.buffer
      params:
        input: "$read.output"
        distance: 0.1
    - id: save
      use: io.write_vector
      params:
        input: "$buffer.output"
        path: "{output_path}"
  outputs:
    result: "$save.output"
    stats: "$buffer.stats"
"""
        pipeline = parse_yaml(yaml_str)
        validate_pipeline(pipeline)
        report = execute_pipeline(pipeline)

        assert report["status"] == "success"
        assert report["pipeline"] == "E2E Test"
        assert len(report["steps"]) == 3
        assert all(s["status"] == "success" for s in report["steps"])
        assert report["outputs"]["result"] == str(output_path)
        assert output_path.exists()

        # Read back and verify
        result_gdf = gpd.read_file(str(output_path))
        assert len(result_gdf) == 3  # Same count as input

    def test_pipeline_with_variables(self, tmp_path, sample_points_gdf):
        """Test variable substitution in pipeline."""
        input_path = tmp_path / "input.geojson"
        sample_points_gdf.to_file(str(input_path), driver="GeoJSON")
        output_path = tmp_path / "output.geojson"

        yaml_str = f"""
pipeline:
  name: "Variable Test"
  variables:
    input_path: "{input_path}"
    output_path: "{output_path}"
    buffer_dist: 0.05
  steps:
    - id: read
      use: io.read_vector
      params:
        path: "${{input_path}}"
    - id: buffer
      use: vector.buffer
      params:
        input: "$read.output"
        distance: "${{buffer_dist}}"
    - id: save
      use: io.write_vector
      params:
        input: "$buffer.output"
        path: "${{output_path}}"
"""
        pipeline = parse_yaml(yaml_str)
        validate_pipeline(pipeline)
        report = execute_pipeline(pipeline)

        assert report["status"] == "success"
        assert output_path.exists()

    def test_pipeline_with_query_step(self, tmp_path, sample_points_gdf):
        """Test query/filter step."""
        input_path = tmp_path / "input.geojson"
        sample_points_gdf.to_file(str(input_path), driver="GeoJSON")

        yaml_str = f"""
pipeline:
  name: "Query Test"
  steps:
    - id: read
      use: io.read_vector
      params:
        path: "{input_path}"
    - id: filter
      use: vector.query
      params:
        input: "$read.output"
        expression: "value > 15"
"""
        pipeline = parse_yaml(yaml_str)
        validate_pipeline(pipeline)
        report = execute_pipeline(pipeline)

        assert report["status"] == "success"
        # Should filter to only B and C (values 20 and 30)
        filter_step = report["steps"][1]
        assert filter_step["output_summary"]["output_count"] == 2

    def test_step_execution_error(self, tmp_path):
        """Test error handling when a step fails."""
        yaml_str = f"""
pipeline:
  name: "Error Test"
  steps:
    - id: read
      use: io.read_vector
      params:
        path: "{tmp_path}/nonexistent.shp"
"""
        pipeline = parse_yaml(yaml_str)
        validate_pipeline(pipeline)
        with pytest.raises(StepExecutionError) as exc_info:
            execute_pipeline(pipeline)
        assert exc_info.value.step_id == "read"

    def test_skip_on_error(self, tmp_path):
        """Test on_error=skip behavior."""
        yaml_str = f"""
pipeline:
  name: "Skip Error Test"
  steps:
    - id: bad-step
      use: io.read_vector
      on_error: skip
      params:
        path: "{tmp_path}/nonexistent.shp"
"""
        pipeline = parse_yaml(yaml_str)
        validate_pipeline(pipeline)
        report = execute_pipeline(pipeline)
        assert report["status"] == "success"
        assert report["steps"][0]["status"] == "skipped"
