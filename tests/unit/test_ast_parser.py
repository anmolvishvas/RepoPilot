"""Unit tests for the Tree-sitter AST parser engine."""

from pathlib import Path

import pytest

from repopilot.ast.parser import TreeSitterParser


def test_parser_initialization_and_unsupported_language() -> None:
    parser = TreeSitterParser(language_name="python")
    assert parser.language_name == "python"

    with pytest.raises(ValueError, match="Unsupported language grammar"):
        TreeSitterParser(language_name="unsupported_lang")


def test_parse_valid_code() -> None:
    parser = TreeSitterParser()
    code = "def add(x: int, y: int) -> int:\n    return x + y\n"
    res = parser.parse_code(code)

    assert res.is_ok is True
    tree = res.unwrap()
    assert tree.root_node.type == "module"
    assert parser.has_syntax_errors(tree) is False


def test_parse_syntax_error_detection() -> None:
    parser = TreeSitterParser()
    invalid_code = "def broken(x: int\n    return x +\n"
    res = parser.parse_code(invalid_code)

    assert res.is_ok is True
    tree = res.unwrap()
    assert parser.has_syntax_errors(tree) is True

    errors = parser.find_syntax_errors(tree.root_node, invalid_code.encode("utf-8"))
    assert len(errors) > 0
    assert any("Line" in err for err in errors)


def test_parse_file_from_disk(tmp_path: Path) -> None:
    parser = TreeSitterParser()
    p = tmp_path / "sample.py"
    p.write_text("x = 42\n", encoding="utf-8")

    res = parser.parse_file(p)
    assert res.is_ok is True
    tree = res.unwrap()
    assert parser.has_syntax_errors(tree) is False


def test_parse_non_existent_file() -> None:
    parser = TreeSitterParser()
    res = parser.parse_file("non_existent_file_path_12345.py")
    assert res.is_err is True
    assert "File not found" in res.unwrap_err().message
