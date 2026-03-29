"""Tests for CurlApiBackend."""

from __future__ import annotations

import json
import shutil
from unittest import mock

import pytest

from geopipe_agent.backends.curl_api_backend import CurlApiBackend


curl_available = shutil.which("curl") is not None
pytestmark = pytest.mark.skipif(not curl_available, reason="curl not installed")


class TestCurlApiBackend:
    @pytest.fixture
    def backend(self):
        return CurlApiBackend()

    def test_name(self, backend):
        assert backend.name() == "curl_api"

    def test_is_available(self, backend):
        assert backend.is_available() is True

    # -- _parse_response ------------------------------------------------------

    def test_parse_response_basic(self):
        raw = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/json\r\n"
            "\r\n"
            '{"key": "value"}'
        )
        status, headers, body = CurlApiBackend._parse_response(raw)
        assert status == 200
        assert headers["Content-Type"] == "application/json"
        assert body == '{"key": "value"}'

    def test_parse_response_with_redirect(self):
        raw = (
            "HTTP/1.1 301 Moved\r\n"
            "Location: https://example.com/new\r\n"
            "\r\n"
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html\r\n"
            "\r\n"
            "<html>ok</html>"
        )
        status, headers, body = CurlApiBackend._parse_response(raw)
        assert status == 200
        assert headers["Content-Type"] == "text/html"
        assert body == "<html>ok</html>"

    def test_parse_response_no_headers(self):
        raw = "just body content"
        status, headers, body = CurlApiBackend._parse_response(raw)
        assert status == 0
        assert headers == {}
        assert body == "just body content"

    def test_parse_response_http2(self):
        raw = (
            "HTTP/2 204\r\n"
            "\r\n"
            ""
        )
        status, headers, body = CurlApiBackend._parse_response(raw)
        assert status == 204

    # -- request validation ---------------------------------------------------

    def test_request_empty_url(self, backend):
        with pytest.raises(ValueError, match="url must not be empty"):
            backend.request("")

    def test_request_blank_url(self, backend):
        with pytest.raises(ValueError, match="url must not be empty"):
            backend.request("   ")

    # -- request with mocked subprocess ---------------------------------------

    def test_request_get(self, backend):
        mock_stdout = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/plain\r\n"
            "\r\n"
            "Hello"
        )
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(
                stdout=mock_stdout, stderr="", returncode=0,
            )
            result = backend.request("https://example.com/api")

        assert result["status_code"] == 200
        assert result["body"] == "Hello"
        assert result["returncode"] == 0

        # Verify curl was called with correct args
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "curl"
        assert "-X" in call_args
        idx = call_args.index("-X")
        assert call_args[idx + 1] == "GET"
        assert "https://example.com/api" in call_args

    def test_request_post_with_data(self, backend):
        mock_stdout = "HTTP/1.1 201 Created\r\n\r\n{}"
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(
                stdout=mock_stdout, stderr="", returncode=0,
            )
            result = backend.request(
                "https://example.com/api",
                method="POST",
                headers={"Content-Type": "application/json"},
                data='{"key":"value"}',
            )

        assert result["status_code"] == 201
        call_args = mock_run.call_args[0][0]
        assert "-X" in call_args
        idx = call_args.index("-X")
        assert call_args[idx + 1] == "POST"
        assert "-d" in call_args
        d_idx = call_args.index("-d")
        assert call_args[d_idx + 1] == '{"key":"value"}'

    def test_request_with_headers(self, backend):
        mock_stdout = "HTTP/1.1 200 OK\r\n\r\nok"
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(
                stdout=mock_stdout, stderr="", returncode=0,
            )
            backend.request(
                "https://example.com",
                headers={"Authorization": "Bearer token123", "Accept": "text/html"},
            )

        call_args = mock_run.call_args[0][0]
        h_indices = [i for i, a in enumerate(call_args) if a == "-H"]
        header_values = [call_args[i + 1] for i in h_indices]
        assert "Authorization: Bearer token123" in header_values
        assert "Accept: text/html" in header_values

    def test_request_insecure(self, backend):
        mock_stdout = "HTTP/1.1 200 OK\r\n\r\nok"
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(
                stdout=mock_stdout, stderr="", returncode=0,
            )
            backend.request("https://example.com", insecure=True)

        call_args = mock_run.call_args[0][0]
        assert "--insecure" in call_args

    def test_request_extra_args(self, backend):
        mock_stdout = "HTTP/1.1 200 OK\r\n\r\nok"
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(
                stdout=mock_stdout, stderr="", returncode=0,
            )
            backend.request("https://example.com", extra_args=["--compressed", "-L"])

        call_args = mock_run.call_args[0][0]
        assert "--compressed" in call_args
        assert "-L" in call_args

    def test_request_output_file(self, backend, tmp_path):
        mock_stdout = "HTTP/1.1 200 OK\r\n\r\n"
        output_file = str(tmp_path / "output.json")
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(
                stdout=mock_stdout, stderr="", returncode=0,
            )
            backend.request("https://example.com/data", output=output_file)

        call_args = mock_run.call_args[0][0]
        assert "-o" in call_args
        o_idx = call_args.index("-o")
        assert call_args[o_idx + 1] == output_file

    # -- request_json ---------------------------------------------------------

    def test_request_json_get(self, backend):
        mock_stdout = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/json\r\n"
            "\r\n"
            '{"result": 42}'
        )
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(
                stdout=mock_stdout, stderr="", returncode=0,
            )
            result = backend.request_json("https://example.com/api")

        assert result["status_code"] == 200
        assert result["json"] == {"result": 42}

    def test_request_json_post(self, backend):
        mock_stdout = (
            "HTTP/1.1 200 OK\r\n\r\n"
            '{"ok": true}'
        )
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(
                stdout=mock_stdout, stderr="", returncode=0,
            )
            result = backend.request_json(
                "https://example.com/api",
                method="POST",
                data={"input": "test"},
            )

        assert result["json"] == {"ok": True}
        call_args = mock_run.call_args[0][0]
        d_idx = call_args.index("-d")
        sent_data = json.loads(call_args[d_idx + 1])
        assert sent_data == {"input": "test"}

    def test_request_json_invalid_response(self, backend):
        mock_stdout = "HTTP/1.1 200 OK\r\n\r\nnot json"
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(
                stdout=mock_stdout, stderr="", returncode=0,
            )
            result = backend.request_json("https://example.com/api")

        assert result["json"] is None

    # -- timeout & error handling ---------------------------------------------

    def test_request_timeout(self, backend):
        import subprocess
        with mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("curl", 30)):
            with pytest.raises(RuntimeError, match="timed out"):
                backend.request("https://example.com", timeout=30)

    def test_request_curl_not_found(self, backend):
        with mock.patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(RuntimeError, match="curl is not installed"):
                backend.request("https://example.com")

    # -- GIS operations not supported -----------------------------------------

    def test_gis_ops_not_supported(self, backend):
        for method_name in ("buffer", "clip", "reproject", "dissolve", "simplify", "overlay"):
            with pytest.raises(NotImplementedError, match="not supported"):
                getattr(backend, method_name)(None, None)
