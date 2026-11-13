"""Rank-BM25 sparse lexical search indexer with code-aware tokenization."""

from __future__ import annotations

import re

from rank_bm25 import BM25Okapi

from repopilot.rag.models import CodeChunk, ScoredChunk


class BM25CodeIndex:
    """Sparse lexical index supporting identifier and keyword code search."""

    def __init__(self) -> None:
        self.chunks: list[CodeChunk] = []
        self._tokenized_corpus: list[list[str]] = []
        self._bm25: BM25Okapi | None = None

    def add_chunks(self, chunks: list[CodeChunk]) -> None:
        """Tokenize and add code chunks to the sparse BM25 corpus."""
        for chunk in chunks:
            self.chunks.append(chunk)
            searchable_text = chunk.to_searchable_text()
            tokens = self.tokenize(searchable_text)
            self._tokenized_corpus.append(tokens)

        if self._tokenized_corpus:
            self._bm25 = BM25Okapi(self._tokenized_corpus)

    def search(self, query: str, limit: int = 10) -> list[ScoredChunk]:
        """Execute sparse lexical search returning top scored chunks."""
        if not self._bm25 or not self.chunks:
            return []

        query_tokens = self.tokenize(query)
        if not query_tokens:
            return []

        doc_scores = self._bm25.get_scores(query_tokens)
        top_indices = sorted(range(len(doc_scores)), key=lambda i: doc_scores[i], reverse=True)[
            :limit
        ]

        results: list[ScoredChunk] = []
        for idx in top_indices:
            score = float(doc_scores[idx])
            matching_tokens = set(query_tokens).intersection(self._tokenized_corpus[idx])
            if matching_tokens or score > 0.0:
                relevance = score if score > 0.0 else float(len(matching_tokens))
                results.append(
                    ScoredChunk(
                        chunk=self.chunks[idx],
                        score=relevance,
                        source="sparse",
                    )
                )

        return results

    @staticmethod
    def tokenize(text: str) -> list[str]:
        """Perform code-aware tokenization with snake_case and camelCase decomposition."""
        raw_tokens = re.findall(r"[a-zA-Z_0-9]+", text)
        decomposed_tokens: list[str] = []

        for token in raw_tokens:
            lower_token = token.lower()
            decomposed_tokens.append(lower_token)

            # Split snake_case
            if "_" in token:
                for sub in token.split("_"):
                    if sub:
                        decomposed_tokens.append(sub.lower())

            # Split camelCase / PascalCase
            camel_parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\d|\W|$)|\d+", token)
            if len(camel_parts) > 1:
                for part in camel_parts:
                    decomposed_tokens.append(part.lower())

        return decomposed_tokens
