"""Dockerized test sandbox runner enforcing resource limits and ephemeral lifecycle."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import docker
from docker.errors import DockerException

from repopilot.agents.state import SandboxTestResult
from repopilot.core.exceptions import SandboxExecutionError, SandboxTimeoutError
from repopilot.core.result import Err, Ok, Result
from repopilot.sandbox.pytest_parser import PytestErrorParser


class DockerSandboxRunner:
    """Manages ephemeral Docker containers for executing test suites in isolation."""

    DEFAULT_IMAGE = "python:3.11-slim"
    DEFAULT_TIMEOUT_SECONDS = 60
    DEFAULT_MEM_LIMIT = "2g"
    DEFAULT_CPU_QUOTA = 200000  # 2.0 cores

    def __init__(
        self,
        image: str = DEFAULT_IMAGE,
        docker_client: docker.DockerClient | None = None,
        allow_fallback: bool = True,
    ) -> None:
        self.image = image
        self.allow_fallback = allow_fallback
        self._client: docker.DockerClient | None = docker_client

    def _get_client(self) -> docker.DockerClient | None:
        """Lazy load and verify Docker daemon connection."""
        if self._client is not None:
            return self._client
        try:
            self._client = docker.from_env()
            self._client.ping()
            return self._client
        except (DockerException, Exception) as exc:
            if not self.allow_fallback:
                raise SandboxExecutionError(
                    "Docker daemon is unavailable and fallback is disabled."
                ) from exc
            return None

    def run_tests(
        self,
        repo_path: Path | str,
        test_path: str | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        network_enabled: bool = False,
    ) -> Result[SandboxTestResult, SandboxExecutionError]:
        """Execute test command inside an ephemeral container with strict resource limits."""
        abs_repo = Path(repo_path).resolve()
        if not abs_repo.exists():
            return Err(SandboxExecutionError(f"Target repository path does not exist: {abs_repo}"))

        try:
            client = self._get_client()
        except SandboxExecutionError as see:
            return Err(see)
        except Exception as exc:
            return Err(
                SandboxExecutionError("Failed to initialize Docker client", details=str(exc))
            )

        if client is None:
            # Fallback execution in controlled subprocess if Docker daemon is not active
            return self._run_fallback(abs_repo, test_path, timeout_seconds)

        cmd = "pytest -v"
        if test_path:
            cmd += f" {test_path}"

        container: Any = None
        start_time = time.time()

        try:
            volumes = {str(abs_repo): {"bind": "/workspace", "mode": "rw"}}
            container = client.containers.run(
                image=self.image,
                command=f"sh -c 'cd /workspace && {cmd}'",
                volumes=volumes,
                working_dir="/workspace",
                mem_limit=self.DEFAULT_MEM_LIMIT,
                cpu_quota=self.DEFAULT_CPU_QUOTA,
                network_mode="none" if not network_enabled else "bridge",
                detach=True,
            )

            # Wait with timeout guard
            result = container.wait(timeout=timeout_seconds)
            exit_code = int(result.get("StatusCode", 1))
            duration = time.time() - start_time

            stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")

            test_result = PytestErrorParser.parse_stdout(
                stdout=stdout, stderr=stderr, exit_code=exit_code, duration=duration
            )
            return Ok(test_result)

        except DockerException as dex:
            return Err(SandboxExecutionError("Docker container execution failed", details=str(dex)))
        except TimeoutError:
            return Err(
                SandboxTimeoutError(f"Test suite execution exceeded {timeout_seconds}s timeout")
            )
        except Exception as exc:
            return Err(
                SandboxExecutionError("Unexpected error running sandbox tests", details=str(exc))
            )
        finally:
            if container is not None:
                try:
                    container.remove(force=True)
                except Exception:  # nosec B110
                    pass

    def _run_fallback(
        self, repo_path: Path, test_path: str | None, timeout_seconds: int
    ) -> Result[SandboxTestResult, SandboxExecutionError]:
        """Execute pytest directly via subprocess when Docker daemon is not reachable."""
        import subprocess  # nosec B404

        cmd = ["pytest", "-v"]
        if test_path:
            cmd.append(test_path)

        start_time = time.time()
        try:
            proc = subprocess.run(  # nosec B603
                cmd,
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            duration = time.time() - start_time
            result = PytestErrorParser.parse_stdout(
                stdout=proc.stdout,
                stderr=proc.stderr,
                exit_code=proc.returncode,
                duration=duration,
            )
            return Ok(result)
        except subprocess.TimeoutExpired:
            return Err(
                SandboxTimeoutError(f"Test suite execution exceeded {timeout_seconds}s timeout")
            )
        except Exception as exc:
            return Err(
                SandboxExecutionError("Failed running fallback pytest process", details=str(exc))
            )
