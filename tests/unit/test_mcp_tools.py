"""Unit tests for MCP tool functions."""

from pathlib import Path

from repopilot.ast.call_graph import CallGraphBuilder
from repopilot.ast.models import (
    ASTParseResult,
    CallSite,
    Position,
    Range,
    SymbolInfo,
    SymbolType,
)
from repopilot.core.exceptions import DiffApplicationError
from repopilot.mcp.tools_ast import get_symbol_blast_radius, search_ast_symbols
from repopilot.mcp.tools_file import apply_unified_diff, read_file_range
from repopilot.mcp.tools_sandbox import run_isolated_tests_tool
from repopilot.sandbox.runner import DockerSandboxRunner


def _make_symbol(id: str, file_path: str) -> SymbolInfo:
    name = id.split(".")[-1]
    return SymbolInfo(
        id=id,
        name=name,
        file_path=file_path,
        symbol_type=SymbolType.FUNCTION,
        range=Range(start=Position(line=1, character=0), end=Position(line=10, character=0)),
        byte_range=(0, 100),
    )


def test_read_file_range_success(tmp_path: Path) -> None:
    sample_file = tmp_path / "hello.py"
    sample_file.write_text("line 1\nline 2\nline 3\nline 4\nline 5\n", encoding="utf-8")

    res = read_file_range(repo_root=tmp_path, relative_path="hello.py", start_line=2, end_line=4)
    assert res.is_ok
    assert res.unwrap() == "line 2\nline 3\nline 4\n"


def test_read_file_range_path_traversal(tmp_path: Path) -> None:
    outside = tmp_path.parent / "forbidden.txt"
    outside.write_text("secret", encoding="utf-8")

    res = read_file_range(repo_root=tmp_path, relative_path="../forbidden.txt")
    assert res.is_err
    assert "traverses outside" in res.unwrap_err().message


def test_read_file_range_not_found(tmp_path: Path) -> None:
    res = read_file_range(repo_root=tmp_path, relative_path="missing.py")
    assert res.is_err
    assert "File not found" in res.unwrap_err().message


def test_apply_unified_diff_success(tmp_path: Path) -> None:
    src_file = tmp_path / "calc.py"
    src_file.write_text(
        "def compute():\n    x = 1\n    return x\n",
        encoding="utf-8",
    )

    patch_str = """--- a/calc.py
+++ b/calc.py
@@ -1,3 +1,3 @@
 def compute():
-    x = 1
+    x = 2
     return x
"""
    res = apply_unified_diff(repo_root=tmp_path, target_file="calc.py", patch_str=patch_str)
    assert res.is_ok
    assert "Successfully applied" in res.unwrap()
    assert src_file.read_text(encoding="utf-8") == "def compute():\n    x = 2\n    return x\n"


def test_apply_unified_diff_syntax_error_rejection(tmp_path: Path) -> None:
    src_file = tmp_path / "broken.py"
    initial_content = "def ok_func():\n    return True\n"
    src_file.write_text(initial_content, encoding="utf-8")

    bad_patch = """--- a/broken.py
+++ b/broken.py
@@ -1,2 +1,2 @@
 def ok_func():
-    return True
+    return def invalid_syntax!!
"""
    res = apply_unified_diff(repo_root=tmp_path, target_file="broken.py", patch_str=bad_patch)
    assert res.is_err
    assert isinstance(res.unwrap_err(), DiffApplicationError)
    assert "syntax errors" in res.unwrap_err().message
    # Ensure original file was preserved intact
    assert src_file.read_text(encoding="utf-8") == initial_content


def test_apply_unified_diff_traversal(tmp_path: Path) -> None:
    res = apply_unified_diff(repo_root=tmp_path, target_file="../evil.py", patch_str="diff")
    assert res.is_err
    assert "traversal" in res.unwrap_err().message.lower()


def test_search_ast_symbols_success(tmp_path: Path) -> None:
    code_file = tmp_path / "service.py"
    code_file.write_text(
        "class OrderService:\n    def create_order(self):\n        pass\n",
        encoding="utf-8",
    )

    res = search_ast_symbols(repo_root=tmp_path, relative_path="service.py", query="Order")
    assert res.is_ok
    symbols = res.unwrap()
    assert any(s.name == "OrderService" for s in symbols)


def test_get_symbol_blast_radius() -> None:
    builder = CallGraphBuilder()
    sym_caller = _make_symbol("mod.caller", "mod.py")
    sym_callee = _make_symbol("mod.callee", "mod.py")

    ast_caller = ASTParseResult(
        file_path="mod.py",
        symbols=[sym_caller, sym_callee],
        call_sites=[
            CallSite(
                caller_symbol_id="mod.caller",
                callee_name="mod.callee",
                file_path="mod.py",
                line_number=3,
            )
        ],
    )
    builder.build([ast_caller])

    res = get_symbol_blast_radius(call_graph=builder, symbol_id="mod.callee")
    assert res.is_ok
    data = res.unwrap()
    assert data["symbol_id"] == "mod.callee"
    assert "mod.caller" in data["callers"]
    assert "mod.caller" in data["blast_radius"]
    assert data["impact_count"] == 1


def test_run_isolated_tests_tool(tmp_path: Path) -> None:
    runner = DockerSandboxRunner(allow_fallback=True)
    res = run_isolated_tests_tool(repo_root=tmp_path, runner=runner)
    assert res.is_ok
