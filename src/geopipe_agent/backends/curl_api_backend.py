"""Curl API backend — web API access via the curl command."""

from __future__ import annotations

import json
import logging
import shlex
import shutil
import subprocess
from typing import Any

from geopipe_agent.backends.base import GeoBackend

logger = logging.getLogger("geopipe_agent")


class CurlApiBackend(GeoBackend):
    """Backend for making HTTP requests via the ``curl`` command.

    Enables pipelines to call web APIs, download data, or interact with
    remote services.  Parameters are assembled into a safe ``curl``
    invocation so that users don't need to construct raw command strings.

    Example usage within a step::

        result = backend.request("https://api.example.com/data")
        result = backend.request(
            "https://api.example.com/submit",
            method="POST",
            headers={"Content-Type": "application/json"},
            data='{"key": "value"}',
        )
    """

    # Default timeout for HTTP requests (seconds)
    _TIMEOUT = 30

    def name(self) -> str:
        return "curl_api"

    def is_available(self) -> bool:
        """Available when ``curl`` is installed on the system."""
        return shutil.which("curl") is not None

    def request(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        data: str | None = None,
        timeout: int | None = None,
        output: str | None = None,
        extra_args: list[str] | None = None,
        insecure: bool = False,
    ) -> dict[str, Any]:
        """Execute an HTTP request via ``curl``.

        Args:
            url: The request URL.
            method: HTTP method (GET, POST, PUT, DELETE, PATCH, etc.).
            headers: HTTP headers as a dict.
            data: Request body (typically JSON or form data).
            timeout: Maximum time in seconds for the request (default 30).
            output: Optional file path to save the response body to.
            extra_args: Additional raw curl arguments for advanced usage.
            insecure: If *True*, skip TLS certificate verification
                (``--insecure``).  Use only for development / testing.

        Returns:
            A dict with keys ``status_code`` (int), ``headers`` (dict),
            ``body`` (str), ``stderr`` (str), and ``returncode`` (int).

        Raises:
            RuntimeError: If curl times out or is not found.
            ValueError: If the *url* is empty.
        """
        if not url or not url.strip():
            raise ValueError("url must not be empty")

        effective_timeout = timeout or self._TIMEOUT

        cmd: list[str] = [
            "curl",
            "--silent",                 # suppress progress bar
            "--show-error",             # still show errors
            "--dump-header", "-",       # dump response headers to stdout
            "--max-time", str(effective_timeout),
            "-X", method.upper(),
        ]

        if insecure:
            cmd.append("--insecure")

        if headers:
            for key, value in headers.items():
                cmd.extend(["-H", f"{key}: {value}"])

        if data is not None:
            cmd.extend(["-d", data])

        if output:
            cmd.extend(["-o", output])

        if extra_args:
            cmd.extend(extra_args)

        cmd.append(url)

        logger.info("CurlAPI executing: %s", " ".join(shlex.quote(c) for c in cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=effective_timeout + 5,  # small grace period beyond curl's own timeout
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"curl request timed out after {effective_timeout}s: {url}"
            ) from exc
        except FileNotFoundError as exc:
            raise RuntimeError(
                "curl is not installed or not on PATH"
            ) from exc

        status_code, resp_headers, body = self._parse_response(result.stdout)

        return {
            "status_code": status_code,
            "headers": resp_headers,
            "body": body,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

    def request_json(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        data: Any = None,
        timeout: int | None = None,
        extra_args: list[str] | None = None,
        insecure: bool = False,
    ) -> dict[str, Any]:
        """Convenience wrapper: send / receive JSON.

        Automatically sets ``Content-Type`` and ``Accept`` headers and
        serializes *data* as JSON.  The response body is parsed as JSON.
        """
        merged_headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if headers:
            merged_headers.update(headers)

        body_str = json.dumps(data) if data is not None else None

        result = self.request(
            url,
            method=method,
            headers=merged_headers,
            data=body_str,
            timeout=timeout,
            extra_args=extra_args,
            insecure=insecure,
        )

        # Attempt to parse response body as JSON
        if result["body"]:
            try:
                result["json"] = json.loads(result["body"])
            except (json.JSONDecodeError, ValueError):
                result["json"] = None
        else:
            result["json"] = None

        return result

    # -- internal helpers -----------------------------------------------------

    @staticmethod
    def _parse_response(raw: str) -> tuple[int, dict[str, str], str]:
        """Parse curl ``--dump-header -`` output into status, headers, body."""
        status_code = 0
        resp_headers: dict[str, str] = {}
        body = raw  # fallback: entire output is the body

        # curl dumps headers followed by a blank line, then the body.
        # With redirects there may be multiple header blocks; we want the last.
        parts = raw.split("\r\n\r\n")
        if len(parts) < 2:
            # Try \n\n as fallback (some curl builds on certain platforms)
            parts = raw.split("\n\n")

        if len(parts) >= 2:
            # Last part is body; second-to-last is the final header block
            body = parts[-1]
            header_block = parts[-2]
            for line in header_block.splitlines():
                if line.startswith("HTTP/"):
                    # e.g. "HTTP/1.1 200 OK" or "HTTP/2 200"
                    parts_status = line.split(None, 2)
                    if len(parts_status) >= 2:
                        try:
                            status_code = int(parts_status[1])
                        except ValueError:
                            pass
                elif ":" in line:
                    key, _, value = line.partition(":")
                    resp_headers[key.strip()] = value.strip()

        return status_code, resp_headers, body
