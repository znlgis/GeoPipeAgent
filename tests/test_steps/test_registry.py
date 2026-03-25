"""Tests for step registry and decorators."""

import pytest

from geopipe_agent.steps.registry import StepInfo, step
from geopipe_agent.steps import registry


class TestStepRegistry:
    def test_list_all(self):
        all_steps = registry.list_all()
        # Should have all the built-in steps
        assert len(all_steps) >= 11
        step_ids = [s.id for s in all_steps]
        assert "io.read_vector" in step_ids
        assert "vector.buffer" in step_ids

    def test_get_step(self):
        info = registry.get("vector.buffer")
        assert info is not None
        assert info.id == "vector.buffer"
        assert info.category == "vector"

    def test_get_nonexistent(self):
        assert registry.get("nonexistent.step") is None

    def test_has_step(self):
        assert registry.has("io.read_vector")
        assert not registry.has("nonexistent")

    def test_categories(self):
        cats = registry.categories()
        assert "io" in cats
        assert "vector" in cats

    def test_list_by_category(self):
        io_steps = registry.list_by_category("io")
        assert len(io_steps) >= 4
        assert all(s.category == "io" for s in io_steps)


class TestStepDecorator:
    def test_decorator_registers_step(self):
        initial_count = len(registry.list_all())

        @step(
            id="test.custom_step",
            name="Custom Test Step",
            description="A test step",
            category="test",
            params={"input": {"type": "string", "required": True}},
        )
        def custom_step(ctx):
            return None

        assert registry.has("test.custom_step")
        info = registry.get("test.custom_step")
        assert info.name == "Custom Test Step"
        assert info.func is custom_step
        assert len(registry.list_all()) == initial_count + 1

    def test_decorator_auto_category(self):
        @step(id="autocat.test_step")
        def auto_step(ctx):
            return None

        info = registry.get("autocat.test_step")
        assert info.category == "autocat"

    def test_step_info_to_dict(self):
        info = registry.get("vector.buffer")
        d = info.to_dict()
        assert d["id"] == "vector.buffer"
        assert "params" in d
        assert "outputs" in d
