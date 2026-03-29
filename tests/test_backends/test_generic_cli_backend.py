"""Tests for GenericCliBackend."""

from __future__ import annotations

import os
import pytest

from geopipe_agent.backends.generic_cli_backend import GenericCliBackend


class TestGenericCliBackend:
    @pytest.fixture
    def backend(self):
        return GenericCliBackend()

    def test_name(self, backend):
        assert backend.name() == "generic_cli"

    def test_is_available(self, backend):
        assert backend.is_available() is True

    # -- execute (list form) --------------------------------------------------

    def test_execute_list_success(self, backend):
        result = backend.execute(["echo", "hello"])
        assert result["returncode"] == 0
        assert result["stdout"].strip() == "hello"
        assert isinstance(result["stderr"], str)

    def test_execute_list_with_args(self, backend):
        result = backend.execute(["printf", "%s %s", "foo", "bar"])
        assert result["returncode"] == 0
        assert result["stdout"] == "foo bar"

    # -- execute (string form, no shell) --------------------------------------

    def test_execute_string_no_shell(self, backend):
        """String commands are shlex-split when shell=False."""
        result = backend.execute("echo hello world")
        assert result["returncode"] == 0
        assert result["stdout"].strip() == "hello world"

    # -- execute (shell mode) -------------------------------------------------

    def test_execute_shell_mode(self, backend):
        result = backend.execute("echo hello | tr a-z A-Z", shell=True)
        assert result["returncode"] == 0
        assert result["stdout"].strip() == "HELLO"

    def test_execute_list_shell_mode(self, backend):
        """List is joined safely when shell=True."""
        result = backend.execute(["echo", "hello world"], shell=True)
        assert result["returncode"] == 0
        assert "hello world" in result["stdout"]

    # -- working directory & env ----------------------------------------------

    def test_execute_cwd(self, backend, tmp_path):
        result = backend.execute(["pwd"], cwd=str(tmp_path))
        assert result["returncode"] == 0
        assert result["stdout"].strip() == str(tmp_path)

    def test_execute_env(self, backend):
        result = backend.execute(
            "echo $MY_TEST_VAR",
            shell=True,
            env={"MY_TEST_VAR": "test_value"},
        )
        assert result["returncode"] == 0
        assert result["stdout"].strip() == "test_value"

    # -- non-zero exit --------------------------------------------------------

    def test_execute_nonzero_exit(self, backend):
        result = backend.execute(["false"])
        assert result["returncode"] != 0

    # -- timeout --------------------------------------------------------------

    def test_execute_timeout(self, backend):
        with pytest.raises(RuntimeError, match="timed out"):
            backend.execute(["sleep", "10"], timeout=1)

    # -- command not found ----------------------------------------------------

    def test_execute_command_not_found(self, backend):
        with pytest.raises(RuntimeError, match="Command not found"):
            backend.execute(["__nonexistent_command_xyz__"])

    # -- invalid command type -------------------------------------------------

    def test_execute_invalid_type(self, backend):
        with pytest.raises(TypeError, match="must be a str or list"):
            backend.execute(12345)  # type: ignore[arg-type]

    # -- GIS operations not supported -----------------------------------------

    def test_gis_ops_not_supported(self, backend):
        for method_name in ("buffer", "clip", "reproject", "dissolve", "simplify", "overlay"):
            with pytest.raises(NotImplementedError, match="not supported"):
                getattr(backend, method_name)(None, None)
