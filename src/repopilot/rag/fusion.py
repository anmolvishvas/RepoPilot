"""Reciprocal Rank Fusion (RRF) for combining dense and sparse retrieval ranks."""

from __future__ import annotations

from repopilot.rag.models import CodeChunk, ScoredChunk


def reciprocal_rank_fusion(
    dense_results: list[ScoredChunk],
    sparse_results: list[ScoredChunk],
    k: int = 60,
    limit: int = 25,
) -> list[ScoredChunk]:
    """Merge and re-score dense and sparse result lists using Reciprocal Rank Fusion.

    RRF_Score(d) = sum_{m in {dense, sparse}} 1 / (k + rank_m(d))
    """
    chunk_table: dict[str, CodeChunk] = {}
    rrf_scores: dict[str, float] = {}

    # Accumulate dense ranks
    for rank, item in enumerate(dense_results, start=1):
        cid = item.chunk.chunk_id
        chunk_table[cid] = item.chunk
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (k + rank))

    # Accumulate sparse ranks
    for rank, item in enumerate(sparse_results, start=1):
        cid = item.chunk.chunk_id
        chunk_table[cid] = item.chunk
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (k + rank))

    # Sort candidates by combined RRF score descending
    sorted_items = sorted(rrf_scores.items(), key=lambda entry: entry[1], reverse=True)[:limit]

    return [
        ScoredChunk(
            chunk=chunk_table[cid],
            score=round(score, 6),
            source="rrf",
        )
        for cid, score in sorted_items
    ]
