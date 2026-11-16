"""Unit tests for RepoPilot CLI commands."""

from unittest.mock import patch

from typer.testing import CliRunner

from repopilot.cli import app

runner = CliRunner()


def test_cli_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "RepoPilot v0.1.0" in result.stdout


def test_cli_server_invocation() -> None:
    with patch("uvicorn.run") as mock_run:
        result = runner.invoke(app, ["server", "--port", "9000"])
        assert result.exit_code == 0
        mock_run.assert_called_once_with(
            "repopilot.server.app:app", host="127.0.0.1", port=9000, reload=False
        )


def test_cli_mcp_invocation() -> None:
    with patch("repopilot.cli.run_mcp_server") as mock_mcp:
        result = runner.invoke(app, ["mcp"])
        assert result.exit_code == 0
        mock_mcp.assert_called_once()
