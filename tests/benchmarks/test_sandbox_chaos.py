"""Sandbox Chaos and Security Hardening Test Suite for RepoPilot.

Validates that the execution sandbox resists adversarial conditions:
1. Infinite loops and thread exhaustion terminated via strict timeouts.
2. Path traversal attacks (relative paths, symlink escapes) securely blocked.
3. Syntax corruption and parser bombs quarantined prior to disk writes.
4. Hard resource constraints (memory, CPU, network isolation) enforced on Docker containers.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from repopilot.ast.parser import TreeSitterParser
from repopilot.core.exceptions import (
    DiffApplicationError,
    RepoPilotError,
    SandboxExecutionError,
    SandboxTimeoutError,
)
from repopilot.mcp.tools_file import apply_unified_diff, read_file_range
from repopilot.sandbox.runner import DockerSandboxRunner


def test_chaos_timeout_guard_terminates_infinite_loop(tmp_path: Path) -> None:
    """Chaos: Verify sandbox timeout cleanly terminates hanging or looping commands."""
    runner = DockerSandboxRunner(allow_fallback=True)

    with (
        patch.object(runner, "_get_client", return_value=None),
        patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["pytest", "-v"], timeout=2),
        ),
    ):
        result = runner.run_tests(repo_path=tmp_path, timeout_seconds=2)
        assert result.is_err
        err = result.unwrap_err()
        assert isinstance(err, SandboxTimeoutError)
        assert "exceeded 2s timeout" in err.message


def test_chaos_docker_container_timeout_and_cleanup(tmp_path: Path) -> None:
    """Chaos: Verify Docker container timeout triggers forced container removal."""
    mock_client = MagicMock()
    mock_container = MagicMock()
    mock_container.wait.side_effect = TimeoutError("Container timed out")
    mock_client.containers.run.return_value = mock_container

    runner = DockerSandboxRunner(docker_client=mock_client)
    result = runner.run_tests(repo_path=tmp_path, timeout_seconds=10)

    assert result.is_err
    err = result.unwrap_err()
    assert isinstance(err, SandboxTimeoutError)
    assert "exceeded 10s timeout" in err.message

    # Ensure container was killed/removed on timeout
    mock_container.remove.assert_called_once_with(force=True)


def test_chaos_path_traversal_exploit_prevented(tmp_path: Path) -> None:
    """Chaos: Directory traversal attempts outside repo root are rejected."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    secret_dir = tmp_path / "secret"
    secret_dir.mkdir()
    secret_file = secret_dir / "keys.env"
    secret_file.write_text("API_SECRET_KEY=adversarial_token\n", encoding="utf-8")

    # 1. Attempt to read outside repo root via read_file_range
    read_res = read_file_range(
        repo_root=repo_dir,
        relative_path="../../secret/keys.env",
        start_line=1,
        end_line=10,
    )
    assert read_res.is_err
    assert isinstance(read_res.unwrap_err(), RepoPilotError)
    assert "traverses outside repository root" in read_res.unwrap_err().message

    # 2. Attempt to apply unified diff outside repo root
    malicious_patch = (
        "--- a/../../secret/keys.env\n"
        "+++ b/../../secret/keys.env\n"
        "@@ -1,1 +1,1 @@\n"
        "-API_SECRET_KEY=adversarial_token\n"
        "+API_SECRET_KEY=pwned\n"
    )
    diff_res = apply_unified_diff(
        repo_root=repo_dir,
        target_file="../../secret/keys.env",
        patch_str=malicious_patch,
    )
    assert diff_res.is_err
    assert isinstance(diff_res.unwrap_err(), DiffApplicationError)
    assert "Path traversal detected" in diff_res.unwrap_err().message

    # Verify secret file was untouched
    assert secret_file.read_text(encoding="utf-8") == "API_SECRET_KEY=adversarial_token\n"


def test_chaos_syntax_quarantine_rejects_ast_corruption(tmp_path: Path) -> None:
    """Chaos: Diffs causing syntax errors are rejected by Tree-sitter prior to disk mutation."""
    repo = tmp_path / "quarantine_repo"
    repo.mkdir()
    valid_file = repo / "calculator.py"
    original_code = "def add(a: int, b: int) -> int:\n    return a + b\n"
    valid_file.write_text(original_code, encoding="utf-8")

    # Patch introduces an unclosed parenthesis syntax bomb
    syntax_bomb = (
        "--- a/calculator.py\n"
        "+++ b/calculator.py\n"
        "@@ -1,2 +1,2 @@\n"
        "-def add(a: int, b: int) -> int:\n"
        "-    return a + b\n"
        "+def add(a: int, b: int) -> int:\n"
        "+    return (a + b\n"
    )

    parser = TreeSitterParser()
    res = apply_unified_diff(
        repo_root=repo,
        target_file="calculator.py",
        patch_str=syntax_bomb,
        parser=parser,
    )

    # Must be quarantined
    assert res.is_err
    err = res.unwrap_err()
    assert isinstance(err, DiffApplicationError)
    assert "syntax errors" in err.message

    # File on disk must remain pristine and uncorrupted
    assert valid_file.read_text(encoding="utf-8") == original_code


def test_chaos_memory_and_cpu_resource_limits_enforced(tmp_path: Path) -> None:
    """Chaos: Docker runner enforces memory limits, cpu quotas, and network isolation."""
    mock_client = MagicMock()
    mock_container = MagicMock()
    mock_container.wait.return_value = {"StatusCode": 0}
    mock_container.logs.side_effect = [b"1 passed", b""]
    mock_client.containers.run.return_value = mock_container

    runner = DockerSandboxRunner(docker_client=mock_client)
    res = runner.run_tests(repo_path=tmp_path, network_enabled=False)

    assert res.is_ok
    mock_client.containers.run.assert_called_once()
    _, kwargs = mock_client.containers.run.call_args

    # Verify hard resource bounds
    assert kwargs.get("mem_limit") == "2g"
    assert kwargs.get("cpu_quota") == 200000
    assert kwargs.get("network_mode") == "none"
    assert kwargs.get("detach") is True


def test_chaos_container_exception_ensures_cleanup(tmp_path: Path) -> None:
    """Chaos: Exception during container log read still guarantees container removal."""
    mock_client = MagicMock()
    mock_container = MagicMock()
    mock_container.wait.return_value = {"StatusCode": 0}
    mock_container.logs.side_effect = RuntimeError("Log stream buffer failed")
    mock_client.containers.run.return_value = mock_container

    runner = DockerSandboxRunner(docker_client=mock_client)
    res = runner.run_tests(repo_path=tmp_path)

    assert res.is_err
    assert isinstance(res.unwrap_err(), SandboxExecutionError)
    mock_container.remove.assert_called_once_with(force=True)
