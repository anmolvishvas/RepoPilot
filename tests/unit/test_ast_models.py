"""Unit tests for AST and Call Graph domain models."""

import pytest
from pydantic import ValidationError

from repopilot.ast.models import (
    ASTParseResult,
    CallGraph,
    CallGraphEdge,
    CallGraphNode,
    CallSite,
    ParameterInfo,
    Position,
    Range,
    SymbolInfo,
    SymbolType,
)


def test_position_and_range() -> None:
    pos_start = Position(line=0, character=0)
    pos_end = Position(line=10, character=4)
    span = Range(start=pos_start, end=pos_end)

    assert span.start.line == 0
    assert span.end.character == 4

    with pytest.raises(ValidationError):
        Position(line=-1, character=0)


def test_symbol_info_creation() -> None:
    symbol = SymbolInfo(
        id="repopilot.core.parser.parse",
        name="parse",
        file_path="src/repopilot/core/parser.py",
        symbol_type=SymbolType.FUNCTION,
        range=Range(start=Position(line=5, character=0), end=Position(line=20, character=0)),
        byte_range=(120, 480),
        docstring="Parse source code into an AST.",
        parameters=[ParameterInfo(name="code", type_annotation="str")],
        return_type="ASTParseResult",
        is_async=False,
    )

    assert symbol.name == "parse"
    assert symbol.symbol_type == SymbolType.FUNCTION
    assert symbol.parameters[0].name == "code"
    assert symbol.is_async is False


def test_call_graph_traversal() -> None:
    node_a = CallGraphNode(
        symbol_id="module.func_a",
        file_path="src/module.py",
        symbol_type=SymbolType.FUNCTION,
        name="func_a",
    )
    node_b = CallGraphNode(
        symbol_id="module.func_b",
        file_path="src/module.py",
        symbol_type=SymbolType.ASYNC_FUNCTION,
        name="func_b",
    )
    node_c = CallGraphNode(
        symbol_id="module.func_c",
        file_path="src/module.py",
        symbol_type=SymbolType.FUNCTION,
        name="func_c",
    )

    edges = [
        CallGraphEdge(
            source_id="module.func_a",
            target_id="module.func_b",
            is_awaited=True,
            call_site_line=12,
        ),
        CallGraphEdge(
            source_id="module.func_c",
            target_id="module.func_b",
            is_awaited=True,
            call_site_line=45,
        ),
    ]

    graph = CallGraph(
        nodes={"module.func_a": node_a, "module.func_b": node_b, "module.func_c": node_c},
        edges=edges,
    )

    # func_a calls func_b
    assert graph.get_callees("module.func_a") == ["module.func_b"]
    # func_b is called by func_a and func_c (blast radius)
    callers = graph.get_callers("module.func_b")
    assert "module.func_a" in callers
    assert "module.func_c" in callers
    assert graph.get_callees("module.func_b") == []


def test_ast_parse_result() -> None:
    res = ASTParseResult(
        file_path="src/service.py",
        symbols=[],
        call_sites=[
            CallSite(
                caller_symbol_id="service.run",
                callee_name="client.fetch",
                file_path="src/service.py",
                line_number=25,
                is_awaited=True,
            )
        ],
        imports=["import httpx", "from typing import Optional"],
        syntax_valid=True,
    )
    assert res.syntax_valid is True
    assert len(res.call_sites) == 1
    assert res.call_sites[0].is_awaited is True
