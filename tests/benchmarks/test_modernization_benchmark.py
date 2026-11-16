"""Modernization Benchmark Evaluation Suite for RepoPilot.

Evaluates autonomous codebase modernization workflows across standard patterns:
1. Sync-to-async function transformation and caller await propagation.
2. Self-healing reflection recovery on unawaited coroutines.
3. Multi-file dependency graph resolution and ordered patching.
"""

from pathlib import Path
from unittest.mock import MagicMock

from langgraph.checkpoint.memory import MemorySaver

from repopilot.agents.graph import create_migration_graph
from repopilot.agents.state import (
    FailedAssertion,
    MigrationPhase,
    SandboxTestResult,
)
from repopilot.ast.call_graph import CallGraphBuilder
from repopilot.ast.models import ASTParseResult, CallSite, Position, Range, SymbolInfo, SymbolType
from repopilot.core.result import Ok


def _build_symbol(sym_id: str, file_path: str) -> SymbolInfo:
    return SymbolInfo(
        id=sym_id,
        name=sym_id.split(".")[-1],
        file_path=file_path,
        symbol_type=SymbolType.FUNCTION,
        range=Range(start=Position(line=1, character=0), end=Position(line=5, character=0)),
        byte_range=(0, 50),
    )


def test_benchmark_sync_to_async_migration(tmp_path: Path) -> None:
    """Benchmark: Autonomous sync-to-async migration with call-graph order."""
    repo = tmp_path / "sync_repo"
    repo.mkdir()

    client_code = repo / "client.py"
    client_code.write_text(
        "def fetch_user(user_id: int) -> dict:\n    return {'id': user_id}\n", encoding="utf-8"
    )

    caller_code = repo / "handler.py"
    caller_code.write_text(
        "from client import fetch_user\ndef handle_request():\n    return fetch_user(1)\n",
        encoding="utf-8",
    )

    mock_runner = MagicMock()
    mock_runner.run_tests.return_value = Ok(
        SandboxTestResult(exit_code=0, total_tests=2, passed_tests=2, failed_tests=0)
    )

    graph = create_migration_graph(
        checkpointer=MemorySaver(),
        runner=mock_runner,
    )

    init_state = {
        "task_id": "bench_01_async",
        "repo_path": str(repo),
        "recipe": "sync-to-async",
        "phase": MigrationPhase.INITIALIZE,
        "max_retries": 3,
    }

    result = graph.invoke(init_state, config={"configurable": {"thread_id": "bench_01"}})

    # Verification criteria
    assert result["phase"] == MigrationPhase.HUMAN_REVIEW
    assert result["is_terminal"] is True
    assert len(result["patches"]) >= 1
    assert any("async def" in p.diff_text for p in result["patches"])


def test_benchmark_self_healing_reflection_loop(tmp_path: Path) -> None:
    """Benchmark: Self-healing resilience when initial patch introduces missing await."""
    repo = tmp_path / "repair_repo"
    repo.mkdir()

    code = repo / "worker.py"
    code.write_text("def fetch():\n    return 42\n", encoding="utf-8")

    # Initial test run produces unawaited coroutine error, reflection repairs it on attempt 2
    failing_result = SandboxTestResult(
        exit_code=1,
        total_tests=1,
        passed_tests=0,
        failed_tests=1,
        failures=[
            FailedAssertion(
                test_name="test_worker",
                file_path="worker.py",
                assertion_message="RuntimeWarning: coroutine 'fetch' was never awaited",
            )
        ],
    )
    passing_result = SandboxTestResult(
        exit_code=0,
        total_tests=1,
        passed_tests=1,
        failed_tests=0,
    )

    mock_runner = MagicMock()
    mock_runner.run_tests.side_effect = [Ok(failing_result), Ok(passing_result)]

    graph = create_migration_graph(
        checkpointer=MemorySaver(),
        runner=mock_runner,
    )

    init_state = {
        "task_id": "bench_02_self_heal",
        "repo_path": str(repo),
        "recipe": "sync-to-async",
        "phase": MigrationPhase.INITIALIZE,
        "max_retries": 3,
    }

    result = graph.invoke(init_state, config={"configurable": {"thread_id": "bench_02"}})

    # Assert agent cycled through reflection and recovered autonomously
    assert result["phase"] == MigrationPhase.HUMAN_REVIEW
    assert result["retry_count"] == 1
    assert len(result["reflections"]) == 1
    assert result["reflections"][0].iteration == 1


def test_benchmark_multi_file_blast_radius_resolution() -> None:
    """Benchmark: Blast radius calculation across interconnected modules."""
    builder = CallGraphBuilder()

    # Create diamond dependency: A -> B, A -> C, B -> D, C -> D
    sym_a = _build_symbol("mod.a", "a.py")
    sym_b = _build_symbol("mod.b", "b.py")
    sym_c = _build_symbol("mod.c", "c.py")
    sym_d = _build_symbol("mod.d", "d.py")

    ast_a = ASTParseResult(
        file_path="a.py",
        symbols=[sym_a],
        call_sites=[
            CallSite(
                caller_symbol_id="mod.a", callee_name="mod.b", file_path="a.py", line_number=2
            ),
            CallSite(
                caller_symbol_id="mod.a", callee_name="mod.c", file_path="a.py", line_number=3
            ),
        ],
    )
    ast_b = ASTParseResult(
        file_path="b.py",
        symbols=[sym_b],
        call_sites=[
            CallSite(
                caller_symbol_id="mod.b", callee_name="mod.d", file_path="b.py", line_number=2
            ),
        ],
    )
    ast_c = ASTParseResult(
        file_path="c.py",
        symbols=[sym_c],
        call_sites=[
            CallSite(
                caller_symbol_id="mod.c", callee_name="mod.d", file_path="c.py", line_number=2
            ),
        ],
    )
    ast_d = ASTParseResult(
        file_path="d.py",
        symbols=[sym_d],
        call_sites=[],
    )

    builder.build([ast_a, ast_b, ast_c, ast_d])

    # Modifying leaf symbol 'mod.d' has blast radius impacting mod.b, mod.c, and mod.a
    blast = builder.get_blast_radius("mod.d")
    assert "mod.b" in blast
    assert "mod.c" in blast
    assert "mod.a" in blast

    affected_files = builder.get_affected_files("mod.d")
    assert affected_files == ["a.py", "b.py", "c.py", "d.py"]
