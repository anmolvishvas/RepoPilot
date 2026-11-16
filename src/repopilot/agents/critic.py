"""Critic and Reflection Agent analyzing test failures for self-healing feedback."""

from __future__ import annotations

import time
from typing import Any

from repopilot.agents.state import (
    MigrationPhase,
    MigrationState,
    ReflectionFeedback,
    ToolExecutionTrace,
)
from repopilot.core.exceptions import CriticError
from repopilot.core.result import Err, Ok, Result


class CriticAgent:
    """Evaluates test sandbox execution outputs and synthesizes targeted repair prompts."""

    def evaluate_test_results(
        self,
        state: MigrationState,
    ) -> Result[dict[str, Any], CriticError]:
        """Critique sandbox test results and determine whether to verify, reflect, or escalate."""
        result = state.latest_sandbox_result
        if result is None:
            return Err(CriticError("Cannot critique: state contains no sandbox test results."))

        if result.passed:
            return Ok(
                {
                    "phase": MigrationPhase.VERIFIED,
                    "is_terminal": True,
                    "error_message": None,
                }
            )

        # Tests failed: check retry budget
        if state.retry_count >= state.max_retries:
            return Ok(
                {
                    "phase": MigrationPhase.ESCALATED,
                    "is_terminal": True,
                    "error_message": (
                        f"Self-healing budget exhausted after {state.retry_count} retries. "
                        f"{len(result.failures)} failing test assertions remaining."
                    ),
                }
            )

        # Formulate self-healing reflection
        iteration = state.retry_count + 1
        remediation_files: set[str] = set()
        adjustments: list[str] = []
        root_causes: list[str] = []

        for fail in result.failures:
            remediation_files.add(fail.file_path)
            msg = fail.assertion_message.lower()
            trace = fail.stack_trace.lower()

            if "coroutine" in msg or "coroutine" in trace or "was never awaited" in trace:
                adjustments.append(
                    f"Add missing 'await' operator to invocations in {fail.test_name}"
                )
                root_causes.append(
                    f"Async coroutine not awaited in {fail.file_path}:{fail.line_number or '?'}"
                )
            elif "typeerror" in msg or "typeerror" in trace:
                adjustments.append(f"Correct parameter type mismatch in {fail.test_name}")
                root_causes.append(f"Type contract mismatch in {fail.file_path}")
            else:
                adjustments.append(
                    f"Repair failing assertion '{fail.assertion_message}' in {fail.test_name}"
                )
                root_causes.append(
                    f"Assertion failure in {fail.file_path}:{fail.line_number or '?'}"
                )

        feedback = ReflectionFeedback(
            iteration=iteration,
            root_cause_analysis="; ".join(root_causes) or "Tests failed with non-zero exit code.",
            suggested_patch_adjustments=adjustments
            or ["Analyze stack traces and adjust patch logic."],
            target_files_to_remediate=sorted(remediation_files),
        )

        return Ok(
            {
                "phase": MigrationPhase.REFLECTING,
                "reflections": [*state.reflections, feedback],
                "retry_count": iteration,
                "is_terminal": False,
            }
        )


def critic_node(state: MigrationState, agent: CriticAgent | None = None) -> dict[str, Any]:
    """LangGraph node execution function for the Critic Agent."""
    start_time = time.time()
    critic = agent or CriticAgent()

    eval_res = critic.evaluate_test_results(state)
    elapsed_ms = (time.time() - start_time) * 1000.0

    if eval_res.is_err:
        err = eval_res.unwrap_err()
        trace = ToolExecutionTrace(
            tool_name="critic_agent",
            args={"retry_count": state.retry_count},
            execution_time_ms=elapsed_ms,
            success=False,
            output_summary=f"Critic evaluation failed: {err.message}",
        )
        return {
            "error_message": err.message,
            "phase": MigrationPhase.FAILED,
            "is_terminal": True,
            "tool_traces": [*state.tool_traces, trace],
        }

    updates = eval_res.unwrap()
    phase = updates.get("phase", state.phase)

    trace = ToolExecutionTrace(
        tool_name="critic_agent",
        args={"retry_count": state.retry_count},
        execution_time_ms=elapsed_ms,
        success=True,
        output_summary=f"Critic transitioned phase to {phase}. Terminal: {updates.get('is_terminal')}",
    )

    return {
        **updates,
        "tool_traces": [*state.tool_traces, trace],
    }
