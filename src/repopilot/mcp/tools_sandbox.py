"""MCP tool for invoking isolated Docker test runner."""

from __future__ import annotations

from pathlib import Path

from repopilot.agents.state import SandboxTestResult
from repopilot.core.exceptions import SandboxExecutionError
from repopilot.core.result import Result
from repopilot.sandbox.runner import DockerSandboxRunner


def run_isolated_tests_tool(
    repo_root: Path | str,
    test_path: str | None = None,
    timeout_seconds: int = 60,
    runner: DockerSandboxRunner | None = None,
) -> Result[SandboxTestResult, SandboxExecutionError]:
    """Execute pytest inside an isolated sandbox container and return structured results."""
    active_runner = runner or DockerSandboxRunner()
    return active_runner.run_tests(
        repo_path=repo_root,
        test_path=test_path,
        timeout_seconds=timeout_seconds,
    )
