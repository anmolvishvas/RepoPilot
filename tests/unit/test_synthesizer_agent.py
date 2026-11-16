"""Unit tests for the Code Synthesizer Agent."""

from pathlib import Path

from repopilot.agents.state import (
    MigrationPhase,
    MigrationPlan,
    MigrationPlanStep,
    MigrationState,
    ReflectionFeedback,
)
from repopilot.agents.synthesizer import SynthesizerAgent, synthesizer_node


def test_synthesizer_patches_success(tmp_path: Path) -> None:
    code_file = tmp_path / "mod.py"
    code_file.write_text("def fetch():\n    return 100\n", encoding="utf-8")

    agent = SynthesizerAgent()
    res = agent.synthesize_patches(
        repo_path=tmp_path,
        target_files=["mod.py"],
        recipe="sync-to-async",
    )

    assert res.is_ok
    patches = res.unwrap()
    assert len(patches) == 1
    assert patches[0].file_path == "mod.py"
    assert "async def fetch():" in patches[0].diff_text


def test_synthesizer_with_reflection(tmp_path: Path) -> None:
    code_file = tmp_path / "client.py"
    code_file.write_text("def caller():\n    res = fetch()\n    return res\n", encoding="utf-8")

    reflection = ReflectionFeedback(
        iteration=1,
        root_cause_analysis="coroutine fetch was not awaited",
        suggested_patch_adjustments=["Add 'await' to fetch call"],
        target_files_to_remediate=["client.py"],
    )

    agent = SynthesizerAgent()
    res = agent.synthesize_patches(
        repo_path=tmp_path,
        target_files=["client.py"],
        recipe="sync-to-async",
        reflections=[reflection],
    )

    assert res.is_ok
    patches = res.unwrap()
    assert len(patches) == 1
    assert "await fetch()" in patches[0].diff_text


def test_synthesizer_file_not_found(tmp_path: Path) -> None:
    agent = SynthesizerAgent()
    res = agent.synthesize_patches(
        repo_path=tmp_path,
        target_files=["missing.py"],
        recipe="sync-to-async",
    )
    assert res.is_err
    assert "not found" in res.unwrap_err().message


def test_synthesizer_node_execution(tmp_path: Path) -> None:
    code_file = tmp_path / "app.py"
    code_file.write_text("def main(): pass\n", encoding="utf-8")

    plan = MigrationPlan(
        recipe="sync-to-async",
        steps=[
            MigrationPlanStep(
                step_number=1,
                file_path="app.py",
                transformation_description="make main async",
            )
        ],
        affected_files=["app.py"],
    )

    state = MigrationState(
        task_id="t1",
        repo_path=str(tmp_path),
        recipe="sync-to-async",
        plan=plan,
    )

    update = synthesizer_node(state)
    assert update["phase"] == MigrationPhase.SANDBOX_TESTING
    assert len(update["patches"]) == 1
    assert len(update["tool_traces"]) == 1


def test_synthesizer_node_without_plan(tmp_path: Path) -> None:
    state = MigrationState(
        task_id="t1",
        repo_path=str(tmp_path),
        recipe="sync-to-async",
        plan=None,
    )
    update = synthesizer_node(state)
    assert update["phase"] == MigrationPhase.FAILED
    assert update["is_terminal"] is True
    assert "no migration plan exists" in update["error_message"]


def test_synthesizer_node_error(tmp_path: Path) -> None:
    plan = MigrationPlan(
        recipe="sync-to-async",
        steps=[],
        affected_files=["missing.py"],
    )
    state = MigrationState(
        task_id="t1",
        repo_path=str(tmp_path),
        recipe="sync-to-async",
        plan=plan,
    )
    update = synthesizer_node(state)
    assert update["phase"] == MigrationPhase.FAILED
    assert update["is_terminal"] is True
