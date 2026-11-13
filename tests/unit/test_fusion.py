"""Unit tests for Reciprocal Rank Fusion."""

from repopilot.rag.fusion import reciprocal_rank_fusion
from repopilot.rag.models import CodeChunk, ScoredChunk


def _make_chunk(cid: str) -> CodeChunk:
    return CodeChunk(
        chunk_id=cid,
        file_path=f"src/{cid}.py",
        code=f"code for {cid}",
        start_line=1,
        end_line=5,
    )


def test_reciprocal_rank_fusion_merging() -> None:
    c1 = _make_chunk("chunk_1")
    c2 = _make_chunk("chunk_2")
    c3 = _make_chunk("chunk_3")

    dense_results = [
        ScoredChunk(chunk=c1, score=0.95, source="dense"),
        ScoredChunk(chunk=c2, score=0.80, source="dense"),
    ]
    sparse_results = [
        ScoredChunk(chunk=c2, score=12.4, source="sparse"),
        ScoredChunk(chunk=c3, score=8.2, source="sparse"),
    ]

    # chunk_2 appears in both dense (rank 2) and sparse (rank 1), so its RRF score should be highest!
    fused = reciprocal_rank_fusion(dense_results, sparse_results, k=60, limit=10)

    assert len(fused) == 3
    assert fused[0].chunk.chunk_id == "chunk_2"
    assert fused[0].source == "rrf"

    # Verify score calculation:
    # rank 2 in dense -> 1/(60+2) = 1/62 = 0.016129
    # rank 1 in sparse -> 1/(60+1) = 1/61 = 0.016393
    # sum = 0.032522
    assert fused[0].score > fused[1].score


def test_reciprocal_rank_fusion_empty_inputs() -> None:
    assert reciprocal_rank_fusion([], []) == []
