"""Unit and integration tests for Qdrant, FlashRank, and HybridCodeRAG."""

from repopilot.rag.engine import HybridCodeRAG
from repopilot.rag.models import CodeChunk, ScoredChunk
from repopilot.rag.reranker import FlashRankReranker
from repopilot.rag.vector_store import QdrantVectorStore


def test_qdrant_vector_store_in_memory() -> None:
    store = QdrantVectorStore(location=":memory:")
    assert store.count() == 0

    chunk = CodeChunk(
        chunk_id="file::query_db",
        file_path="src/db.py",
        symbol_id="db.query",
        symbol_type="function",
        code="def query(sql: str) -> list: pass",
        start_line=1,
        end_line=2,
    )
    store.add_chunks([chunk])
    assert store.count() == 1

    results = store.search("execute database SQL query", limit=1)
    assert len(results) == 1
    assert results[0].chunk.chunk_id == "file::query_db"
    assert results[0].source == "dense"

    # Search with non-matching file filter
    empty_res = store.search("database query", limit=1, file_filter="src/other.py")
    assert len(empty_res) == 0

    # Clear
    store.clear()
    assert store.count() == 0


def test_flashrank_reranker() -> None:
    reranker = FlashRankReranker()
    c1 = CodeChunk(
        chunk_id="c1",
        file_path="src/auth.py",
        code="def authenticate(token: str): pass",
        docstring="Verify user session token",
        start_line=1,
        end_line=2,
    )
    c2 = CodeChunk(
        chunk_id="c2",
        file_path="src/calc.py",
        code="def calculate_tax(amount: float): pass",
        docstring="Compute sales tax rate",
        start_line=1,
        end_line=2,
    )

    candidates = [
        ScoredChunk(chunk=c2, score=0.5, source="rrf"),
        ScoredChunk(chunk=c1, score=0.4, source="rrf"),
    ]

    reranked = reranker.rerank(
        query="validate authentication token", candidates=candidates, top_k=2
    )
    assert len(reranked) == 2
    assert reranked[0].chunk.chunk_id == "c1"
    assert reranked[0].source == "reranker"


def test_hybrid_code_rag_end_to_end() -> None:
    rag = HybridCodeRAG()

    code = """
def connect_redis(host: str, port: int) -> None:
    \"\"\"Establish connection to Redis cache cluster.\"\"\"
    pass

def render_markdown(text: str) -> str:
    \"\"\"Render markdown to HTML format.\"\"\"
    return "<p>" + text + "</p>"
"""
    from repopilot.ast.symbol_table import SymbolTableBuilder

    builder = SymbolTableBuilder()
    parse_res = builder.build_from_code(code, file_path="src/infra.py", module_name="infra")
    assert parse_res.is_ok is True

    indexed_count = rag.index_parse_results([(parse_res.unwrap(), code)])
    assert indexed_count >= 2

    # Query for redis connection
    res = rag.search("connect to redis caching server", top_k=1)
    assert len(res.chunks) == 1
    assert "redis" in res.chunks[0].chunk.code.lower()

    # Clear RAG
    rag.clear()
    assert rag.search("redis").chunks == []
