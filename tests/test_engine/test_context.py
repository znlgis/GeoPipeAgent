"""Tests for pipeline context and resolver."""

import pytest

from geopipe_agent.engine.context import PipelineContext, StepContext
from geopipe_agent.models.result import StepResult
from geopipe_agent.errors import VariableResolutionError


class TestPipelineContext:
    def test_resolve_variable(self):
        ctx = PipelineContext(variables={"path": "/data/test.shp"})
        assert ctx.resolve("${path}") == "/data/test.shp"

    def test_resolve_numeric_variable(self):
        ctx = PipelineContext(variables={"distance": 500})
        result = ctx.resolve("${distance}")
        assert result == 500

    def test_resolve_embedded_variable(self):
        ctx = PipelineContext(variables={"name": "roads"})
        result = ctx.resolve("data/${name}.shp")
        assert result == "data/roads.shp"

    def test_resolve_step_reference(self):
        ctx = PipelineContext()
        ctx.set_output("read", StepResult(output="test_data"))
        result = ctx.resolve("$read.output")
        assert result == "test_data"

    def test_resolve_step_stats(self):
        ctx = PipelineContext()
        ctx.set_output("buffer", StepResult(stats={"feature_count": 42}))
        result = ctx.resolve("$buffer.feature_count")
        assert result == 42

    def test_undefined_variable_raises(self):
        ctx = PipelineContext(variables={})
        with pytest.raises(VariableResolutionError, match="not defined"):
            ctx.resolve("${undefined}")

    def test_undefined_step_reference_raises(self):
        ctx = PipelineContext()
        with pytest.raises(VariableResolutionError, match="no output"):
            ctx.resolve("$missing.output")

    def test_invalid_step_reference_format(self):
        ctx = PipelineContext()
        with pytest.raises(VariableResolutionError, match="Expected format"):
            ctx.resolve("$nostep")

    def test_plain_value_passthrough(self):
        ctx = PipelineContext()
        assert ctx.resolve(42) == 42
        assert ctx.resolve("plain") == "plain"
        assert ctx.resolve(None) is None

    def test_resolve_params(self):
        ctx = PipelineContext(variables={"dist": 100})
        ctx.set_output("read", StepResult(output="gdf"))
        resolved = ctx.resolve_params({
            "input": "$read.output",
            "distance": "${dist}",
            "cap_style": "round",
        })
        assert resolved["input"] == "gdf"
        assert resolved["distance"] == 100
        assert resolved["cap_style"] == "round"


class TestStepContext:
    def test_param_access(self):
        ctx = StepContext(params={"distance": 500, "cap_style": "round"})
        assert ctx.param("distance") == 500
        assert ctx.param("cap_style") == "round"
        assert ctx.param("missing", "default") == "default"

    def test_input_shortcut(self):
        ctx = StepContext(params={"input": "data"})
        assert ctx.input() == "data"
