"""Tests for YAML pipeline parser."""

import pytest

from geopipe_agent.engine.parser import parse_yaml
from geopipe_agent.errors import PipelineParseError


class TestParseYaml:
    def test_parse_simple_pipeline(self, tmp_path):
        yaml_content = """
pipeline:
  name: "Test Pipeline"
  description: "A test pipeline"
  steps:
    - id: read
      use: io.read_vector
      params:
        path: "data/test.shp"
    - id: buffer
      use: vector.buffer
      params:
        input: "$read.output"
        distance: 500
"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)

        pipeline = parse_yaml(str(yaml_file))
        assert pipeline.name == "Test Pipeline"
        assert pipeline.description == "A test pipeline"
        assert len(pipeline.steps) == 2
        assert pipeline.steps[0].id == "read"
        assert pipeline.steps[0].use == "io.read_vector"
        assert pipeline.steps[1].params["distance"] == 500

    def test_parse_from_string(self):
        yaml_str = """
pipeline:
  name: "String Pipeline"
  steps:
    - id: step1
      use: io.read_vector
      params:
        path: "test.shp"
"""
        pipeline = parse_yaml(yaml_str)
        assert pipeline.name == "String Pipeline"
        assert len(pipeline.steps) == 1

    def test_parse_with_variables(self):
        yaml_str = """
pipeline:
  name: "Var Pipeline"
  variables:
    input_path: "data/roads.shp"
    buffer_dist: 500
  steps:
    - id: read
      use: io.read_vector
      params:
        path: "${input_path}"
"""
        pipeline = parse_yaml(yaml_str)
        assert pipeline.variables["input_path"] == "data/roads.shp"
        assert pipeline.variables["buffer_dist"] == 500

    def test_parse_with_outputs(self):
        yaml_str = """
pipeline:
  name: "Output Pipeline"
  steps:
    - id: read
      use: io.read_vector
      params:
        path: "test.shp"
  outputs:
    result: "$read.output"
"""
        pipeline = parse_yaml(yaml_str)
        assert pipeline.outputs["result"] == "$read.output"

    def test_missing_pipeline_key(self):
        with pytest.raises(PipelineParseError, match="Missing 'pipeline' key"):
            parse_yaml("steps: []")

    def test_missing_steps(self):
        with pytest.raises(PipelineParseError, match="non-empty list"):
            parse_yaml("pipeline:\n  name: test\n  steps: []")

    def test_missing_step_id(self):
        yaml_str = """
pipeline:
  name: test
  steps:
    - use: io.read_vector
"""
        with pytest.raises(PipelineParseError, match="missing required 'id'"):
            parse_yaml(yaml_str)

    def test_missing_step_use(self):
        yaml_str = """
pipeline:
  name: test
  steps:
    - id: step1
"""
        with pytest.raises(PipelineParseError, match="missing required 'use'"):
            parse_yaml(yaml_str)

    def test_on_error_and_backend(self):
        yaml_str = """
pipeline:
  name: test
  steps:
    - id: step1
      use: vector.buffer
      on_error: skip
      backend: qgis_process
      params:
        input: "test"
        distance: 100
"""
        pipeline = parse_yaml(yaml_str)
        assert pipeline.steps[0].on_error == "skip"
        assert pipeline.steps[0].backend == "qgis_process"
