"""Unit tests for the Critic & Self-Healing Reflection Agent."""

from repopilot.agents.critic import CriticAgent, critic_node
from repopilot.agents.state import (
    FailedAssertion,
    MigrationPhase,
    MigrationState,
    SandboxTestResult,
)


def test_critic_evaluates_passing_tests() -> None:
    pass_res = SandboxTestResult(
        exit_code=0,
        total_tests=5,
        passed_tests=5,
        failed_tests=0,
    )
    state = MigrationState(
        task_id="t1",
        repo_path=".",
        recipe="test",
        latest_sandbox_result=pass_res,
    )

    agent = CriticAgent()
    eval_res = agent.evaluate_test_results(state)

    assert eval_res.is_ok
    data = eval_res.unwrap()
    assert data["phase"] == MigrationPhase.VERIFIED
    assert data["is_terminal"] is True


def test_critic_evaluates_failing_tests_self_healing() -> None:
    fail_res = SandboxTestResult(
        exit_code=1,
        total_tests=2,
        passed_tests=1,
        failed_tests=1,
        failures=[
            FailedAssertion(
                test_name="test_async_call",
                file_path="tests/test_foo.py",
                line_number=20,
                assertion_message="RuntimeWarning: coroutine was never awaited",
                stack_trace="tests/test_foo.py:20: RuntimeWarning: coroutine was never awaited",
            )
        ],
    )
    state = MigrationState(
        task_id="t1",
        repo_path=".",
        recipe="sync-to-async",
        retry_count=0,
        max_retries=3,
        latest_sandbox_result=fail_res,
    )

    agent = CriticAgent()
    eval_res = agent.evaluate_test_results(state)

    assert eval_res.is_ok
    data = eval_res.unwrap()
    assert data["phase"] == MigrationPhase.REFLECTING
    assert data["retry_count"] == 1
    assert data["is_terminal"] is False
    assert len(data["reflections"]) == 1

    feedback = data["reflections"][0]
    assert feedback.iteration == 1
    assert "tests/test_foo.py" in feedback.target_files_to_remediate
    assert any("await" in adj.lower() for adj in feedback.suggested_patch_adjustments)


def test_critic_evaluates_escalation_on_max_retries() -> None:
    fail_res = SandboxTestResult(
        exit_code=1,
        total_tests=1,
        passed_tests=0,
        failed_tests=1,
        failures=[
            FailedAssertion(
                test_name="test_broken",
                file_path="tests/test_broken.py",
                assertion_message="AssertionError",
            )
        ],
    )
    state = MigrationState(
        task_id="t1",
        repo_path=".",
        recipe="sync-to-async",
        retry_count=3,
        max_retries=3,
        latest_sandbox_result=fail_res,
    )

    agent = CriticAgent()
    eval_res = agent.evaluate_test_results(state)

    assert eval_res.is_ok
    data = eval_res.unwrap()
    assert data["phase"] == MigrationPhase.ESCALATED
    assert data["is_terminal"] is True
    assert "budget exhausted" in data["error_message"].lower()


def test_critic_node_execution() -> None:
    pass_res = SandboxTestResult(exit_code=0, total_tests=1, passed_tests=1)
    state = MigrationState(
        task_id="t1",
        repo_path=".",
        recipe="test",
        latest_sandbox_result=pass_res,
    )

    update = critic_node(state)
    assert update["phase"] == MigrationPhase.VERIFIED
    assert update["is_terminal"] is True
    assert len(update["tool_traces"]) == 1


def test_critic_node_missing_results() -> None:
    state = MigrationState(
        task_id="t1",
        repo_path=".",
        recipe="test",
        latest_sandbox_result=None,
    )

    update = critic_node(state)
    assert update["phase"] == MigrationPhase.FAILED
    assert update["is_terminal"] is True
    assert "no sandbox test results" in update["error_message"].lower()
