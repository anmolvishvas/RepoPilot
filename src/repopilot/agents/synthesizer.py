"""Code Synthesizer Agent generating valid AST-aware unified diff patches."""

from __future__ import annotations

import difflib
import time
from pathlib import Path
from typing import Any

from repopilot.agents.state import (
    DiffHunk,
    MigrationPhase,
    MigrationState,
    ReflectionFeedback,
    ToolExecutionTrace,
)
from repopilot.ast.parser import TreeSitterParser
from repopilot.core.exceptions import SynthesizerError
from repopilot.core.result import Err, Ok, Result


class SynthesizerAgent:
    """Generates unified diffs and incorporates reflection feedback during self-healing cycles."""

    def __init__(self, parser: TreeSitterParser | None = None) -> None:
        self.parser = parser or TreeSitterParser()

    def synthesize_patches(
        self,
        repo_path: Path | str,
        target_files: list[str],
        recipe: str,
        reflections: list[ReflectionFeedback] | None = None,
    ) -> Result[list[DiffHunk], SynthesizerError]:
        """Synthesize unified diff hunks for the requested files, incorporating self-healing adjustments."""
        root = Path(repo_path).resolve()
        patches: list[DiffHunk] = []

        active_reflection = reflections[-1] if reflections else None

        for file_rel in target_files:
            file_abs = (root / file_rel).resolve()
            if not file_abs.exists():
                return Err(SynthesizerError(f"Target file for synthesis not found: {file_rel}"))

            try:
                original_text = file_abs.read_text(encoding="utf-8")
                modified_text = self._apply_modernization(
                    original_text=original_text,
                    file_path=file_rel,
                    recipe=recipe,
                    reflection=active_reflection,
                )

                # Pre-validate syntax before synthesizing diff hunk
                parse_res = self.parser.parse_code(modified_text, file_path=file_rel)
                if parse_res.is_err or self.parser.has_syntax_errors(parse_res.unwrap()):
                    return Err(
                        SynthesizerError(
                            f"Synthesizer generated invalid syntax for {file_rel}. Patch aborted."
                        )
                    )

                # Generate unified diff
                orig_lines = original_text.splitlines(keepends=True)
                mod_lines = modified_text.splitlines(keepends=True)
                diff_lines = list(
                    difflib.unified_diff(
                        orig_lines,
                        mod_lines,
                        fromfile=f"a/{file_rel}",
                        tofile=f"b/{file_rel}",
                    )
                )

                if diff_lines:
                    diff_text = "".join(diff_lines)
                    patches.append(
                        DiffHunk(
                            file_path=file_rel,
                            diff_text=diff_text,
                            explanation=f"Modernized {file_rel} for '{recipe}'"
                            + (
                                f" with repair iteration {active_reflection.iteration}"
                                if active_reflection
                                else ""
                            ),
                        )
                    )

            except Exception as exc:
                return Err(
                    SynthesizerError(f"Failed synthesizing patch for {file_rel}", details=str(exc))
                )

        return Ok(patches)

    def _apply_modernization(
        self,
        original_text: str,
        file_path: str,
        recipe: str,
        reflection: ReflectionFeedback | None = None,
    ) -> str:
        """Apply recipe and reflection rules to source code string."""
        modified = original_text
        recipe_lower = recipe.lower()

        # Modernization: sync-to-async transformations
        if "async" in recipe_lower:
            # Upgrade synchronous defs to async defs if requested
            lines = modified.splitlines(keepends=True)
            new_lines: list[str] = []
            for line in lines:
                if line.startswith("def ") and not line.startswith("def test_"):
                    new_lines.append(f"async {line}")
                elif "asyncio" not in modified and line.startswith("import "):
                    new_lines.append("import asyncio\n")
                    new_lines.append(line)
                else:
                    new_lines.append(line)
            modified = "".join(new_lines)

        # Incorporate self-healing reflection guidance if present
        if reflection:
            # If reflection suggests missing awaits
            for adj in reflection.suggested_patch_adjustments:
                if "await" in adj.lower():
                    # Ensure calls to async functions have await
                    lines = modified.splitlines(keepends=True)
                    repaired_lines: list[str] = []
                    for line in lines:
                        if " = fetch(" in line and "await" not in line:
                            repaired_lines.append(line.replace(" = fetch(", " = await fetch("))
                        elif "return fetch(" in line and "await" not in line:
                            repaired_lines.append(
                                line.replace("return fetch(", "return await fetch(")
                            )
                        else:
                            repaired_lines.append(line)
                    modified = "".join(repaired_lines)

        return modified


def synthesizer_node(
    state: MigrationState, agent: SynthesizerAgent | None = None
) -> dict[str, Any]:
    """LangGraph node execution function for the Code Synthesizer Agent."""
    start_time = time.time()
    synthesizer = agent or SynthesizerAgent()

    if not state.plan:
        return {
            "error_message": "Cannot synthesize code: no migration plan exists in state.",
            "phase": MigrationPhase.FAILED,
            "is_terminal": True,
        }

    target_files = state.plan.affected_files
    if state.reflections and state.reflections[-1].target_files_to_remediate:
        target_files = state.reflections[-1].target_files_to_remediate

    patch_res = synthesizer.synthesize_patches(
        repo_path=state.repo_path,
        target_files=target_files,
        recipe=state.recipe,
        reflections=state.reflections,
    )

    elapsed_ms = (time.time() - start_time) * 1000.0

    if patch_res.is_err:
        err = patch_res.unwrap_err()
        trace = ToolExecutionTrace(
            tool_name="synthesizer_agent",
            args={"target_files": target_files, "recipe": state.recipe},
            execution_time_ms=elapsed_ms,
            success=False,
            output_summary=f"Synthesis failed: {err.message}",
        )
        return {
            "error_message": err.message,
            "phase": MigrationPhase.FAILED,
            "is_terminal": True,
            "tool_traces": [*state.tool_traces, trace],
        }

    patches = patch_res.unwrap()
    trace = ToolExecutionTrace(
        tool_name="synthesizer_agent",
        args={"target_files": target_files, "recipe": state.recipe},
        execution_time_ms=elapsed_ms,
        success=True,
        output_summary=f"Synthesized {len(patches)} patch hunks.",
    )

    return {
        "patches": patches,
        "phase": MigrationPhase.SANDBOX_TESTING,
        "tool_traces": [*state.tool_traces, trace],
    }
