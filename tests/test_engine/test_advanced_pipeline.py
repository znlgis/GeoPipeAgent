"""Tests for advanced pipeline features (when, retry)."""

import pytest
from unittest.mock import MagicMock, patch

from geopipe_agent.engine.executor import execute_pipeline, _evaluate_condition
from geopipe_agent.engine.context import PipelineContext
from geopipe_agent.models.pipeline import PipelineDefinition, StepDefinition
from geopipe_agent.models.result import StepResult


class TestWhenCondition:
    def test_evaluate_true(self):
        context = PipelineContext(variables={"flag": True})
        assert _evaluate_condition("${flag}", context) is True

    def test_evaluate_false(self):
        context = PipelineContext(variables={"flag": False})
        assert _evaluate_condition("${flag}", context) is False

    def test_evaluate_comparison(self):
        context = PipelineContext(variables={"count": 10})
        assert _evaluate_condition("${count} > 5", context) is True
        assert _evaluate_condition("${count} < 5", context) is False

    def test_evaluate_step_ref(self):
        context = PipelineContext(variables={})
        context.set_output("step1", StepResult(output="data", stats={"feature_count": 42}))
        assert _evaluate_condition("$step1.feature_count > 10", context) is True
        assert _evaluate_condition("$step1.feature_count < 10", context) is False

    def test_evaluate_invalid_returns_false(self):
        context = PipelineContext(variables={})
        assert _evaluate_condition("some invalid expression!!!", context) is False

    def test_when_skips_step(self):
        """Test that a step with when=False is skipped."""
        pipeline = PipelineDefinition(
            name="test-when",
            steps=[
                StepDefinition(
                    id="read",
                    use="io.read_vector",
                    params={"path": "/dummy"},
                    when="${skip_it}",
                ),
            ],
            variables={"skip_it": False},
            outputs={},
        )

        report = execute_pipeline(pipeline)
        assert report["steps"][0]["status"] == "skipped"
        assert "condition not met" in report["steps"][0]["skip_reason"]


class TestRetryLogic:
    def test_retry_succeeds_on_second_attempt(self):
        """Test that on_error=retry actually retries."""
        call_count = {"n": 0}
        original_resolve = None

        def flaky_step(ctx):
            call_count["n"] += 1
            if call_count["n"] < 2:
                raise RuntimeError("Transient error")
            return StepResult(output="ok")

        from geopipe_agent.steps.registry import StepRegistry, StepInfo

        registry = StepRegistry()
        # Register a flaky test step
        info = StepInfo(
            id="test.flaky",
            func=flaky_step,
            name="Flaky Step",
            category="io",  # io category to skip backend
        )
        registry.register(info)

        pipeline = PipelineDefinition(
            name="test-retry",
            steps=[
                StepDefinition(
                    id="flaky",
                    use="test.flaky",
                    params={},
                    on_error="retry",
                ),
            ],
            variables={},
            outputs={},
        )

        report = execute_pipeline(pipeline)
        assert report["steps"][0]["status"] == "success"
        assert report["steps"][0].get("retries", 0) >= 1
        assert call_count["n"] >= 2

    def test_retry_exhausts_and_fails(self):
        """Test that retry gives up after max attempts."""

        def always_fail_step(ctx):
            raise RuntimeError("Permanent error")

        from geopipe_agent.steps.registry import StepRegistry, StepInfo
        from geopipe_agent.errors import StepExecutionError

        registry = StepRegistry()
        info = StepInfo(
            id="test.always_fail",
            func=always_fail_step,
            name="Always Fail",
            category="io",
        )
        registry.register(info)

        pipeline = PipelineDefinition(
            name="test-retry-fail",
            steps=[
                StepDefinition(
                    id="failing",
                    use="test.always_fail",
                    params={},
                    on_error="retry",
                ),
            ],
            variables={},
            outputs={},
        )

        with pytest.raises(StepExecutionError, match="Permanent error"):
            execute_pipeline(pipeline)
