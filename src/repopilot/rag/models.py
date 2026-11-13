"""Pydantic models for Code-RAG chunks, scores, and search results."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CodeChunk(BaseModel):
    """Syntactic code chunk representing a complete semantic AST unit."""

    model_config = ConfigDict(strict=True, frozen=True)

    chunk_id: str = Field(min_length=1, description="Unique chunk identifier")
    file_path: str = Field(min_length=1)
    symbol_id: str | None = None
    symbol_type: str | None = None
    code: str = Field(min_length=1, description="Source code text of the chunk")
    start_line: int = Field(ge=0)
    end_line: int = Field(ge=0)
    docstring: str | None = None
    parent_symbol: str | None = None
    parameters: list[str] = Field(default_factory=list)
    imports: list[str] = Field(default_factory=list)

    def to_searchable_text(self) -> str:
        """Compose an enriched semantic text representation for embedding."""
        parts: list[str] = [f"File: {self.file_path}"]
        if self.symbol_id:
            parts.append(f"Symbol: {self.symbol_id}")
        if self.symbol_type:
            parts.append(f"Type: {self.symbol_type}")
        if self.parameters:
            parts.append(f"Parameters: {', '.join(self.parameters)}")
        if self.docstring:
            parts.append(f"Documentation: {self.docstring}")
        parts.append(f"Code:\n{self.code}")
        return "\n".join(parts)


class ScoredChunk(BaseModel):
    """CodeChunk paired with a relevance score and attribution source."""

    model_config = ConfigDict(strict=True, frozen=True)

    chunk: CodeChunk
    score: float
    source: str = Field(default="hybrid", description="dense, sparse, rrf, or reranker")


class RAGSearchResult(BaseModel):
    """Aggregated outcome of a hybrid search and rerank pipeline execution."""

    model_config = ConfigDict(strict=True, frozen=True)

    query: str
    chunks: list[ScoredChunk] = Field(default_factory=list)
    total_candidates: int = Field(ge=0)
