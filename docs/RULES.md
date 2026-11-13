# Engineering Rulebook & Inviolable Principles

## RepoPilot: Autonomous Codebase Modernization & Migration Agent

**Author:** Anmol Vishvas (<anmol23vishvas@gmail.com>)  
**Target Repository:** [https://github.com/anmolvishvas/RepoPilot](https://github.com/anmolvishvas/RepoPilot)  
**Standard Level:** Senior / Staff Engineer Production Baseline  

---

## 1. Purpose & Scope

This document defines the non-negotiable architectural mandates, coding practices, and safety constraints that govern both human developers and autonomous AI code generation agents contributing to **RepoPilot**. Violations of these rules will result in immediate CI pipeline failure and rejection of pull requests.

---

## 2. Inviolable Architectural Principles

### 2.1 Principle 1: Absolute Sandbox Isolation
> Arbitrary test execution, build scripts, and linting suites **MUST ONLY** run inside ephemeral Docker containers. Execution on the developer or host machine is strictly forbidden.

1. **Host Immutability:** The host operating system running RepoPilot must never execute untrusted project commands (`pytest`, `npm test`, `python script.py`).
2. **Container Ephemerality:** Containers must be instantiated with:
   - Read-only root filesystem (`--read-only`) where possible.
   - Strictly bounded resource quotas (`cpu_quota=200000`, `mem_limit="2g"`).
   - Disabled network access (`--network none`) during test phases, unless a specific package installation step is isolated and whitelisted.
   - Mandatory teardown (`container.remove(force=True)`) inside `try...finally` or async context managers.

### 2.2 Principle 2: Strict Idempotency in Code Patching
> Every synthesized code patch must yield deterministic, reproducible AST transformations. Applying the same migration recipe twice must result in a zero-change no-op.

1. **Unified Diff Verification:** Code modifications must be produced and ingested as standard unified diffs (`diff -u`).
2. **Pre- and Post-Patch AST Validation:** Before a patch is submitted to the verification sandbox, Tree-sitter must parse the modified file. If the file contains syntax errors or unclosed blocks, the patch must be rejected immediately at the agent boundary, saving sandbox compute and LLM tokens.
3. **No Non-Deterministic Edits:** Avoid arbitrary line-number insertions without surrounding context anchors (minimum 3 lines of leading and trailing context).

### 2.3 Principle 3: Pure, Checkpointed State Machines
> All agent state transitions in LangGraph must be immutable, pure, and checkpointed. State must never be mutated in-place.

1. **State Immutability:** Agent state objects must be implemented as Pydantic models or frozen typed dicts. State updates must return new state instances or append-only change deltas.
2. **Deterministic Replayability:** Every state transition must be persistable to an SQLite or PostgreSQL checkpointer, enabling auditability, time-travel debugging, and guaranteed rollback to clean git commits.
3. **Finite State Bounds:** Loops in LangGraph must have hard termination counters (e.g., `max_iterations = 3`). Infinite reflection loops are strictly forbidden.

---

## 3. Technology & Coding Standards

### 3.1 Strict Typing Discipline (`mypy --strict`)
Every single Python file in `src/` and `tests/` must pass `mypy --strict` without exceptions.

1. **Zero `Any` Types:** Explicit `Any` (`typing.Any`) is prohibited unless interfacing with un-typed third-party dynamic C-extensions. If required, it must be accompanied by an inline comment explaining why a generic `TypeVar` or `Protocol` is insufficient.
2. **Mandatory Type Annotations:** All functions, methods, and class attributes must have explicit type annotations for all parameters and return values (e.g., `def parse_file(path: Path) -> Result[ASTGraph, ParseError]:`).
3. **Generics & Variance:** Use `TypeVar`, `ParamSpec`, and `Sequence` / `Mapping` abstract types rather than concrete mutable collections (`list`, `dict`) in public signatures.

### 3.2 Error Handling & Result Monads
> The application must never raise unhandled exceptions or leak raw runtime tracebacks across module boundaries.

1. **Domain Exception Hierarchy:** All exceptions must inherit from a unified base class: `RepoPilotError`.
2. **Result Pattern for Fallible Operations:** Operations that can fail expectedly (AST parsing, network retrieval, container spawning, diff application) should return a typed `Result[T, E]` or `Either` structure rather than throwing exceptions:
   ```python
   from dataclasses import dataclass
   from typing import Generic, TypeVar, Union

   T = TypeVar("T")
   E = TypeVar("E")

   @dataclass(frozen=True)
   class Ok(Generic[T]):
       value: T

   @dataclass(frozen=True)
   class Err(Generic[E]):
       error: E

   Result = Union[Ok[T], Err[E]]
   ```
3. **Exhaustive Pattern Matching:** Consume `Result` types using Python 3.10+ `match...case` blocks to ensure all failure branches are handled explicitly.

### 3.3 Pydantic v2 for All Schemas
1. **Strict Models:** Use `pydantic.BaseModel` configured with `model_config = ConfigDict(strict=True, frozen=True)`.
2. **Structured LLM Outputs:** All prompts requiring model reasoning or structured artifacts (plans, patches, reflections) must define an explicit Pydantic response schema and enforce it using tool calling or json-mode validators.
3. **Field Validation:** Implement `@field_validator` and `@model_validator` to assert domain invariants (e.g., verifying that line numbers are positive and start lines precede end lines).

---

## 4. Structured Concurrency & Async Safety Rules

### 4.1 Modern Async Patterns
1. **Use `asyncio.TaskGroup`:** In Python 3.11+, concurrent tasks must be launched using `async with asyncio.TaskGroup() as tg:`. Do not use `asyncio.gather()` unless individual task failure swallowing is explicitly needed.
2. **Handle `ExceptionGroup`:** Ensure exception handlers are prepared to catch and unpack `ExceptionGroup` or `BaseExceptionGroup`.

### 4.2 Timeouts & Cancellation
1. **Mandatory Timeout Guards:** Every external I/O call (LLM inference, Qdrant vector search, Docker container execution) must be wrapped in `asyncio.timeout()`:
   ```python
   async with asyncio.timeout(timeout_seconds):
       result = await execute_sandbox_run(container_id)
   ```
2. **Clean Cancellation Propagation:** Coroutines must never swallow `asyncio.CancelledError`. When caught for cleanup, it must always be re-raised:
   ```python
   except asyncio.CancelledError:
       await cleanup_resources()
       raise
   ```

---

## 5. Code Style, Formatting & Testing Standards

### 5.1 Linting & Formatting with Ruff
- **Formatter & Linter:** All formatting and linting is enforced via **Ruff**.
- **Line Length:** 100 characters maximum.
- **Rule Sets Enforced:**
  - `E`, `W` (pycodestyle errors and warnings)
  - `F` (Pyflakes)
  - `I` (isort import sorting)
  - `B` (flake8-bugbear)
  - `C4` (flake8-comprehensions)
  - `UP` (pyupgrade modern syntax enforcement)
  - `RUF` (Ruff-specific rules)

### 5.2 Test Coverage & Quality Gates
1. **Minimum Branch Coverage:** CI enforces a minimum of **90% branch coverage** (`pytest --cov=src --cov-fail-under=90`).
2. **Test Pyramid Distribution:**
   - **Unit Tests (70%):** Mock external dependencies; verify Tree-sitter parsing, BM25 indexing, RRF math, diff application, and state reducers.
   - **Integration Tests (20%):** Verify FastMCP tool endpoints, Qdrant vector indexing, and Docker container lifecycle management.
   - **End-to-End Tests (10%):** Complete multi-file modernization runs against real open-source test repos (e.g., migrating a mini sync HTTP client library to async `httpx`).
3. **Deterministic Fixtures:** Test fixtures must use reproducible seed values for embeddings, mock responses, and temp directories.
