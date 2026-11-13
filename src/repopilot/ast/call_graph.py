"""Directed call graph builder and blast-radius dependency calculator."""

from __future__ import annotations

import networkx as nx

from repopilot.ast.models import (
    ASTParseResult,
    CallGraph,
    CallGraphEdge,
    CallGraphNode,
    SymbolInfo,
)


class CallGraphBuilder:
    """Builds and queries cross-file directed symbol call graphs."""

    def __init__(self) -> None:
        self._graph = nx.DiGraph()
        self._symbols: dict[str, SymbolInfo] = {}
        self._name_to_ids: dict[str, list[str]] = {}

    def add_parse_result(self, parse_result: ASTParseResult) -> None:
        """Register all symbols and call sites from a file parse result."""
        for symbol in parse_result.symbols:
            self.add_symbol(symbol)

        for call_site in parse_result.call_sites:
            target_id = self._resolve_callee(call_site.callee_name, call_site.caller_symbol_id)
            if target_id and target_id != call_site.caller_symbol_id:
                self.add_call_edge(
                    source_id=call_site.caller_symbol_id,
                    target_id=target_id,
                    is_awaited=call_site.is_awaited,
                    call_site_line=call_site.line_number,
                )

    def add_symbol(self, symbol: SymbolInfo) -> None:
        """Add a symbol node to the graph."""
        self._symbols[symbol.id] = symbol
        self._name_to_ids.setdefault(symbol.name, []).append(symbol.id)

        node = CallGraphNode(
            symbol_id=symbol.id,
            file_path=symbol.file_path,
            symbol_type=symbol.symbol_type,
            name=symbol.name,
        )
        self._graph.add_node(symbol.id, data=node)

    def add_call_edge(
        self, source_id: str, target_id: str, is_awaited: bool = False, call_site_line: int = 1
    ) -> None:
        """Add a directed call edge (source_id calls target_id)."""
        if not self._graph.has_node(source_id) and source_id in self._symbols:
            self.add_symbol(self._symbols[source_id])
        if not self._graph.has_node(target_id) and target_id in self._symbols:
            self.add_symbol(self._symbols[target_id])

        self._graph.add_edge(
            source_id,
            target_id,
            is_awaited=is_awaited,
            call_site_line=call_site_line,
        )

    def get_callees(self, symbol_id: str) -> list[str]:
        """Return symbols directly called by the given symbol."""
        if not self._graph.has_node(symbol_id):
            return []
        return list(self._graph.successors(symbol_id))

    def get_callers(self, symbol_id: str) -> list[str]:
        """Return symbols that directly call the given symbol."""
        if not self._graph.has_node(symbol_id):
            return []
        return list(self._graph.predecessors(symbol_id))

    def get_blast_radius(self, symbol_id: str) -> list[str]:
        """Compute all transitive upstream callers affected by modifying symbol_id."""
        if not self._graph.has_node(symbol_id):
            return []
        # In a directed graph where A -> B (A calls B), the blast radius of B is ancestors(B)
        ancestors = nx.ancestors(self._graph, symbol_id)
        return list(ancestors)

    def get_affected_files(self, symbol_id: str) -> list[str]:
        """Return all distinct file paths affected by changes to symbol_id."""
        affected_symbol_ids = [symbol_id, *self.get_blast_radius(symbol_id)]
        files: set[str] = set()
        for sym_id in affected_symbol_ids:
            if sym_id in self._symbols:
                files.add(self._symbols[sym_id].file_path)
        return sorted(files)

    def get_topological_migration_order(self) -> list[str]:
        """Return bottom-up migration order (leaves/callees first, then callers)."""
        try:
            # Reverse topological sort so dependencies are migrated before their callers
            return list(reversed(list(nx.topological_sort(self._graph))))
        except nx.NetworkXUnfeasible:
            # Graph has cycles; fallback to standard node list
            return list(self._graph.nodes)

    def to_model(self) -> CallGraph:
        """Export internal graph to Pydantic CallGraph model."""
        nodes: dict[str, CallGraphNode] = {}
        for node_id, data in self._graph.nodes(data=True):
            if "data" in data and isinstance(data["data"], CallGraphNode):
                nodes[node_id] = data["data"]
            elif node_id in self._symbols:
                sym = self._symbols[node_id]
                nodes[node_id] = CallGraphNode(
                    symbol_id=sym.id,
                    file_path=sym.file_path,
                    symbol_type=sym.symbol_type,
                    name=sym.name,
                )

        edges: list[CallGraphEdge] = []
        for u, v, data in self._graph.edges(data=True):
            edges.append(
                CallGraphEdge(
                    source_id=u,
                    target_id=v,
                    is_awaited=data.get("is_awaited", False),
                    call_site_line=data.get("call_site_line", 1),
                )
            )

        return CallGraph(nodes=nodes, edges=edges)

    def _resolve_callee(self, callee_name: str, caller_id: str) -> str | None:
        """Resolve a called function expression to a known symbol ID."""
        if not callee_name:
            return None

        # Clean method call expressions like 'self.fetch' or 'client.fetch'
        target_name = callee_name.split(".")[-1]

        # 1. Exact match with registered symbol ID
        if callee_name in self._symbols:
            return callee_name

        # 2. Check sibling methods/functions within the same parent scope
        if "." in caller_id:
            parent_scope = caller_id.rsplit(".", 1)[0]
            scoped_id = f"{parent_scope}.{target_name}"
            if scoped_id in self._symbols:
                return scoped_id

        # 3. Match by unqualified symbol name if unique
        candidate_ids = self._name_to_ids.get(target_name, [])
        if len(candidate_ids) == 1:
            return candidate_ids[0]

        return None
