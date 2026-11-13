"""FlashRank cross-encoder reranker for high-precision code chunk re-scoring."""

from __future__ import annotations

from flashrank import Ranker, RerankRequest

from repopilot.rag.models import ScoredChunk


class FlashRankReranker:
    """Lightweight, ultra-fast CPU cross-encoder reranker."""

    def __init__(self, model_name: str = "ms-marco-TinyBERT-L-2-v2") -> None:
        self.model_name = model_name
        self._ranker: Ranker | None = None

    def _get_ranker(self) -> Ranker:
        """Lazy load the FlashRank ranker model."""
        if self._ranker is None:
            self._ranker = Ranker(model_name=self.model_name)
        return self._ranker

    def rerank(
        self, query: str, candidates: list[ScoredChunk], top_k: int = 5
    ) -> list[ScoredChunk]:
        """Rerank candidates using deep query-document cross-attention."""
        if not candidates:
            return []

        try:
            ranker = self._get_ranker()
            passages = [
                {"id": scored.chunk.chunk_id, "text": scored.chunk.to_searchable_text()}
                for scored in candidates
            ]
            request = RerankRequest(query=query, passages=passages)
            ranked_results = ranker.rerank(request)

            chunk_map = {scored.chunk.chunk_id: scored.chunk for scored in candidates}
            reranked_chunks: list[ScoredChunk] = []

            for item in ranked_results[:top_k]:
                cid = str(item["id"])
                if cid in chunk_map:
                    reranked_chunks.append(
                        ScoredChunk(
                            chunk=chunk_map[cid],
                            score=float(item.get("score", 0.0)),
                            source="reranker",
                        )
                    )

            return reranked_chunks
        except Exception:
            # Fallback to existing candidate ordering if cross-encoder inference encounters an issue
            return candidates[:top_k]
