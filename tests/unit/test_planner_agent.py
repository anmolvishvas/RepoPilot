"""Unit tests for the Planner & Supervisor Agent."""

from pathlib import Path

from repopilot.agents.planner import PlannerAgent, planner_node
from repopilot.agents.state import MigrationPhase, MigrationState
from repopilot.ast.call_graph import CallGraphBuilder
from repopilot.ast.models import ASTParseResult, CallSite, Position, Range, SymbolInfo, SymbolType


def _make_func_symbol(id: str, file_path: str) -> SymbolInfo:
    name = id.split(".")[-1]
    return SymbolInfo(
        id=id,
        name=name,
        file_path=file_path,
        symbol_type=SymbolType.FUNCTION,
        range=Range(start=Position(line=1, character=0), end=Position(line=5, character=0)),
        byte_range=(0, 50),
    )


def test_planner_generate_plan_success(tmp_path: Path) -> None:
    f1 = tmp_path / "callee.py"
    f1.write_text("def fetch_data():\n    return 42\n", encoding="utf-8")
    f2 = tmp_path / "caller.py"
    f2.write_text(
        "from callee import fetch_data\ndef run():\n    return fetch_data()\n", encoding="utf-8"
    )

    call_graph = CallGraphBuilder()
    sym_callee = _make_func_symbol("callee.fetch_data", "callee.py")
    sym_caller = _make_func_symbol("caller.run", "caller.py")

    ast_callee = ASTParseResult(file_path="callee.py", symbols=[sym_callee])
    ast_caller = ASTParseResult(
        file_path="caller.py",
        symbols=[sym_caller],
        call_sites=[
            CallSite(
                caller_symbol_id="caller.run",
                callee_name="callee.fetch_data",
                file_path="caller.py",
                line_number=3,
            )
        ],
    )
    call_graph.build([ast_callee, ast_caller])

    agent = PlannerAgent(call_graph=call_graph)
    res = agent.generate_plan(recipe="sync-to-async", repo_path=tmp_path)

    assert res.is_ok
    plan = res.unwrap()
    assert plan.recipe == "sync-to-async"
    assert len(plan.steps) == 2
    assert "callee.py" in plan.affected_files
    assert "caller.py" in plan.affected_files


def test_planner_empty_recipe(tmp_path: Path) -> None:
    agent = PlannerAgent()
    res = agent.generate_plan(recipe="", repo_path=tmp_path)
    assert res.is_err
    assert "cannot be empty" in res.unwrap_err().message


def test_planner_nonexistent_repo(tmp_path: Path) -> None:
    agent = PlannerAgent()
    res = agent.generate_plan(recipe="modernize", repo_path=tmp_path / "missing")
    assert res.is_err
    assert "does not exist" in res.unwrap_err().message


def test_planner_node_execution(tmp_path: Path) -> None:
    (tmp_path / "service.py").write_text("def ping(): pass\n", encoding="utf-8")

    state = MigrationState(
        task_id="task_123",
        repo_path=str(tmp_path),
        recipe="add type stubs",
    )

    update = planner_node(state)
    assert update["phase"] == MigrationPhase.SYNTHESIZING
    assert update["plan"] is not None
    assert len(update["tool_traces"]) == 1
    assert update["tool_traces"][0].success
