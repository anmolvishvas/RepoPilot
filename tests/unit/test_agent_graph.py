"""Unit tests for the LangGraph state machine and self-healing cyclic orchestration."""

from pathlib import Path
from unittest.mock import MagicMock

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END

from repopilot.agents.graph import (
    create_migration_graph,
    human_review_node,
    route_after_critic,
    sandbox_node,
)
from repopilot.agents.state import (
    FailedAssertion,
    MigrationPhase,
    MigrationState,
    SandboxTestResult,
)
from repopilot.core.result import Ok


def test_route_after_critic() -> None:
    reflect_state = MigrationState(
        task_id="1", repo_path=".", recipe="r", phase=MigrationPhase.REFLECTING
    )
    assert route_after_critic(reflect_state) == "synthesizer"

    verified_state = MigrationState(
        task_id="1", repo_path=".", recipe="r", phase=MigrationPhase.VERIFIED
    )
    assert route_after_critic(verified_state) == "human_review"

    escalated_state = MigrationState(
        task_id="1", repo_path=".", recipe="r", phase=MigrationPhase.ESCALATED
    )
    assert route_after_critic(escalated_state) == END


def test_human_review_node() -> None:
    state = MigrationState(task_id="1", repo_path=".", recipe="r", phase=MigrationPhase.VERIFIED)
    update = human_review_node(state)
    assert update["phase"] == MigrationPhase.HUMAN_REVIEW
    assert update["is_terminal"] is True
    assert len(update["tool_traces"]) == 1


def test_sandbox_node() -> None:
    mock_runner = MagicMock()
    mock_runner.run_tests.return_value = Ok(
        SandboxTestResult(exit_code=0, total_tests=3, passed_tests=3)
    )

    state = MigrationState(task_id="1", repo_path=".", recipe="r")
    update = sandbox_node(state, runner=mock_runner)

    assert update["phase"] == MigrationPhase.SANDBOX_TESTING
    assert update["latest_sandbox_result"].passed is True
    assert len(update["tool_traces"]) == 1


def test_full_agent_cycle_with_self_healing(tmp_path: Path) -> None:
    # Setup test repository files
    code_file = tmp_path / "service.py"
    code_file.write_text("def fetch():\n    return 42\n", encoding="utf-8")

    # Mock sandbox runner:
    # Call 1 (initial run): fails with missing await
    # Call 2 (after reflection & repair): passes!
    fail_result = SandboxTestResult(
        exit_code=1,
        total_tests=1,
        passed_tests=0,
        failed_tests=1,
        failures=[
            FailedAssertion(
                test_name="test_fetch",
                file_path="service.py",
                assertion_message="RuntimeWarning: coroutine was never awaited",
            )
        ],
    )
    pass_result = SandboxTestResult(
        exit_code=0,
        total_tests=1,
        passed_tests=1,
        failed_tests=0,
    )

    mock_runner = MagicMock()
    mock_runner.run_tests.side_effect = [Ok(fail_result), Ok(pass_result)]

    graph = create_migration_graph(
        checkpointer=MemorySaver(),
        runner=mock_runner,
    )

    initial_state = {
        "task_id": "test_task_42",
        "repo_path": str(tmp_path),
        "recipe": "sync-to-async",
        "phase": MigrationPhase.INITIALIZE,
        "max_retries": 3,
    }

    config = {"configurable": {"thread_id": "migration_thread_1"}}
    final_state = graph.invoke(initial_state, config=config)

    # Validate that self-healing cycle succeeded and transitioned through reflection to human review
    assert final_state["phase"] == MigrationPhase.HUMAN_REVIEW
    assert final_state["is_terminal"] is True
    assert final_state["retry_count"] == 1
    assert len(final_state["reflections"]) == 1
    assert "service.py" in final_state["reflections"][0].target_files_to_remediate
    assert len(final_state["patches"]) >= 1
    assert any(t.tool_name == "critic_agent" for t in final_state["tool_traces"])
