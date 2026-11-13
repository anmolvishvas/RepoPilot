# Phased Implementation Plan & Task Backlog

## RepoPilot: Autonomous Codebase Modernization & Migration Agent

**Author:** Anmol Vishvas (<anmol23vishvas@gmail.com>)  
**Target Repository:** [https://github.com/anmolvishvas/RepoPilot](https://github.com/anmolvishvas/RepoPilot)  
**Tracking Mode:** Production Engineering Implementation Matrix  

---

## Phase 1: Repository Scaffolding, Strict Tooling, and Domain Schemas

- [x] **TASK-101: Project Packaging & Dependency Configuration**
  - **Description:** Setup modern Python packaging via `pyproject.toml` (Poetry or Hatchling) configuring Python $\ge 3.11$, strict typing dependencies, and CLI entry points.
  - **Acceptance Criteria:** `poetry install` or `pip install -e .` completes cleanly with locked dependencies in isolated virtual environment.

- [x] **TASK-102: Linter, Formatter & Type-Checking Scaffolding**
  - **Description:** Configure `ruff.toml` and `mypy.ini` enforcing line length 100, strict type-checking (`disallow_untyped_defs = true`, `disallow_any_generics = true`), and pre-commit hooks.
  - **Acceptance Criteria:** `ruff check .`, `ruff format --check .`, and `mypy --strict src/` return zero warnings or errors.

- [x] **TASK-103: Domain Schemas & Result Monads**
  - **Description:** Implement immutable Pydantic v2 domain schemas (`src/repopilot/ast/models.py`, `src/repopilot/agents/state.py`) and generic `Result[T, E]` monad (`src/repopilot/core/result.py`).
  - **Acceptance Criteria:** Unit tests demonstrate serialization/deserialization and pattern matching over `Ok` and `Err` branches.

---

## Phase 2: Tree-sitter AST Parser & Symbol Dependency Graph Builder

- [x] **TASK-201: Tree-sitter Multi-Language Grammar Bindings**
  - **Description:** Implement `TreeSitterParser` (`src/repopilot/ast/parser.py`) binding official Tree-sitter grammars for Python (with TS/Go extensible hooks).
  - **Acceptance Criteria:** Successfully parses syntax trees, extracts byte offsets, and identifies syntax errors on malformed source files.

- [x] **TASK-202: Symbol Table Extraction Engine**
  - **Description:** Implement `SymbolTableBuilder` (`src/repopilot/ast/symbol_table.py`) traversing ASTs to catalog all classes, functions, methods, imports, and variables with fully qualified names.
  - **Acceptance Criteria:** 100% extraction of top-level and nested callable symbols across a 50-file sample repository.

- [x] **TASK-203: Directed Call-Graph & Blast-Radius Engine**
  - **Description:** Implement `CallGraphBuilder` (`src/repopilot/ast/call_graph.py`) mapping caller-to-callee dependencies using NetworkX or custom adjacency matrices.
  - **Acceptance Criteria:** Traverses reverse dependency edges to compute the exact list of downstream affected files when a target symbol signature changes.

---

## Phase 3: Hybrid Code-RAG Engine (Qdrant + BM25 + FlashRank)

- [ ] **TASK-301: AST Syntactic Chunker**
  - **Description:** Implement `ASTChunker` (`src/repopilot/rag/chunker.py`) that chunks code along exact function and class boundaries rather than arbitrary token counts.
  - **Acceptance Criteria:** Zero chunks split mid-statement; every chunk retains parent class, signature header, and module path metadata.

- [ ] **TASK-302: Dense Vector Store & FastEmbed Integration**
  - **Description:** Implement `QdrantVectorStore` (`src/repopilot/rag/vector_store.py`) integrating `FastEmbed` for local embedding generation (`bge-small-en-v1.5`).
  - **Acceptance Criteria:** Dense search returns top-K semantically relevant functions with sub-30ms latency on CPU.

- [ ] **TASK-303: Rank-BM25 Sparse Lexical Indexer**
  - **Description:** Implement `BM25CodeIndex` (`src/repopilot/rag/bm25_index.py`) tokenizing code identifiers, variable names, and error strings.
  - **Acceptance Criteria:** Exact symbol searches (e.g., `test_connection_pool_overflow`) achieve 100% recall in the top-3 results.

- [ ] **TASK-304: Reciprocal Rank Fusion & FlashRank Reranker**
  - **Description:** Implement RRF merger ($k=60$) and `FlashRankReranker` (`src/repopilot/rag/reranker.py`) running local cross-encoders.
  - **Acceptance Criteria:** RRF merges dense and sparse results; FlashRank reranks 25 candidates down to top 5 in $<150$ms without GPU dependencies.

---

## Phase 4: FastMCP Code Server & Dockerized Pytest Sandbox

- [ ] **TASK-401: FastMCP Protocol Server Setup**
  - **Description:** Implement `FastMCPServer` (`src/repopilot/mcp/server.py`) using the official Python FastMCP SDK with STDIO and SSE transport support.
  - **Acceptance Criteria:** Exposes valid JSON-RPC 2.0 endpoints compliant with MCP specification and connectable from Claude Desktop / Cursor.

- [ ] **TASK-402: Safe Local Tool Registry**
  - **Description:** Implement `search_ast_symbols`, `read_file_range`, and `apply_unified_diff` with path canonicalization and directory traversal guards.
  - **Acceptance Criteria:** Invocations outside target repository root are rejected with typed security errors.

- [ ] **TASK-403: Ephemeral Docker Test Sandbox**
  - **Description:** Implement `DockerSandboxRunner` (`src/repopilot/sandbox/runner.py`) using `docker-py` to spin up isolated containers with CPU/memory limits and timeout guards.
  - **Acceptance Criteria:** Executes Pytest suite inside ephemeral container; captures stdout, stderr, and exit codes; guarantees container destruction on exit.

- [ ] **TASK-404: Pytest & JUnit XML Error Parser**
  - **Description:** Implement `PytestErrorParser` (`src/repopilot/sandbox/pytest_parser.py`) extracting failing test names, assertion messages, and traceback line numbers.
  - **Acceptance Criteria:** Emits structured Pydantic failure models ready for consumption by reflection agents.

---

## Phase 5: LangGraph Multi-Agent State Engine & Self-Correction Feedback Loop

- [ ] **TASK-501: LangGraph State Machine Architecture**
  - **Description:** Define `MigrationState` and construct the cyclic `StateGraph` (`src/repopilot/agents/graph.py`) linking Planner, Synthesizer, and Critic nodes.
  - **Acceptance Criteria:** State transitions are immutable and recorded in SQLite checkpointer with full time-travel capability.

- [ ] **TASK-502: Planner & Supervisor Agent Node**
  - **Description:** Implement `PlannerNode` (`src/repopilot/agents/planner.py`) decomposing migration recipes into an ordered sequence of file modifications.
  - **Acceptance Criteria:** Generates a topological execution plan respecting the AST call graph dependencies.

- [ ] **TASK-503: Code Synthesizer Agent Node**
  - **Description:** Implement `SynthesizerNode` (`src/repopilot/agents/synthesizer.py`) generating standard unified diffs informed by AST context and caller contracts.
  - **Acceptance Criteria:** Synthesizes syntactically valid unified diffs that cleanly apply to the staging git worktree.

- [ ] **TASK-504: Test Critic & Self-Healing Reflection Node**
  - **Description:** Implement `CriticNode` (`src/repopilot/agents/critic.py`) analyzing Pytest stack traces to formulate targeted repair prompts.
  - **Acceptance Criteria:** Triggers a maximum of 3 self-healing retry iterations when tests fail; resolves common syntax and missing-await regressions autonomously.

---

## Phase 6: FastAPI SSE Gateway & Vue 3 Real-time Canvas

- [ ] **TASK-601: FastAPI Server-Sent Events (SSE) Gateway**
  - **Description:** Implement asynchronous streaming routes (`src/repopilot/server/routes_stream.py`) broadcasting agent thought streams and tool events.
  - **Acceptance Criteria:** Clients receive real-time JSON event packets with $<50$ms server dispatch latency.

- [ ] **TASK-602: Vue 3 / Nuxt 3 Cockpit Scaffolding**
  - **Description:** Initialize Nuxt 3 project in `ui/` with Tailwind CSS, dark-mode tokens, and Pinia state management.
  - **Acceptance Criteria:** Clean build with responsive 3-column cockpit layout.

- [ ] **TASK-603: Real-Time Execution Trace & Terminal Component**
  - **Description:** Implement `ExecutionTrace.vue` streaming SSE events with state badges, tool call accordions, and ANSI log rendering.
  - **Acceptance Criteria:** Auto-scrolls and color-codes test passes/failures in real time.

- [ ] **TASK-604: Interactive Split-Screen Unified Diff Viewer**
  - **Description:** Implement `UnifiedDiffViewer.vue` rendering side-by-side syntax-highlighted diffs with inline AST explanation breadcrumbs.
  - **Acceptance Criteria:** Renders multi-file diffs with line-level addition/deletion highlighting and operator approval buttons.

- [ ] **TASK-605: AST Dependency Mini-Map**
  - **Description:** Implement `DependencyMiniMap.vue` rendering interactive D3.js or SVG node-link diagrams of affected symbols.
  - **Acceptance Criteria:** Clicking an AST node centers the diff viewer directly on that file's changes.

---

## Phase 7: Benchmark Evaluations, Chaos Testing, and CI/CD Automation

- [ ] **TASK-701: Modernization Benchmark Suite**
  - **Description:** Construct 10 benchmark test repositories covering sync-to-async, Pydantic v1 to v2, and Python typing additions.
  - **Acceptance Criteria:** RepoPilot achieves $\ge 85\%$ autonomous test pass rate across benchmark repos.

- [ ] **TASK-702: Sandbox Chaos & Security Hardening**
  - **Description:** Subject the Docker sandbox to fork-bombs, memory exhaustion, network breakout attempts, and infinite loops.
  - **Acceptance Criteria:** 100% of adversarial test runs are terminated cleanly by timeout/memory guards with zero host escape.

- [ ] **TASK-703: GitHub Actions PR Workflows**
  - **Description:** Implement `.github/workflows/ci.yml` and `pr-audit.yml` validating Ruff formatting, Mypy strict typing, 90% branch coverage, and PR title conventions.
  - **Acceptance Criteria:** CI matrix runs on Python 3.11, 3.12, 3.13 and blocks non-compliant PRs.
