"""Tree-sitter AST parser binding multi-language grammars with strict validation."""

from __future__ import annotations

from pathlib import Path

import tree_sitter_python as tspython
from tree_sitter import Language, Node, Parser, Tree

from repopilot.core.exceptions import ASTParseError
from repopilot.core.result import Err, Ok, Result


class TreeSitterParser:
    """Multi-language AST parser wrapping Tree-sitter grammars."""

    def __init__(self, language_name: str = "python") -> None:
        self.language_name = language_name.lower()
        if self.language_name == "python":
            self.language = Language(tspython.language())
        else:
            raise ValueError(f"Unsupported language grammar: {language_name}")

        self._parser = Parser(self.language)

    def parse_code(
        self, source_code: str, file_path: str = "<memory>"
    ) -> Result[Tree, ASTParseError]:
        """Parse source code string into a Tree-sitter syntax tree."""
        try:
            encoded_bytes = source_code.encode("utf-8")
            tree = self._parser.parse(encoded_bytes)
            if tree is None:
                return Err(ASTParseError(f"Failed to generate syntax tree for {file_path}"))
            return Ok(tree)
        except Exception as exc:
            return Err(ASTParseError(f"Exception while parsing {file_path}", details=str(exc)))

    def parse_file(self, file_path: Path | str) -> Result[Tree, ASTParseError]:
        """Read and parse a file from disk into a Tree-sitter syntax tree."""
        path = Path(file_path)
        if not path.exists():
            return Err(ASTParseError(f"File not found: {path}"))

        try:
            content = path.read_text(encoding="utf-8")
            return self.parse_code(content, file_path=str(path))
        except Exception as exc:
            return Err(ASTParseError(f"Failed reading file {path}", details=str(exc)))

    def has_syntax_errors(self, tree: Tree) -> bool:
        """Check if any node in the syntax tree has syntax errors."""
        return bool(tree.root_node.has_error)

    def find_syntax_errors(self, node: Node, code_bytes: bytes) -> list[str]:
        """Recursively collect error messages from ERROR or MISSING nodes."""
        errors: list[str] = []
        if node.type == "ERROR" or node.is_missing:
            start_row = node.start_point.row + 1
            start_col = node.start_point.column
            snippet = code_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")
            desc = "Missing token" if node.is_missing else f"Unexpected syntax: {snippet!r}"
            errors.append(f"Line {start_row}:{start_col} - {desc}")

        for child in node.children:
            errors.extend(self.find_syntax_errors(child, code_bytes))

        return errors
