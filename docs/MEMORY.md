# Project Memory, ADRs & Living State Journal

## RepoPilot: Autonomous Codebase Modernization & Migration Agent

**Author:** Anmol Vishvas (<anmol23vishvas@gmail.com>)  
**Target Repository:** [https://github.com/anmolvishvas/RepoPilot](https://github.com/anmolvishvas/RepoPilot)  
**Last Updated:** 2026-11-13  
**Current Phase:** Phase 1 (Scaffolding & Baseline Architecture)  

---

## 1. Project Status Summary

RepoPilot has established its foundational architecture, product requirements, engineering rulebook, and UI/UX design specifications. The project is positioned to solve enterprise-scale codebase modernization through deterministic abstract syntax tree (AST) reasoning, hybrid code retrieval, isolated sandbox test feedback, and self-healing LangGraph state machines.

### 1.1 Phase Progress Dashboard
- [x] **Phase 0:** Architectural Design & Core Documentation (PRD, Architecture, Rules, Design, Tasks, Memory)
- [x] **Phase 1:** Repository Scaffolding, Strict Tooling, and Domain Schemas (Completed)
- [x] **Phase 2:** Tree-sitter AST Parser & Symbol Dependency Graph Builder (Completed)
- [x] **Phase 3:** Hybrid Code-RAG Engine (Qdrant + BM25 + FlashRank) (Completed)
- [ ] **Phase 4:** FastMCP Code Server & Dockerized Pytest Sandbox (Next Up)
- [ ] **Phase 3:** Hybrid Code-RAG Engine (Qdrant + BM25 + FlashRank)
- [ ] **Phase 4:** FastMCP Code Server & Dockerized Pytest Sandbox
- [ ] **Phase 5:** LangGraph Multi-Agent State Engine & Self-Correction Feedback Loop
- [ ] **Phase 6:** FastAPI SSE Gateway & Vue 3 Real-time Canvas
- [ ] **Phase 7:** Benchmark Evaluations, Chaos Testing, and CI/CD Automation

---

## 2. Architectural Decision Records (ADRs)

### ADR-001: LangGraph over CrewAI/AutoGen for Stateful Cycle Determinism
- **Status:** Accepted
- **Context:** Enterprise codebase refactoring requires strict cyclical control loops (Plan $\rightarrow$ Patch $\rightarrow$ Test $\rightarrow$ Reflect $\rightarrow$ Patch) with deterministic stopping criteria, rollback mechanics, and immutable state persistence. Frameworks like CrewAI and AutoGen favor open-ended multi-agent conversation patterns that lack rigid state transition semantics, making deterministic replay and branch checkpointing difficult to enforce.
- **Decision:** Adopt **LangGraph** as the state machine orchestration engine for RepoPilot.
- **Consequences:**
  - *Positive:* Enables explicit cyclic graph topologies, typed state transitions via Pydantic, time-travel debugging, and SQLite/PostgreSQL checkpoint persistence.
  - *Positive:* Simplifies human-in-the-loop review nodes where execution pauses until explicit user approval.
  - *Trade-off:* Requires explicit state schema definition for all agent transitions, increasing initial design rigor.

---

### ADR-002: FastMCP as the Standard Tool Protocol Instead of Proprietary Function Calling
- **Status:** Accepted
- **Context:** To ensure RepoPilot can be invoked from modern AI IDEs (Cursor, Claude Desktop, Antigravity) and custom CLI runners without vendor lock-in, tools must not be hardcoded to proprietary OpenAI or Anthropic tool-calling schemas.
- **Decision:** Implement tool interfaces using the **FastMCP Python SDK** adhering to the open Model Context Protocol specification.
- **Consequences:**
  - *Positive:* Any MCP-compliant client can immediately discover and run RepoPilot tools (`search_ast_symbols`, `read_file_range`, `apply_unified_diff`, `run_isolated_tests`).
  - *Positive:* Decouples tool implementation from model providers, allowing seamless model swapping (Claude 3.7 Sonnet, GPT-4o, Gemini 2.5/3.8 Pro).
  - *Trade-off:* Client connections require STDIO or SSE protocol handling rather than direct Python method calls.

---

### ADR-003: Tree-sitter AST Syntactic Chunking over Naive Fixed-Token Sliding Windows
- **Status:** Accepted
- **Context:** Standard RAG pipelines use fixed token chunking (e.g., 512 tokens with 50-token overlap). On source code, this routinely splits function signatures from their implementations, severs class docstrings, and breaks caller/callee context, causing models to hallucinate invalid method signatures and missing parameters.
- **Decision:** Implement syntactic chunking using **Tree-sitter** concrete and abstract syntax trees. Chunks are strictly anchored to functional nodes (functions, classes, methods) and enriched with parent class names, module paths, and parameter lists.
- **Consequences:**
  - *Positive:* Eliminates fractured code blocks; vector embeddings represent cohesive semantic units.
  - *Positive:* Enables precise symbol table lookups and directed call-graph extraction.
  - *Trade-off:* Requires native Tree-sitter language grammar compilation for each supported programming language.

---

### ADR-004: Ephemeral Docker Containerization for Untrusted Test Execution
- **Status:** Accepted
- **Context:** Modernization agents synthesize arbitrary code modifications that must be validated by running test suites (`pytest`). Running unverified, agent-generated code directly on the host machine presents severe security vulnerabilities (accidental file deletion, network data exfiltration, fork bombs, and environment variable contamination).
- **Decision:** Execute all test commands inside ephemeral Docker containers created via `docker-py`, configured with read-only root filesystems, resource limits, and disabled network access.
- **Consequences:**
  - *Positive:* Total host isolation; zero risk of system damage or credential theft from untrusted code.
  - *Positive:* Reproducible runtime environments matching target deployment containers.
  - *Trade-off:* Requires Docker daemon availability on the host and introduces ~1-2 seconds of container startup overhead per verification cycle.

---

## 3. Immediate Next Actions

1. **Initialize Project Scaffolding:** Create `pyproject.toml`, `ruff.toml`, and `mypy.ini` in the repository root.
2. **Implement Core Result & AST Domain Schemas:** Author `Result[T, E]`, `SymbolInfo`, `CallGraphNode`, and `CallGraphEdge` Pydantic models.
3. **Build Tree-sitter Parser Engine:** Implement initial Python grammar parser in `src/repopilot/ast/parser.py`.
4. **Setup Docker Test Container:** Author `Dockerfile.sandbox` with pre-installed test runner dependencies for isolated test execution.

---

## 4. Technical Debt & Risk Register

| Risk / Debt ID | Description | Impact | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **RISK-01** | High latency during cold Docker container startup. | Test verification loop latency increases by 2-4s. | Maintain a pre-warmed container pool or reuse persistent containers across iterative self-healing cycles for a single run. |
| **RISK-02** | Massive repositories ($>1$M LOC) causing memory bloat during full AST indexing. | Potential OOM during initial symbol graph generation. | Stream Tree-sitter parsing with incremental indexing; persist graph to disk-backed SQLite or NetworkX file stores rather than holding purely in RAM. |
| **RISK-03** | Complex git merge conflicts during multi-file patch application. | Patch application failures in `apply_unified_diff`. | Isolate changes in temporary git worktrees; validate diff cleanly applies using `git apply --check` before executing disk writes. |
