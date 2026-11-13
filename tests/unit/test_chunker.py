"""Unit tests for AST syntactic chunker."""

from pathlib import Path

from repopilot.ast.symbol_table import SymbolTableBuilder
from repopilot.rag.chunker import ASTChunker


def test_chunk_code_syntactic_boundaries() -> None:
    code = """
import os

GLOBAL_TIMEOUT = 30

def calculate_hash(data: str) -> str:
    \"\"\"Compute SHA-256 hash.\"\"\"
    return "hash_" + data

class CacheManager:
    \"\"\"Manages local caching.\"\"\"

    def get(self, key: str) -> str:
        return "val"
"""
    builder = SymbolTableBuilder()
    chunker = ASTChunker(symbol_builder=builder)

    parse_res = builder.build_from_code(code, file_path="src/cache.py", module_name="cache")
    assert parse_res.is_ok is True

    chunks = chunker.chunk_parse_result(parse_res.unwrap(), code)
    assert len(chunks) >= 3

    chunk_symbols = [c.symbol_id for c in chunks if c.symbol_id]
    assert "cache.calculate_hash" in chunk_symbols
    assert "cache.CacheManager" in chunk_symbols
    assert "cache.CacheManager.get" in chunk_symbols

    # Verify function chunk details
    fn_chunk = next(c for c in chunks if c.symbol_id == "cache.calculate_hash")
    assert fn_chunk.docstring == "Compute SHA-256 hash."
    assert "calculate_hash" in fn_chunk.code
    assert fn_chunk.parameters == ["data"]
    assert "import os" in fn_chunk.imports


def test_chunk_file_from_disk(tmp_path: Path) -> None:
    sample_file = tmp_path / "utils.py"
    sample_file.write_text("def ping() -> str:\n    return 'pong'\n", encoding="utf-8")

    chunker = ASTChunker()
    chunks = chunker.chunk_file(sample_file)

    assert len(chunks) >= 1
    assert chunks[0].symbol_id == "utils.ping"
    assert "return 'pong'" in chunks[0].code


def test_chunk_non_existent_file() -> None:
    chunker = ASTChunker()
    chunks = chunker.chunk_file("non_existent_123.py")
    assert chunks == []
