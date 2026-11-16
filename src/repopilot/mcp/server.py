"""FastMCP Code Server exposing AST, RAG, file editing, and sandbox test tools."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from repopilot.ast.call_graph import CallGraphBuilder
from repopilot.ast.symbol_table import SymbolTableBuilder
from repopilot.mcp.tools_ast import get_symbol_blast_radius as tool_get_blast_radius
from repopilot.mcp.tools_ast import search_ast_symbols as tool_search_ast
from repopilot.mcp.tools_file import apply_unified_diff as tool_apply_diff
from repopilot.mcp.tools_file import read_file_range as tool_read_range
from repopilot.mcp.tools_sandbox import run_isolated_tests_tool
from repopilot.rag.engine import HybridCodeRAG
from repopilot.sandbox.runner import DockerSandboxRunner


def create_mcp_server(
    repo_root: Path | str | None = None,
    rag_engine: HybridCodeRAG | None = None,
    sandbox_runner: DockerSandboxRunner | None = None,
) -> FastMCP:
    """Factory creating a configured FastMCP server bound to a target repository."""
    root_path = Path(repo_root or os.getcwd()).resolve()
    mcp = FastMCP("RepoPilot Code Intelligence Server")

    symbol_builder = SymbolTableBuilder()
    call_graph = CallGraphBuilder()
    rag = rag_engine or HybridCodeRAG()
    runner = sandbox_runner or DockerSandboxRunner()

    @mcp.tool()
    def search_ast_symbols(file_path: str, query: str = "") -> list[dict[str, Any]]:
        """Search AST symbols in a given file by identifier or query string."""
        res = tool_search_ast(
            repo_root=root_path,
            relative_path=file_path,
            query=query,
            symbol_builder=symbol_builder,
        )
        if res.is_err:
            return [{"error": res.unwrap_err().message}]
        return [sym.model_dump() for sym in res.unwrap()]

    @mcp.tool()
    def get_symbol_blast_radius(symbol_id: str) -> dict[str, Any]:
        """Compute the downstream blast radius (affected callers and files) for a symbol."""
        res = tool_get_blast_radius(call_graph=call_graph, symbol_id=symbol_id)
        if res.is_err:
            return {"error": res.unwrap_err().message}
        return res.unwrap()

    @mcp.tool()
    def read_file_range(relative_path: str, start_line: int = 1, end_line: int = 100) -> str:
        """Safely read a specific line range from a file, preventing path traversal attacks."""
        res = tool_read_range(
            repo_root=root_path,
            relative_path=relative_path,
            start_line=start_line,
            end_line=end_line,
        )
        if res.is_err:
            return f"Error: {res.unwrap_err().message}"
        return res.unwrap()

    @mcp.tool()
    def apply_unified_diff(target_file: str, patch_str: str) -> str:
        """Validate and apply a unified diff to a file, verifying AST syntax before committing."""
        res = tool_apply_diff(
            repo_root=root_path,
            target_file=target_file,
            patch_str=patch_str,
        )
        if res.is_err:
            return f"Error: {res.unwrap_err().message}"
        return res.unwrap()

    @mcp.tool()
    def run_isolated_tests(
        test_path: str | None = None, timeout_seconds: int = 60
    ) -> dict[str, Any]:
        """Execute test suite in an isolated ephemeral Docker sandbox and capture output."""
        res = run_isolated_tests_tool(
            repo_root=root_path,
            test_path=test_path,
            timeout_seconds=timeout_seconds,
            runner=runner,
        )
        if res.is_err:
            return {"error": res.unwrap_err().message, "passed": False}
        return res.unwrap().model_dump()

    @mcp.tool()
    def search_code_rag(query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Search codebase using hybrid dense + sparse BM25 retrieval and FlashRank reranking."""
        search_res = rag.search(query=query, top_k=top_k)
        return [
            {
                "chunk_id": scored.chunk.chunk_id,
                "file_path": scored.chunk.file_path,
                "symbol_id": scored.chunk.symbol_id,
                "score": scored.score,
                "source": scored.source,
                "code": scored.chunk.code,
            }
            for scored in search_res.chunks
        ]

    return mcp


def main() -> None:
    """CLI entry point to run the FastMCP server over standard I/O."""
    server = create_mcp_server()
    server.run()


if __name__ == "__main__":
    main()
