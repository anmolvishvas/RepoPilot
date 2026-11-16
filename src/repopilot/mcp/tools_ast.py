"""AST symbol exploration and dependency blast-radius MCP tool implementations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from repopilot.ast.call_graph import CallGraphBuilder
from repopilot.ast.models import SymbolInfo
from repopilot.ast.symbol_table import SymbolTableBuilder
from repopilot.core.exceptions import ASTParseError, RepoPilotError
from repopilot.core.result import Err, Ok, Result


def search_ast_symbols(
    repo_root: Path | str,
    relative_path: str,
    query: str = "",
    symbol_builder: SymbolTableBuilder | None = None,
) -> Result[list[SymbolInfo], ASTParseError]:
    """Parse a file and search its extracted symbol table."""
    root = Path(repo_root).resolve()
    target = (root / relative_path).resolve()

    if not target.is_relative_to(root):
        return Err(ASTParseError(f"Access denied: {relative_path} traverses outside repo root."))

    if not target.exists():
        return Err(ASTParseError(f"File not found: {relative_path}"))

    builder = symbol_builder or SymbolTableBuilder()
    parse_res = builder.build_from_file(target)
    if parse_res.is_err:
        return Err(parse_res.unwrap_err())

    all_symbols = parse_res.unwrap().symbols
    if not query:
        return Ok(all_symbols)

    q = query.lower()
    filtered = [s for s in all_symbols if q in s.name.lower() or q in s.id.lower()]
    return Ok(filtered)


def get_symbol_blast_radius(
    call_graph: CallGraphBuilder,
    symbol_id: str,
) -> Result[dict[str, Any], RepoPilotError]:
    """Calculate the downstream affected callers and files when a symbol signature changes."""
    callees = call_graph.get_callees(symbol_id)
    callers = call_graph.get_callers(symbol_id)
    blast_radius = call_graph.get_blast_radius(symbol_id)
    affected_files = call_graph.get_affected_files(symbol_id)

    return Ok(
        {
            "symbol_id": symbol_id,
            "callees": callees,
            "callers": callers,
            "blast_radius": blast_radius,
            "affected_files": affected_files,
            "impact_count": len(blast_radius),
        }
    )
