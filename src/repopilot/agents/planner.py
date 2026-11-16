"""Planner and Supervisor Agent decomposing migration goals into ordered AST steps."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from repopilot.agents.state import (
    MigrationPhase,
    MigrationPlan,
    MigrationPlanStep,
    MigrationState,
    ToolExecutionTrace,
)
from repopilot.ast.call_graph import CallGraphBuilder
from repopilot.core.exceptions import PlannerError
from repopilot.core.result import Err, Ok, Result


class PlannerAgent:
    """Supervisory agent that determines symbol migration ordering and generates execution plans."""

    def __init__(self, call_graph: CallGraphBuilder | None = None) -> None:
        self.call_graph = call_graph or CallGraphBuilder()

    def generate_plan(
        self,
        recipe: str,
        repo_path: Path | str,
        target_files: list[str] | None = None,
    ) -> Result[MigrationPlan, PlannerError]:
        """Formulate a step-by-step migration plan respecting AST dependency topology."""
        if not recipe.strip():
            return Err(PlannerError("Migration recipe cannot be empty."))

        root = Path(repo_path).resolve()
        if not root.exists():
            return Err(PlannerError(f"Repository root does not exist: {root}"))

        # Determine topological execution sequence from call graph
        topological_symbols = self.call_graph.get_topological_migration_order()

        steps: list[MigrationPlanStep] = []
        affected_files_set: set[str] = set()

        # If specific files are provided, or discover files in repository
        files_to_plan: list[str] = target_files or []
        if not files_to_plan:
            # Gather relevant python files from repository
            for p in sorted(root.glob("**/*.py")):
                if not any(part.startswith((".", "venv", "__pycache__")) for part in p.parts):
                    files_to_plan.append(str(p.relative_to(root).as_posix()))

        if not files_to_plan:
            return Err(PlannerError(f"No source code files found to migrate under {root}."))

        # Map symbols to files
        file_to_symbols: dict[str, list[str]] = {}
        for sym_id in topological_symbols:
            files = self.call_graph.get_affected_files(sym_id)
            for f in files:
                file_to_symbols.setdefault(f, []).append(sym_id)

        step_counter = 1
        for f in files_to_plan:
            symbols = file_to_symbols.get(f, [])
            desc = f"Modernize {f} according to recipe: '{recipe}'"
            if symbols:
                desc += f" (Target symbols: {', '.join(symbols[:3])}{'...' if len(symbols) > 3 else ''})"

            steps.append(
                MigrationPlanStep(
                    step_number=step_counter,
                    file_path=f,
                    target_symbol_ids=symbols,
                    transformation_description=desc,
                    dependencies=[step_counter - 1] if step_counter > 1 else [],
                )
            )
            affected_files_set.add(f)
            step_counter += 1

        plan = MigrationPlan(
            recipe=recipe,
            steps=steps,
            affected_files=sorted(affected_files_set),
        )
        return Ok(plan)


def planner_node(state: MigrationState, agent: PlannerAgent | None = None) -> dict[str, Any]:
    """LangGraph node execution function for the Planner Agent."""
    start_time = time.time()
    planner = agent or PlannerAgent()

    plan_res = planner.generate_plan(
        recipe=state.recipe,
        repo_path=state.repo_path,
    )

    elapsed_ms = (time.time() - start_time) * 1000.0

    if plan_res.is_err:
        err = plan_res.unwrap_err()
        trace = ToolExecutionTrace(
            tool_name="planner_agent",
            args={"recipe": state.recipe, "repo_path": state.repo_path},
            execution_time_ms=elapsed_ms,
            success=False,
            output_summary=f"Planning failed: {err.message}",
        )
        return {
            "error_message": err.message,
            "phase": MigrationPhase.FAILED,
            "is_terminal": True,
            "tool_traces": [*state.tool_traces, trace],
        }

    plan = plan_res.unwrap()
    trace = ToolExecutionTrace(
        tool_name="planner_agent",
        args={"recipe": state.recipe, "repo_path": state.repo_path},
        execution_time_ms=elapsed_ms,
        success=True,
        output_summary=f"Synthesized {len(plan.steps)} migration steps across {len(plan.affected_files)} files.",
    )

    return {
        "plan": plan,
        "phase": MigrationPhase.SYNTHESIZING,
        "tool_traces": [*state.tool_traces, trace],
    }
