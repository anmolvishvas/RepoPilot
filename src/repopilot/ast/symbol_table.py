"""Symbol table extraction engine leveraging Tree-sitter concrete syntax trees."""

from __future__ import annotations

from pathlib import Path

from tree_sitter import Node

from repopilot.ast.models import (
    ASTParseResult,
    CallSite,
    ParameterInfo,
    Position,
    Range,
    SymbolInfo,
    SymbolType,
)
from repopilot.ast.parser import TreeSitterParser
from repopilot.core.exceptions import ASTParseError
from repopilot.core.result import Err, Ok, Result


class SymbolTableBuilder:
    """Extracts symbol catalogs and call sites from parsed syntax trees."""

    def __init__(self, parser: TreeSitterParser | None = None) -> None:
        self.parser = parser or TreeSitterParser(language_name="python")

    def build_from_file(
        self, file_path: Path | str, module_name: str | None = None
    ) -> Result[ASTParseResult, ASTParseError]:
        """Read, parse, and catalog symbols from a file on disk."""
        path = Path(file_path)
        if not path.exists():
            return Err(ASTParseError(f"File not found: {path}"))

        try:
            content = path.read_text(encoding="utf-8")
            mod = module_name or path.stem
            return self.build_from_code(content, file_path=str(path), module_name=mod)
        except Exception as exc:
            return Err(ASTParseError(f"Failed to read file {path}", details=str(exc)))

    def build_from_code(
        self, source_code: str, file_path: str = "<memory>", module_name: str = ""
    ) -> Result[ASTParseResult, ASTParseError]:
        """Parse source code in memory and catalog all symbols and call sites."""
        parse_res = self.parser.parse_code(source_code, file_path=file_path)
        if parse_res.is_err:
            return Err(parse_res.unwrap_err())

        tree = parse_res.unwrap()
        code_bytes = source_code.encode("utf-8")
        syntax_valid = not self.parser.has_syntax_errors(tree)
        error_msg: str | None = None
        if not syntax_valid:
            errors = self.parser.find_syntax_errors(tree.root_node, code_bytes)
            error_msg = "; ".join(errors) if errors else "Syntax error detected"

        symbols: list[SymbolInfo] = []
        call_sites: list[CallSite] = []
        imports: list[str] = []

        self._traverse_module(
            root=tree.root_node,
            code_bytes=code_bytes,
            file_path=file_path,
            module_name=module_name,
            symbols=symbols,
            call_sites=call_sites,
            imports=imports,
        )

        return Ok(
            ASTParseResult(
                file_path=file_path,
                symbols=symbols,
                call_sites=call_sites,
                imports=imports,
                syntax_valid=syntax_valid,
                error_message=error_msg,
            )
        )

    def _traverse_module(
        self,
        root: Node,
        code_bytes: bytes,
        file_path: str,
        module_name: str,
        symbols: list[SymbolInfo],
        call_sites: list[CallSite],
        imports: list[str],
    ) -> None:
        """Traverse the top-level module AST statements."""
        for child in root.children:
            if child.type == "import_statement" or child.type == "import_from_statement":
                imports.append(self._get_node_text(child, code_bytes))

            elif child.type == "function_definition":
                self._extract_function(
                    node=child,
                    code_bytes=code_bytes,
                    file_path=file_path,
                    prefix=module_name,
                    parent_symbol=None,
                    decorators=[],
                    symbols=symbols,
                    call_sites=call_sites,
                )

            elif child.type == "class_definition":
                self._extract_class(
                    node=child,
                    code_bytes=code_bytes,
                    file_path=file_path,
                    prefix=module_name,
                    decorators=[],
                    symbols=symbols,
                    call_sites=call_sites,
                )

            elif child.type == "decorated_definition":
                self._extract_decorated(
                    node=child,
                    code_bytes=code_bytes,
                    file_path=file_path,
                    prefix=module_name,
                    parent_symbol=None,
                    symbols=symbols,
                    call_sites=call_sites,
                )

    def _extract_decorated(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        prefix: str,
        parent_symbol: str | None,
        symbols: list[SymbolInfo],
        call_sites: list[CallSite],
    ) -> None:
        """Handle decorated definitions (functions or classes preceded by decorators)."""
        decorators: list[str] = []
        target_node: Node | None = None

        for child in node.children:
            if child.type == "decorator":
                decorators.append(self._get_node_text(child, code_bytes).strip())
            elif child.type in ("function_definition", "class_definition"):
                target_node = child

        if target_node is None:
            return

        if target_node.type == "function_definition":
            self._extract_function(
                node=target_node,
                code_bytes=code_bytes,
                file_path=file_path,
                prefix=prefix,
                parent_symbol=parent_symbol,
                decorators=decorators,
                symbols=symbols,
                call_sites=call_sites,
            )
        elif target_node.type == "class_definition":
            self._extract_class(
                node=target_node,
                code_bytes=code_bytes,
                file_path=file_path,
                prefix=prefix,
                decorators=decorators,
                symbols=symbols,
                call_sites=call_sites,
            )

    def _extract_function(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        prefix: str,
        parent_symbol: str | None,
        decorators: list[str],
        symbols: list[SymbolInfo],
        call_sites: list[CallSite],
    ) -> None:
        """Extract a function or method symbol and inspect its inner call sites."""
        name = ""
        parameters: list[ParameterInfo] = []
        return_type: str | None = None
        is_async = False
        body_node: Node | None = None

        for child in node.children:
            if child.type == "async":
                is_async = True
            elif child.type == "identifier":
                name = self._get_node_text(child, code_bytes)
            elif child.type == "parameters":
                parameters = self._extract_parameters(child, code_bytes)
            elif child.type == "type":
                return_type = self._get_node_text(child, code_bytes)
            elif child.type == "block":
                body_node = child

        if not name:
            return

        qualified_id = f"{prefix}.{name}" if prefix else name
        docstring = self._extract_docstring(body_node, code_bytes)

        if parent_symbol:
            symbol_type = SymbolType.ASYNC_METHOD if is_async else SymbolType.METHOD
        else:
            symbol_type = SymbolType.ASYNC_FUNCTION if is_async else SymbolType.FUNCTION

        symbols.append(
            SymbolInfo(
                id=qualified_id,
                name=name,
                file_path=file_path,
                symbol_type=symbol_type,
                range=self._node_to_range(node),
                byte_range=(node.start_byte, node.end_byte),
                docstring=docstring,
                parent_symbol=parent_symbol,
                parameters=parameters,
                return_type=return_type,
                decorators=decorators,
                is_async=is_async,
            )
        )

        if body_node:
            self._extract_call_sites(
                body_node=body_node,
                caller_symbol_id=qualified_id,
                file_path=file_path,
                code_bytes=code_bytes,
                call_sites=call_sites,
            )

    def _extract_class(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        prefix: str,
        decorators: list[str],
        symbols: list[SymbolInfo],
        call_sites: list[CallSite],
    ) -> None:
        """Extract a class symbol and all of its member methods."""
        class_name = ""
        body_node: Node | None = None

        for child in node.children:
            if child.type == "identifier":
                class_name = self._get_node_text(child, code_bytes)
            elif child.type == "block":
                body_node = child

        if not class_name:
            return

        qualified_class_id = f"{prefix}.{class_name}" if prefix else class_name
        docstring = self._extract_docstring(body_node, code_bytes)

        symbols.append(
            SymbolInfo(
                id=qualified_class_id,
                name=class_name,
                file_path=file_path,
                symbol_type=SymbolType.CLASS,
                range=self._node_to_range(node),
                byte_range=(node.start_byte, node.end_byte),
                docstring=docstring,
                parent_symbol=prefix or None,
                decorators=decorators,
            )
        )

        if body_node:
            for child in body_node.children:
                if child.type == "function_definition":
                    self._extract_function(
                        node=child,
                        code_bytes=code_bytes,
                        file_path=file_path,
                        prefix=qualified_class_id,
                        parent_symbol=qualified_class_id,
                        decorators=[],
                        symbols=symbols,
                        call_sites=call_sites,
                    )
                elif child.type == "decorated_definition":
                    self._extract_decorated(
                        node=child,
                        code_bytes=code_bytes,
                        file_path=file_path,
                        prefix=qualified_class_id,
                        parent_symbol=qualified_class_id,
                        symbols=symbols,
                        call_sites=call_sites,
                    )

    def _extract_parameters(self, params_node: Node, code_bytes: bytes) -> list[ParameterInfo]:
        """Extract parameters and type annotations from parameter list node."""
        params: list[ParameterInfo] = []
        for child in params_node.children:
            if child.type in (
                "identifier",
                "typed_parameter",
                "default_parameter",
                "typed_default_parameter",
            ):
                param_text = self._get_node_text(child, code_bytes)
                name = param_text
                type_ann: str | None = None
                default_val: str | None = None

                if ":" in param_text:
                    parts = param_text.split(":", 1)
                    name = parts[0].strip()
                    rest = parts[1].strip()
                    if "=" in rest:
                        type_ann, default_val = [p.strip() for p in rest.split("=", 1)]
                    else:
                        type_ann = rest
                elif "=" in param_text:
                    name, default_val = [p.strip() for p in param_text.split("=", 1)]

                params.append(
                    ParameterInfo(name=name, type_annotation=type_ann, default_value=default_val)
                )

        return params

    def _extract_docstring(self, body_node: Node | None, code_bytes: bytes) -> str | None:
        """Extract docstring if first statement in block is a string expression."""
        if not body_node or not body_node.children:
            return None

        first_stmt = body_node.children[0]
        if first_stmt.type == "expression_statement":
            for child in first_stmt.children:
                if child.type == "string":
                    text = self._get_node_text(child, code_bytes).strip()
                    for quote in ('"""', "'''", '"', "'"):
                        if text.startswith(quote) and text.endswith(quote):
                            return text[len(quote) : -len(quote)].strip()
                    return text
        return None

    def _extract_call_sites(
        self,
        body_node: Node,
        caller_symbol_id: str,
        file_path: str,
        code_bytes: bytes,
        call_sites: list[CallSite],
    ) -> None:
        """Recursively search for function/method calls inside a function body."""
        for child in body_node.children:
            if child.type == "call":
                callee_name = ""
                if child.children:
                    callee_name = self._get_node_text(child.children[0], code_bytes)

                is_awaited = child.parent is not None and child.parent.type == "await"

                call_sites.append(
                    CallSite(
                        caller_symbol_id=caller_symbol_id,
                        callee_name=callee_name,
                        file_path=file_path,
                        line_number=child.start_point.row + 1,
                        is_awaited=is_awaited,
                    )
                )

            elif child.type == "await":
                # Child of await might be a call
                for grand_child in child.children:
                    if grand_child.type == "call":
                        callee_name = ""
                        if grand_child.children:
                            callee_name = self._get_node_text(grand_child.children[0], code_bytes)
                        call_sites.append(
                            CallSite(
                                caller_symbol_id=caller_symbol_id,
                                callee_name=callee_name,
                                file_path=file_path,
                                line_number=grand_child.start_point.row + 1,
                                is_awaited=True,
                            )
                        )
            else:
                self._extract_call_sites(
                    body_node=child,
                    caller_symbol_id=caller_symbol_id,
                    file_path=file_path,
                    code_bytes=code_bytes,
                    call_sites=call_sites,
                )

    def _get_node_text(self, node: Node, code_bytes: bytes) -> str:
        """Slice and decode UTF-8 bytes for a given AST node."""
        return code_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")

    def _node_to_range(self, node: Node) -> Range:
        """Convert Tree-sitter node bounds to Range span."""
        return Range(
            start=Position(line=node.start_point.row, character=node.start_point.column),
            end=Position(line=node.end_point.row, character=node.end_point.column),
        )
