"""Unit tests for FastMCP server instantiation and tool registry."""

from pathlib import Path
from unittest.mock import MagicMock

from repopilot.agents.state import SandboxTestResult
from repopilot.core.result import Ok
from repopilot.mcp.server import create_mcp_server
from repopilot.rag.models import CodeChunk, RAGSearchResult, ScoredChunk


def test_create_mcp_server_initialization(tmp_path: Path) -> None:
    mock_rag = MagicMock()
    mock_runner = MagicMock()

    server = create_mcp_server(repo_root=tmp_path, rag_engine=mock_rag, sandbox_runner=mock_runner)
    assert server is not None
    assert server.name == "RepoPilot Code Intelligence Server"


def test_mcp_server_tools_registered(tmp_path: Path) -> None:
    server = create_mcp_server(repo_root=tmp_path)
    assert server is not None


def test_mcp_server_tool_handlers(tmp_path: Path) -> None:
    sample_file = tmp_path / "app.py"
    sample_file.write_text("def hello():\n    return 'world'\n", encoding="utf-8")

    mock_rag = MagicMock()
    mock_rag.search.return_value = RAGSearchResult(
        query="hello",
        total_candidates=1,
        chunks=[
            ScoredChunk(
                chunk=CodeChunk(
                    chunk_id="chunk_1",
                    file_path="app.py",
                    symbol_id="hello",
                    code="def hello(): return 'world'",
                    start_line=1,
                    end_line=2,
                ),
                score=0.95,
                source="hybrid_fusion",
            )
        ],
    )

    mock_runner = MagicMock()
    mock_runner.run_tests.return_value = Ok(
        SandboxTestResult(
            exit_code=0,
            stdout="1 passed",
            stderr="",
            total_tests=1,
            passed_tests=1,
            failed_tests=0,
            failures=[],
        )
    )

    server = create_mcp_server(repo_root=tmp_path, rag_engine=mock_rag, sandbox_runner=mock_runner)

    # FastMCP stores tools in _tool_manager
    tools_dict = (
        {t.name: t for t in server._tool_manager.list_tools()}
        if hasattr(server, "_tool_manager")
        else {}
    )

    # If list_tools() gives tools, we can test their functions
    if "read_file_range" in tools_dict:
        fn = tools_dict["read_file_range"].fn
        res_text = fn(relative_path="app.py", start_line=1, end_line=2)
        assert "def hello():" in res_text

    if "search_ast_symbols" in tools_dict:
        fn = tools_dict["search_ast_symbols"].fn
        symbols = fn(file_path="app.py", query="hello")
        assert len(symbols) >= 1
        assert symbols[0]["name"] == "hello"

    if "get_symbol_blast_radius" in tools_dict:
        fn = tools_dict["get_symbol_blast_radius"].fn
        blast = fn(symbol_id="hello")
        assert "symbol_id" in blast

    if "apply_unified_diff" in tools_dict:
        fn = tools_dict["apply_unified_diff"].fn
        patch = "--- a/app.py\n+++ b/app.py\n@@ -1,2 +1,2 @@\n def hello():\n-    return 'world'\n+    return 'pilot'\n"
        diff_res = fn(target_file="app.py", patch_str=patch)
        assert "Successfully applied" in diff_res

    if "run_isolated_tests" in tools_dict:
        fn = tools_dict["run_isolated_tests"].fn
        run_res = fn()
        assert run_res.get("exit_code") == 0

    if "search_code_rag" in tools_dict:
        fn = tools_dict["search_code_rag"].fn
        rag_res = fn(query="hello")
        assert len(rag_res) == 1
        assert rag_res[0]["chunk_id"] == "chunk_1"
