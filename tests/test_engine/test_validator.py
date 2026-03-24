"""Tests for pipeline validator."""

import pytest

from geopipe_agent.engine.validator import validate_pipeline
from geopipe_agent.errors import PipelineValidationError
from geopipe_agent.models.pipeline import PipelineDefinition, StepDefinition


class TestValidatePipeline:
    def test_valid_pipeline(self):
        pipeline = PipelineDefinition(
            name="Test",
            steps=[
                StepDefinition(id="read", use="io.read_vector", params={"path": "test.shp"}),
                StepDefinition(
                    id="buffer",
                    use="vector.buffer",
                    params={"input": "$read.output", "distance": 500},
                ),
            ],
        )
        warnings = validate_pipeline(pipeline)
        assert isinstance(warnings, list)

    def test_invalid_step_id_with_dot(self):
        pipeline = PipelineDefinition(
            name="Test",
            steps=[
                StepDefinition(id="my.step", use="io.read_vector"),
            ],
        )
        with pytest.raises(PipelineValidationError, match="no dots"):
            validate_pipeline(pipeline)

    def test_invalid_step_id_with_uppercase(self):
        pipeline = PipelineDefinition(
            name="Test",
            steps=[
                StepDefinition(id="MyStep", use="io.read_vector"),
            ],
        )
        with pytest.raises(PipelineValidationError, match="invalid"):
            validate_pipeline(pipeline)

    def test_duplicate_step_id(self):
        pipeline = PipelineDefinition(
            name="Test",
            steps=[
                StepDefinition(id="read", use="io.read_vector", params={"path": "a.shp"}),
                StepDefinition(id="read", use="io.read_vector", params={"path": "b.shp"}),
            ],
        )
        with pytest.raises(PipelineValidationError, match="Duplicate"):
            validate_pipeline(pipeline)

    def test_unregistered_step(self):
        pipeline = PipelineDefinition(
            name="Test",
            steps=[
                StepDefinition(id="step1", use="nonexistent.step"),
            ],
        )
        with pytest.raises(PipelineValidationError, match="not registered"):
            validate_pipeline(pipeline)

    def test_invalid_step_reference(self):
        pipeline = PipelineDefinition(
            name="Test",
            steps=[
                StepDefinition(
                    id="buffer",
                    use="vector.buffer",
                    params={"input": "$nonexistent.output", "distance": 100},
                ),
            ],
        )
        with pytest.raises(PipelineValidationError, match="not been defined"):
            validate_pipeline(pipeline)

    def test_undefined_variable(self):
        pipeline = PipelineDefinition(
            name="Test",
            variables={},
            steps=[
                StepDefinition(
                    id="read",
                    use="io.read_vector",
                    params={"path": "${missing_var}"},
                ),
            ],
        )
        with pytest.raises(PipelineValidationError, match="not defined"):
            validate_pipeline(pipeline)

    def test_valid_variable_reference(self):
        pipeline = PipelineDefinition(
            name="Test",
            variables={"input_path": "data/test.shp"},
            steps=[
                StepDefinition(
                    id="read",
                    use="io.read_vector",
                    params={"path": "${input_path}"},
                ),
            ],
        )
        warnings = validate_pipeline(pipeline)
        assert isinstance(warnings, list)

    def test_invalid_on_error(self):
        pipeline = PipelineDefinition(
            name="Test",
            steps=[
                StepDefinition(
                    id="read",
                    use="io.read_vector",
                    params={"path": "test.shp"},
                    on_error="invalid",
                ),
            ],
        )
        with pytest.raises(PipelineValidationError, match="on_error"):
            validate_pipeline(pipeline)

    def test_invalid_output_reference(self):
        pipeline = PipelineDefinition(
            name="Test",
            steps=[
                StepDefinition(id="read", use="io.read_vector", params={"path": "test.shp"}),
            ],
            outputs={"result": "$nonexistent.output"},
        )
        with pytest.raises(PipelineValidationError, match="does not exist"):
            validate_pipeline(pipeline)
