"""Unit tests for LangGraph agent state models."""

from repopilot.agents.state import (
    DiffHunk,
    FailedAssertion,
    MigrationPhase,
    MigrationPlan,
    MigrationPlanStep,
    MigrationState,
    ReflectionFeedback,
    SandboxTestResult,
    ToolExecutionTrace,
)


def test_migration_phase_values() -> None:
    assert MigrationPhase.INITIALIZE.value == "initialize"
    assert MigrationPhase.PLANNING.value == "planning"
    assert MigrationPhase.SYNTHESIZING.value == "synthesizing"
    assert MigrationPhase.SANDBOX_TESTING.value == "sandbox_testing"
    assert MigrationPhase.REFLECTING.value == "reflecting"
    assert MigrationPhase.VERIFIED.value == "verified"
    assert MigrationPhase("initialize") is MigrationPhase.INITIALIZE


def test_sandbox_test_result_logic() -> None:
    success_result = SandboxTestResult(
        exit_code=0,
        stdout="All tests passed.",
        stderr="",
        total_tests=12,
        passed_tests=12,
        failed_tests=0,
        execution_time_seconds=2.4,
    )
    assert success_result.passed is True

    failure_result = SandboxTestResult(
        exit_code=1,
        stdout="",
        stderr="AssertionError in test_fetch",
        total_tests=12,
        passed_tests=11,
        failed_tests=1,
        failures=[
            FailedAssertion(
                test_name="test_fetch",
                file_path="tests/test_client.py",
                line_number=34,
                assertion_message="Expected Coroutine, got None",
                stack_trace="Traceback...",
            )
        ],
        execution_time_seconds=1.8,
    )
    assert failure_result.passed is False
    assert len(failure_result.failures) == 1
    assert failure_result.failures[0].line_number == 34


def test_migration_state_lifecycle() -> None:
    plan = MigrationPlan(
        recipe="sync-to-async",
        steps=[
            MigrationPlanStep(
                step_number=1,
                file_path="src/client.py",
                transformation_description="Convert requests.get to await client.get",
            )
        ],
        affected_files=["src/client.py"],
    )

    state = MigrationState(
        task_id="task-12345",
        repo_path="/path/to/repo",
        recipe="sync-to-async",
        phase=MigrationPhase.PLANNING,
        plan=plan,
        patches=[
            DiffHunk(
                file_path="src/client.py",
                diff_text="--- a/client.py\n+++ b/client.py\n@@ -1 +1 @@\n-sync\n+async",
            )
        ],
        reflections=[
            ReflectionFeedback(
                iteration=1,
                root_cause_analysis="Missed async keyword on method declaration",
                suggested_patch_adjustments=["Add async def get(self)"],
                target_files_to_remediate=["src/client.py"],
            )
        ],
        tool_traces=[
            ToolExecutionTrace(
                tool_name="search_ast_symbols",
                args={"query": "fetch_user"},
                execution_time_ms=14.2,
                success=True,
                output_summary="Found 1 symbol",
            )
        ],
    )

    assert state.task_id == "task-12345"
    assert state.plan is not None
    assert len(state.plan.steps) == 1
    assert state.retry_count == 0
    assert state.max_retries == 3
    assert state.is_terminal is False
    assert len(state.tool_traces) == 1
    assert state.tool_traces[0].tool_name == "search_ast_symbols"
