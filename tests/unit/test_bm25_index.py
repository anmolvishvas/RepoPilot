"""Unit tests for Rank-BM25 code indexer."""

from repopilot.rag.bm25_index import BM25CodeIndex
from repopilot.rag.models import CodeChunk


def test_code_aware_tokenization() -> None:
    tokens = BM25CodeIndex.tokenize("def fetch_user_by_id(userId: int) -> UserProfile:")
    assert "fetch" in tokens
    assert "user" in tokens
    assert "by" in tokens
    assert "id" in tokens
    assert "userid" in tokens
    assert "profile" in tokens


def test_bm25_exact_symbol_search() -> None:
    chunk1 = CodeChunk(
        chunk_id="file1::test_pool",
        file_path="src/pool.py",
        symbol_id="test_connection_pool_overflow",
        symbol_type="function",
        code="def test_connection_pool_overflow(): pass",
        start_line=1,
        end_line=2,
    )
    chunk2 = CodeChunk(
        chunk_id="file2::render_template",
        file_path="src/template.py",
        symbol_id="render_html_template",
        symbol_type="function",
        code="def render_html_template(): pass",
        start_line=1,
        end_line=2,
    )

    index = BM25CodeIndex()
    index.add_chunks([chunk1, chunk2])

    # Query matching chunk 1
    results = index.search("connection pool overflow", limit=5)
    assert len(results) > 0
    assert results[0].chunk.chunk_id == "file1::test_pool"
    assert results[0].source == "sparse"
    assert results[0].score > 0.0

    # Query matching chunk 2
    results_html = index.search("render template", limit=5)
    assert len(results_html) > 0
    assert results_html[0].chunk.chunk_id == "file2::render_template"

    # Empty query returns empty
    assert index.search("") == []


def test_bm25_empty_index() -> None:
    index = BM25CodeIndex()
    assert index.search("anything") == []
