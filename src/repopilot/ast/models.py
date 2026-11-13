"""Pydantic v2 domain schemas for AST structures, symbols, and call graphs."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SymbolType(StrEnum):
    """Enumeration of AST symbol types."""

    FUNCTION = "function"
    ASYNC_FUNCTION = "async_function"
    METHOD = "method"
    ASYNC_METHOD = "async_method"
    CLASS = "class"
    MODULE = "module"
    IMPORT = "import"
    VARIABLE = "variable"


class Position(BaseModel):
    """Zero-indexed position in a source code file."""

    model_config = ConfigDict(strict=True, frozen=True)

    line: int = Field(ge=0, description="Zero-indexed line number")
    character: int = Field(ge=0, description="Zero-indexed character offset within the line")


class Range(BaseModel):
    """Range span bounded by start and end positions."""

    model_config = ConfigDict(strict=True, frozen=True)

    start: Position
    end: Position


class ParameterInfo(BaseModel):
    """Metadata describing a function or method parameter."""

    model_config = ConfigDict(strict=True, frozen=True)

    name: str = Field(min_length=1)
    type_annotation: str | None = None
    default_value: str | None = None


class SymbolInfo(BaseModel):
    """Comprehensive representation of an extracted AST symbol."""

    model_config = ConfigDict(strict=True, frozen=True)

    id: str = Field(min_length=1, description="Fully qualified symbol identifier")
    name: str = Field(min_length=1, description="Bare symbol name")
    file_path: str = Field(min_length=1, description="Relative file path within repository")
    symbol_type: SymbolType
    range: Range
    byte_range: tuple[int, int]
    docstring: str | None = None
    parent_symbol: str | None = None
    parameters: list[ParameterInfo] = Field(default_factory=list)
    return_type: str | None = None
    decorators: list[str] = Field(default_factory=list)
    is_async: bool = False


class CallSite(BaseModel):
    """Represents a call invocation within a function body."""

    model_config = ConfigDict(strict=True, frozen=True)

    caller_symbol_id: str = Field(min_length=1, description="Identifier of enclosing caller symbol")
    callee_name: str = Field(min_length=1, description="Name or expression of called function")
    resolved_callee_id: str | None = Field(
        default=None, description="Resolved qualified identifier of callee, if known"
    )
    file_path: str = Field(min_length=1)
    line_number: int = Field(ge=1, description="1-based line number of the call site")
    is_awaited: bool = False


class CallGraphNode(BaseModel):
    """Vertex in the codebase call graph."""

    model_config = ConfigDict(strict=True, frozen=True)

    symbol_id: str = Field(min_length=1)
    file_path: str = Field(min_length=1)
    symbol_type: SymbolType
    name: str = Field(min_length=1)


class CallGraphEdge(BaseModel):
    """Directed edge in the call graph (source calls target)."""

    model_config = ConfigDict(strict=True, frozen=True)

    source_id: str = Field(min_length=1, description="Calling symbol ID")
    target_id: str = Field(min_length=1, description="Target called symbol ID")
    is_awaited: bool = False
    call_site_line: int = Field(ge=1)


class CallGraph(BaseModel):
    """Directed call graph representing repository dependency relationships."""

    model_config = ConfigDict(strict=True, frozen=True)

    nodes: dict[str, CallGraphNode] = Field(default_factory=dict)
    edges: list[CallGraphEdge] = Field(default_factory=list)

    def get_callees(self, symbol_id: str) -> list[str]:
        """Return IDs of symbols called by the given symbol."""
        return [edge.target_id for edge in self.edges if edge.source_id == symbol_id]

    def get_callers(self, symbol_id: str) -> list[str]:
        """Return IDs of symbols that call the given symbol (reverse blast radius)."""
        return [edge.source_id for edge in self.edges if edge.target_id == symbol_id]


class ASTParseResult(BaseModel):
    """Output artifact resulting from parsing an individual file."""

    model_config = ConfigDict(strict=True, frozen=True)

    file_path: str = Field(min_length=1)
    symbols: list[SymbolInfo] = Field(default_factory=list)
    call_sites: list[CallSite] = Field(default_factory=list)
    imports: list[str] = Field(default_factory=list)
    syntax_valid: bool = True
    error_message: str | None = None
