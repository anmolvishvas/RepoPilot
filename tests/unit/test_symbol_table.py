"""Unit tests for the AST symbol table extraction engine."""

from pathlib import Path

from repopilot.ast.models import SymbolType
from repopilot.ast.symbol_table import SymbolTableBuilder


def test_extract_symbols_from_functions_and_classes() -> None:
    code = '''
import httpx
from typing import Optional

@app_route("/users")
async def fetch_user(user_id: int) -> str:
    """Fetch user by identifier."""
    return await client.get(f"/user/{user_id}")

class UserService:
    """User service domain manager."""

    @cached
    def get_details(self, user_id: int = 1) -> dict:
        return {"id": user_id}
'''
    builder = SymbolTableBuilder()
    res = builder.build_from_code(code, file_path="src/service.py", module_name="service")

    assert res.is_ok is True
    ast_res = res.unwrap()
    assert ast_res.syntax_valid is True
    assert len(ast_res.imports) == 2

    # Check extracted symbols
    symbols_by_id = {s.id: s for s in ast_res.symbols}
    assert "service.fetch_user" in symbols_by_id
    fetch_user = symbols_by_id["service.fetch_user"]
    assert fetch_user.symbol_type == SymbolType.ASYNC_FUNCTION
    assert fetch_user.is_async is True
    assert fetch_user.docstring == "Fetch user by identifier."
    assert len(fetch_user.decorators) == 1
    assert "@app_route" in fetch_user.decorators[0]
    assert len(fetch_user.parameters) == 1
    assert fetch_user.parameters[0].name == "user_id"
    assert fetch_user.parameters[0].type_annotation == "int"

    # Check class and method
    assert "service.UserService" in symbols_by_id
    user_service = symbols_by_id["service.UserService"]
    assert user_service.symbol_type == SymbolType.CLASS

    assert "service.UserService.get_details" in symbols_by_id
    method = symbols_by_id["service.UserService.get_details"]
    assert method.symbol_type == SymbolType.METHOD
    assert method.parent_symbol == "service.UserService"
    assert len(method.decorators) == 1
    assert "@cached" in method.decorators[0]

    # Check call sites
    assert len(ast_res.call_sites) > 0
    call = ast_res.call_sites[0]
    assert call.caller_symbol_id == "service.fetch_user"
    assert "client.get" in call.callee_name
    assert call.is_awaited is True


def test_extract_from_file_on_disk(tmp_path: Path) -> None:
    builder = SymbolTableBuilder()
    p = tmp_path / "math_utils.py"
    p.write_text("def square(n: int) -> int:\n    return n * n\n", encoding="utf-8")

    res = builder.build_from_file(p)
    assert res.is_ok is True
    ast_res = res.unwrap()
    assert len(ast_res.symbols) == 1
    assert ast_res.symbols[0].name == "square"


def test_extract_syntax_error_file() -> None:
    builder = SymbolTableBuilder()
    invalid_code = "def oops(\n    return 42\n"
    res = builder.build_from_code(invalid_code, file_path="broken.py")

    assert res.is_ok is True
    ast_res = res.unwrap()
    assert ast_res.syntax_valid is False
    assert ast_res.error_message is not None
