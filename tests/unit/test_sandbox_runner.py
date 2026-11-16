"""Unit tests for DockerSandboxRunner and fallback execution."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from repopilot.core.exceptions import SandboxExecutionError, SandboxTimeoutError
from repopilot.sandbox.runner import DockerSandboxRunner


def test_runner_nonexistent_repo(tmp_path: Path) -> None:
    non_existent = tmp_path / "does_not_exist"
    runner = DockerSandboxRunner()
    res = runner.run_tests(repo_path=non_existent)

    assert res.is_err
    assert isinstance(res.unwrap_err(), SandboxExecutionError)
    assert "does not exist" in res.unwrap_err().message


def test_runner_fallback_subprocess_success(tmp_path: Path) -> None:
    runner = DockerSandboxRunner(allow_fallback=True)

    fake_stdout = "===== 3 passed in 0.20s ====="
    with (
        patch.object(runner, "_get_client", return_value=None),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["pytest", "-v"],
            returncode=0,
            stdout=fake_stdout,
            stderr="",
        )
        res = runner.run_tests(repo_path=tmp_path)

        assert res.is_ok
        test_res = res.unwrap()
        assert test_res.is_success
        assert test_res.passed_tests == 3
        assert test_res.failed_tests == 0


def test_runner_fallback_subprocess_timeout(tmp_path: Path) -> None:
    runner = DockerSandboxRunner(allow_fallback=True)

    with (
        patch.object(runner, "_get_client", return_value=None),
        patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="pytest", timeout=5)),
    ):
        res = runner.run_tests(repo_path=tmp_path, timeout_seconds=5)

        assert res.is_err
        err = res.unwrap_err()
        assert isinstance(err, SandboxTimeoutError)
        assert "exceeded 5s timeout" in err.message


def test_runner_fallback_disallowed_no_docker(tmp_path: Path) -> None:
    runner = DockerSandboxRunner(allow_fallback=False)

    with patch("docker.from_env", side_effect=Exception("No daemon")):
        res = runner.run_tests(repo_path=tmp_path)
        assert res.is_err
        assert "unavailable and fallback is disabled" in res.unwrap_err().message


def test_runner_docker_container_lifecycle(tmp_path: Path) -> None:
    mock_client = MagicMock()
    mock_container = MagicMock()
    mock_container.wait.return_value = {"StatusCode": 0}
    mock_container.logs.side_effect = [
        b"===== 4 passed in 0.50s =====",
        b"",
    ]
    mock_client.containers.run.return_value = mock_container

    runner = DockerSandboxRunner(docker_client=mock_client)
    res = runner.run_tests(repo_path=tmp_path, test_path="tests/test_unit.py")

    assert res.is_ok
    test_res = res.unwrap()
    assert test_res.is_success
    assert test_res.passed_tests == 4

    mock_client.containers.run.assert_called_once()
    mock_container.wait.assert_called_once()
    mock_container.remove.assert_called_once_with(force=True)
