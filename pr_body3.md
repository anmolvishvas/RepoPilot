## 🎯 Architectural Motivation & Summary

Implements **Phase 2: Tree-sitter AST Parser & Symbol Dependency Graph Builder** (TASK-201, TASK-202, TASK-203), giving RepoPilot complete syntactic and call-graph awareness across codebases.

Key additions:
- **Tree-sitter Parser Engine (`src/repopilot/ast/parser.py`)**:
  - `TreeSitterParser`: Multi-language syntax parsing engine wrapping official Tree-sitter grammars (`tree-sitter-python`).
  - Error detection: recursive syntax error extraction identifying line/column and unexpected syntax snippets.
  - Safe file reading and in-memory code parsing returning `Result[Tree, ASTParseError]`.
- **Symbol Table Extraction Engine (`src/repopilot/ast/symbol_table.py`)**:
  - `SymbolTableBuilder`: Extracts all top-level and nested functions, async functions, classes, and member methods.
  - Parses parameters, type annotations, default values, docstrings, decorators, and return types.
  - Recursively discovers caller-to-callee `CallSite` invocations, detecting `await` expressions (`is_awaited`).
  - Handles module-level imports (`import_statement`, `import_from_statement`).
- **Directed Call-Graph & Blast-Radius Engine (`src/repopilot/ast/call_graph.py`)**:
  - `CallGraphBuilder`: Multi-file dependency graph powered by NetworkX.
  - Computes direct callees and callers.
  - Computes transitive **blast radius** (`get_blast_radius(symbol_id)`), tracing all downstream impacted callers across files when a symbol signature changes.
  - Calculates topological bottom-up migration ordering (`get_topological_migration_order()`).
- **Comprehensive Unit Tests**:
  - `test_ast_parser.py`: Tests valid/malformed code, file reading, and syntax error tracking.
  - `test_symbol_table.py`: Tests function, class, decorator, docstring, and call site extraction.
  - `test_call_graph.py`: Tests multi-file cross-boundary resolution, blast-radius calculation, cycle handling, and topological migration order.
  - **31/31 unit tests passing**, **93.64% test coverage**, and strict `mypy` and `ruff` verification.

---

## 🧩 Subsystems Affected

- [x] **AST & Code Intelligence** (`src/repopilot/ast/`)
- [x] **Tooling & Configs** (`mypy.ini`)
- [x] **Documentation** (`docs/`)

---

## 🏷️ Type of Change

- [x] `feat`: New feature or capability
- [x] `test`: Unit, integration, or e2e test suite additions
- [x] `docs`: Documentation addition or update

---

## ⚠️ Breaking Change Notice

- [ ] **Yes**
- [x] **No**

---

## 🧪 Verification & Quality Checklist

- [x] **Sandbox Isolation:** No untrusted test executions run on host.
- [x] **Strict Typing:** `mypy --strict src/ tests/` passes cleanly across 24 source files.
- [x] **Code Formatting & Linting:** `ruff check .` and `ruff format --check .` are 100% clean.
- [x] **Test Coverage:** 31 tests pass with 93.64% coverage ($\ge 90\%$ enforced).
