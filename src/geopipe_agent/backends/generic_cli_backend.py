"""Generic CLI backend — execute arbitrary command-line commands."""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
from typing import Any

from geopipe_agent.backends.base import GeoBackend

logger = logging.getLogger("geopipe_agent")


class GenericCliBackend(GeoBackend):
    """Backend for executing arbitrary command-line commands.

    Provides a flexible interface for running any CLI command, enabling users
    to integrate custom tools and scripts into their pipelines.

    Example usage within a step::

        result = backend.execute(["ls", "-la", "/data"])
        result = backend.execute("echo hello | tr a-z A-Z", shell=True)
    """

    # Default timeout for CLI commands (seconds)
    _TIMEOUT = 300

    def name(self) -> str:
        return "generic_cli"

    def is_available(self) -> bool:
        """Always available — any system has a shell."""
        return True

    def execute(
        self,
        command: str | list[str],
        *,
        timeout: int | None = None,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        shell: bool = False,
    ) -> dict[str, Any]:
        """Execute a command and return its output.

        Args:
            command: Command to execute.  Pass a list of strings for safe
                execution without a shell, or a single string with
                ``shell=True`` when pipes / redirects are needed.
            timeout: Maximum execution time in seconds (default 300).
            cwd: Working directory for the command.
            env: Additional environment variables (merged with current env).
            shell: If *True*, run via the system shell.  Necessary for
                pipes and redirects but the caller must handle escaping.

        Returns:
            A dict with keys ``stdout``, ``stderr``, and ``returncode``.

        Raises:
            RuntimeError: If the command times out.
            TypeError: If *command* type is invalid.
        """
        effective_timeout = timeout or self._TIMEOUT

        if isinstance(command, str) and not shell:
            # Split safely when not using shell mode
            command = shlex.split(command)
        elif isinstance(command, list) and shell:
            # Join for shell execution
            command = " ".join(shlex.quote(c) for c in command)
        elif not isinstance(command, (str, list)):
            raise TypeError(
                f"command must be a str or list[str], got {type(command).__name__}"
            )

        merged_env = None
        if env:
            merged_env = {**os.environ, **env}

        logger.info("GenericCLI executing: %s (shell=%s, cwd=%s)", command, shell, cwd)

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                cwd=cwd,
                env=merged_env,
                shell=shell,  # noqa: S603
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"Command timed out after {effective_timeout}s: {command}"
            ) from exc
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"Command not found: {command}"
            ) from exc

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
