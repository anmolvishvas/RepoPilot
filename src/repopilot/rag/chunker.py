"""AST syntactic chunker slicing source code along exact node boundaries."""

from __future__ import annotations

from pathlib import Path

from repopilot.ast.models import ASTParseResult, SymbolInfo
from repopilot.ast.symbol_table import SymbolTableBuilder
from repopilot.rag.models import CodeChunk


class ASTChunker:
    """Chunks source code along semantic AST nodes without token fractures."""

    def __init__(self, symbol_builder: SymbolTableBuilder | None = None) -> None:
        self.symbol_builder = symbol_builder or SymbolTableBuilder()

    def chunk_parse_result(self, parse_result: ASTParseResult, source_code: str) -> list[CodeChunk]:
        """Convert an ASTParseResult into structured semantic CodeChunk units."""
        chunks: list[CodeChunk] = []
        code_bytes = source_code.encode("utf-8")
        chunked_byte_ranges: list[tuple[int, int]] = []

        # 1. Chunk every extracted callable or class symbol
        for symbol in parse_result.symbols:
            chunk = self._symbol_to_chunk(symbol, code_bytes, parse_result.imports)
            chunks.append(chunk)
            chunked_byte_ranges.append(symbol.byte_range)

        # 2. Capture any remaining module-level code (e.g. constants, config assignments)
        remaining_code = self._extract_uncovered_code(code_bytes, chunked_byte_ranges)
        if remaining_code.strip():
            chunks.append(
                CodeChunk(
                    chunk_id=f"{parse_result.file_path}::module_globals",
                    file_path=parse_result.file_path,
                    symbol_id=f"{Path(parse_result.file_path).stem}::globals",
                    symbol_type="module_globals",
                    code=remaining_code.strip(),
                    start_line=0,
                    end_line=source_code.count("\n"),
                    imports=parse_result.imports,
                )
            )

        return chunks

    def chunk_file(self, file_path: Path | str) -> list[CodeChunk]:
        """Read a file from disk, parse its AST, and return syntactic chunks."""
        path = Path(file_path)
        if not path.exists():
            return []

        content = path.read_text(encoding="utf-8")
        parse_res = self.symbol_builder.build_from_file(path)
        if parse_res.is_err:
            return []

        return self.chunk_parse_result(parse_res.unwrap(), content)

    def _symbol_to_chunk(
        self, symbol: SymbolInfo, code_bytes: bytes, imports: list[str]
    ) -> CodeChunk:
        """Slice snippet directly from source bytes preserving exact whitespace."""
        start_byte, end_byte = symbol.byte_range
        snippet = code_bytes[start_byte:end_byte].decode("utf-8", errors="replace")
        param_names = [p.name for p in symbol.parameters]

        return CodeChunk(
            chunk_id=f"{symbol.file_path}::{symbol.id}",
            file_path=symbol.file_path,
            symbol_id=symbol.id,
            symbol_type=symbol.symbol_type.value,
            code=snippet,
            start_line=symbol.range.start.line,
            end_line=symbol.range.end.line,
            docstring=symbol.docstring,
            parent_symbol=symbol.parent_symbol,
            parameters=param_names,
            imports=imports,
        )

    def _extract_uncovered_code(
        self, code_bytes: bytes, covered_ranges: list[tuple[int, int]]
    ) -> str:
        """Extract top-level statements not enclosed in any function or class."""
        sorted_ranges = sorted(covered_ranges, key=lambda r: r[0])
        uncovered_parts: list[str] = []
        current_idx = 0

        for start, end in sorted_ranges:
            if start > current_idx:
                part = code_bytes[current_idx:start].decode("utf-8", errors="replace")
                # Filter out pure blank lines and comments
                if any(
                    line.strip() and not line.strip().startswith(("#", "import", "from"))
                    for line in part.splitlines()
                ):
                    uncovered_parts.append(part)
            current_idx = max(current_idx, end)

        if current_idx < len(code_bytes):
            part = code_bytes[current_idx:].decode("utf-8", errors="replace")
            if any(
                line.strip() and not line.strip().startswith(("#", "import", "from"))
                for line in part.splitlines()
            ):
                uncovered_parts.append(part)

        return "\n".join(uncovered_parts)
