"""Unified Hybrid Code-RAG pipeline coordinator."""

from __future__ import annotations

from pathlib import Path

from repopilot.ast.models import ASTParseResult
from repopilot.rag.bm25_index import BM25CodeIndex
from repopilot.rag.chunker import ASTChunker
from repopilot.rag.fusion import reciprocal_rank_fusion
from repopilot.rag.models import CodeChunk, RAGSearchResult, ScoredChunk
from repopilot.rag.reranker import FlashRankReranker
from repopilot.rag.vector_store import QdrantVectorStore


class HybridCodeRAG:
    """Coordinates syntactic chunking, dense search, sparse search, RRF, and cross-encoder reranking."""

    def __init__(
        self,
        vector_store: QdrantVectorStore | None = None,
        sparse_index: BM25CodeIndex | None = None,
        reranker: FlashRankReranker | None = None,
        chunker: ASTChunker | None = None,
    ) -> None:
        self.chunker = chunker or ASTChunker()
        self.vector_store = vector_store or QdrantVectorStore()
        self.sparse_index = sparse_index or BM25CodeIndex()
        self.reranker = reranker or FlashRankReranker()
        self._all_chunks: list[CodeChunk] = []

    def index_files(self, file_paths: list[Path | str]) -> int:
        """Chunk and index multiple files into both dense and sparse indices."""
        all_new_chunks: list[CodeChunk] = []
        for path in file_paths:
            chunks = self.chunker.chunk_file(path)
            all_new_chunks.extend(chunks)

        return self._index_chunks(all_new_chunks)

    def index_parse_results(self, items: list[tuple[ASTParseResult, str]]) -> int:
        """Chunk and index already parsed AST results with their source codes."""
        all_new_chunks: list[CodeChunk] = []
        for parse_result, source_code in items:
            chunks = self.chunker.chunk_parse_result(parse_result, source_code)
            all_new_chunks.extend(chunks)

        return self._index_chunks(all_new_chunks)

    def _index_chunks(self, chunks: list[CodeChunk]) -> int:
        """Add chunks to dense and sparse storage."""
        if not chunks:
            return 0

        self.vector_store.add_chunks(chunks)
        self.sparse_index.add_chunks(chunks)
        self._all_chunks.extend(chunks)
        return len(chunks)

    def search(self, query: str, top_k: int = 5, file_filter: str | None = None) -> RAGSearchResult:
        """Execute hybrid search with reciprocal rank fusion and FlashRank reranking."""
        # 1. Retrieve candidates from dense and sparse search
        dense_results: list[ScoredChunk] = self.vector_store.search(
            query=query, limit=20, file_filter=file_filter
        )
        sparse_results: list[ScoredChunk] = self.sparse_index.search(query=query, limit=20)

        # 2. Merge ranks using Reciprocal Rank Fusion (RRF)
        merged_candidates = reciprocal_rank_fusion(
            dense_results=dense_results,
            sparse_results=sparse_results,
            k=60,
            limit=25,
        )

        # 3. Precision reranking via FlashRank cross-encoder
        final_reranked = self.reranker.rerank(
            query=query,
            candidates=merged_candidates,
            top_k=top_k,
        )

        return RAGSearchResult(
            query=query,
            chunks=final_reranked,
            total_candidates=len(merged_candidates),
        )

    def clear(self) -> None:
        """Clear dense and sparse index state."""
        self.vector_store.clear()
        self.sparse_index = BM25CodeIndex()
        self._all_chunks.clear()
