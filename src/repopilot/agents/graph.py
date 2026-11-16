"""LangGraph cyclic multi-agent state machine orchestrating migration lifecycle."""

from __future__ import annotations

import time
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from repopilot.agents.critic import CriticAgent, critic_node
from repopilot.agents.planner import PlannerAgent, planner_node
from repopilot.agents.state import (
    MigrationPhase,
    MigrationState,
    ToolExecutionTrace,
)
from repopilot.agents.synthesizer import SynthesizerAgent, synthesizer_node
from repopilot.sandbox.runner import DockerSandboxRunner


def sandbox_node(
    state: MigrationState,
    runner: DockerSandboxRunner | None = None,
) -> dict[str, Any]:
    """Execute test suite in isolated Docker sandbox and capture results."""
    start_time = time.time()
    active_runner = runner or DockerSandboxRunner(allow_fallback=True)

    res = active_runner.run_tests(repo_path=state.repo_path)
    elapsed_ms = (time.time() - start_time) * 1000.0

    if res.is_ok:
        test_result = res.unwrap()
        trace = ToolExecutionTrace(
            tool_name="docker_sandbox_runner",
            args={"repo_path": state.repo_path},
            execution_time_ms=elapsed_ms,
            success=test_result.passed,
            output_summary=f"Tests {'passed' if test_result.passed else 'failed'} (Exit: {test_result.exit_code})",
        )
        return {
            "latest_sandbox_result": test_result,
            "phase": MigrationPhase.SANDBOX_TESTING,
            "tool_traces": [*state.tool_traces, trace],
        }

    err = res.unwrap_err()
    trace = ToolExecutionTrace(
        tool_name="docker_sandbox_runner",
        args={"repo_path": state.repo_path},
        execution_time_ms=elapsed_ms,
        success=False,
        output_summary=f"Sandbox execution error: {err.message}",
    )
    return {
        "error_message": err.message,
        "phase": MigrationPhase.FAILED,
        "is_terminal": True,
        "tool_traces": [*state.tool_traces, trace],
    }


def human_review_node(state: MigrationState) -> dict[str, Any]:
    """Checkpoint node for operator verification and diff approval before landing code."""
    trace = ToolExecutionTrace(
        tool_name="human_review",
        args={"phase": state.phase.value},
        execution_time_ms=0.0,
        success=True,
        output_summary="Paused at human review checkpoint for operator sign-off.",
    )
    return {
        "phase": MigrationPhase.HUMAN_REVIEW,
        "is_terminal": True,
        "tool_traces": [*state.tool_traces, trace],
    }


def route_after_critic(state: MigrationState) -> str:
    """Evaluate critic verdict: loop back to synthesizer for self-healing, or proceed."""
    if state.phase == MigrationPhase.REFLECTING:
        return "synthesizer"
    if state.phase == MigrationPhase.VERIFIED:
        return "human_review"
    return END


def create_migration_graph(
    checkpointer: Any | None = None,
    interrupt_before_human: bool = False,
    planner: PlannerAgent | None = None,
    synthesizer: SynthesizerAgent | None = None,
    critic: CriticAgent | None = None,
    runner: DockerSandboxRunner | None = None,
) -> Any:
    """Factory compiling a cyclical LangGraph state machine with self-healing feedback."""
    builder = StateGraph(MigrationState)

    builder.add_node("planner", lambda s: planner_node(s, agent=planner))
    builder.add_node("synthesizer", lambda s: synthesizer_node(s, agent=synthesizer))
    builder.add_node("sandbox_runner", lambda s: sandbox_node(s, runner=runner))
    builder.add_node("critic", lambda s: critic_node(s, agent=critic))
    builder.add_node("human_review", human_review_node)

    builder.add_edge(START, "planner")
    builder.add_edge("planner", "synthesizer")
    builder.add_edge("synthesizer", "sandbox_runner")
    builder.add_edge("sandbox_runner", "critic")

    builder.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "synthesizer": "synthesizer",
            "human_review": "human_review",
            END: END,
        },
    )
    builder.add_edge("human_review", END)

    interrupts = ["human_review"] if interrupt_before_human else []
    cp = checkpointer or MemorySaver()
    return builder.compile(checkpointer=cp, interrupt_before=interrupts)
