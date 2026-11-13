"""Unit tests for the directed call-graph and blast-radius calculator."""

from repopilot.ast.call_graph import CallGraphBuilder
from repopilot.ast.models import (
    ASTParseResult,
    CallSite,
    Position,
    Range,
    SymbolInfo,
    SymbolType,
)


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


def test_call_graph_resolution_and_blast_radius() -> None:
    builder = CallGraphBuilder()

    # Three files:
    # client.py has 'client.request'
    # service.py has 'service.fetch_user' which calls 'client.request'
    # handler.py has 'handler.handle_get' which calls 'service.fetch_user'
    sym_request = _make_symbol("client.request", "src/client.py")
    sym_fetch = _make_symbol("service.fetch_user", "src/service.py")
    sym_handle = _make_symbol("handler.handle_get", "src/handler.py")

    parse_client = ASTParseResult(
        file_path="src/client.py",
        symbols=[sym_request],
        call_sites=[],
    )
    parse_service = ASTParseResult(
        file_path="src/service.py",
        symbols=[sym_fetch],
        call_sites=[
            CallSite(
                caller_symbol_id="service.fetch_user",
                callee_name="client.request",
                file_path="src/service.py",
                line_number=5,
                is_awaited=True,
            )
        ],
    )
    parse_handler = ASTParseResult(
        file_path="src/handler.py",
        symbols=[sym_handle],
        call_sites=[
            CallSite(
                caller_symbol_id="handler.handle_get",
                callee_name="service.fetch_user",
                file_path="src/handler.py",
                line_number=12,
                is_awaited=True,
            )
        ],
    )

    builder.add_parse_result(parse_client)
    builder.add_parse_result(parse_service)
    builder.add_parse_result(parse_handler)

    # Direct callees
    assert builder.get_callees("handler.handle_get") == ["service.fetch_user"]
    assert builder.get_callees("service.fetch_user") == ["client.request"]
    assert builder.get_callees("client.request") == []

    # Direct callers
    assert builder.get_callers("client.request") == ["service.fetch_user"]

    # Transitive Blast Radius of client.request:
    # Modifying client.request affects service.fetch_user and handler.handle_get!
    blast_radius = builder.get_blast_radius("client.request")
    assert "service.fetch_user" in blast_radius
    assert "handler.handle_get" in blast_radius
    assert len(blast_radius) == 2

    # Affected files
    affected_files = builder.get_affected_files("client.request")
    assert "src/client.py" in affected_files
    assert "src/service.py" in affected_files
    assert "src/handler.py" in affected_files

    # Bottom-up migration order: leaves first
    order = builder.get_topological_migration_order()
    idx_request = order.index("client.request")
    idx_fetch = order.index("service.fetch_user")
    idx_handle = order.index("handler.handle_get")
    assert idx_request < idx_fetch < idx_handle

    # Model export
    graph_model = builder.to_model()
    assert len(graph_model.nodes) == 3
    assert len(graph_model.edges) == 2


def test_call_graph_cyclic_dependency_fallback() -> None:
    builder = CallGraphBuilder()
    sym_a = _make_symbol("pkg.service_a", "src/service_a.py")
    sym_b = _make_symbol("pkg.service_b", "src/service_b.py")

    builder.add_symbol(sym_a)
    builder.add_symbol(sym_b)
    # A calls B and B calls A (Cycle)
    builder.add_call_edge("pkg.service_a", "pkg.service_b")
    builder.add_call_edge("pkg.service_b", "pkg.service_a")

    order = builder.get_topological_migration_order()
    assert len(order) == 2
    assert "pkg.service_a" in order
    assert "pkg.service_b" in order


def test_call_graph_sibling_scope_resolution() -> None:
    builder = CallGraphBuilder()
    sym_method1 = _make_symbol("service.UserService.get_user", "src/service.py")
    sym_method2 = _make_symbol("service.UserService.get_cached_user", "src/service.py")

    parse = ASTParseResult(
        file_path="src/service.py",
        symbols=[sym_method1, sym_method2],
        call_sites=[
            CallSite(
                caller_symbol_id="service.UserService.get_cached_user",
                callee_name="self.get_user",
                file_path="src/service.py",
                line_number=20,
            )
        ],
    )
    builder.add_parse_result(parse)

    assert builder.get_callees("service.UserService.get_cached_user") == [
        "service.UserService.get_user"
    ]


def test_call_graph_unknown_symbols_graceful() -> None:
    builder = CallGraphBuilder()
    assert builder.get_callees("unknown.id") == []
    assert builder.get_callers("unknown.id") == []
    assert builder.get_blast_radius("unknown.id") == []
    assert builder.get_affected_files("unknown.id") == []
