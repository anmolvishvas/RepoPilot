# Product Requirements Document (PRD)

## RepoPilot: Autonomous Codebase Modernization & Migration Agent

**Author:** Anmol Vishvas (<anmol23vishvas@gmail.com>)  
**Target Repository:** [https://github.com/anmolvishvas/RepoPilot](https://github.com/anmolvishvas/RepoPilot)  
**Status:** Approved / Foundational Architecture  
**Target Release:** v1.0.0-MVP  

---

## 1. Executive Summary & Product Vision

### 1.1 Executive Summary
**RepoPilot** is an enterprise-grade autonomous codebase modernization and refactoring agent engineered to solve complex, multi-file code transformations deterministically. Powered by **FastMCP** (Model Context Protocol), **Tree-sitter Code-Graph RAG**, and **Self-Healing LangGraph State Machines**, RepoPilot transitions legacy repositories through structural upgrades—such as sync-to-async migrations, framework migrations (e.g., Pydantic v1 to v2, FastAPI modernizations), strict type-stub additions, and breaking API deprecation remediations—with mathematical precision and continuous sandboxed test verification.

### 1.2 High-Level Vision
To eliminate manual, error-prone boilerplate migration work in enterprise engineering organizations by providing a reliable, context-aware AI partner that reasons across the complete abstract syntax tree (AST) call graph, synthesizes unified diffs, verifies changes in ephemeral Docker test sandboxes, self-heals regressions, and presents clean, human-verifiable pull requests.

```
+-----------------------------------------------------------------------------------+
|                                    RepoPilot                                      |
|                                                                                   |
|  [Legacy Repo] ---> [Tree-sitter Graph + Hybrid RAG] ---> [LangGraph State Engine]|
|                                                                    |              |
|                                                                    v              |
|  [Verified PR] <--- [Human-in-the-Loop Review] <--- [Docker Sandboxed Test Loop]  |
+-----------------------------------------------------------------------------------+
```

---

## 2. Problem Statement & Market Analysis

### 2.1 The Crisis of Legacy Modernization
Enterprise software systems frequently stagnate because the cost and risk of structural refactoring exceed team capacity:
- **Synchronous-to-Asynchronous Migrations:** Rewriting blocking database and HTTP clients to `asyncio` or `anyio` cascades across hundreds of call sites, requiring exact coroutine lifecycle handling and connection pool tuning.
- **Framework & Major Library Upgrades:** Upgrading foundational libraries (Pydantic v1 to v2, SQLAlchemy 1.4 to 2.0, Python 3.8 to 3.12+ syntax) breaks internal contracts, deprecates helper utilities, and changes serialization mechanics.
- **Strict Typing Ingestion:** Introducing `mypy --strict` to a 500k LOC code base demands global symbol resolution, generic variance validation, and accurate stub generation.

### 2.2 Failure Modes of Existing LLM Solutions
Current developer tools (e.g., Copilot chat, naive RAG assistants, isolated single-file agents) consistently fail on large codebases due to three structural flaws:

| Failure Mode | Root Cause in Existing Tools | RepoPilot Solution |
| :--- | :--- | :--- |
| **Shattered Call-Graph Context** | Fixed-token sliding windows split functions across chunk boundaries and miss caller/callee AST relationships. | **Syntactic AST Chunking & Symbol Graph:** Tree-sitter parses complete semantic nodes (functions, classes, methods) and indexes explicit call-graph edges. |
| **Hallucinated Imports & Broken Contracts** | Models guess module paths and method signatures based on shallow vector similarity of raw text. | **Hybrid Code-RAG + Reranking:** Dense vectors + BM25 sparse lexical search combined via Reciprocal Rank Fusion (RRF) and FlashRank cross-encoder reranking. |
| **Blind Code Generation (No Test Feedback)** | Agents emit code directly to disk without running unit or integration test suites, leaving runtime crashes to human review. | **LangGraph Self-Healing Feedback Loop:** Ephemeral Dockerized Pytest execution captures exact stack traces and feeds them back to a reflection agent for iterative repair. |
| **Host Environment Contamination** | Tools execute untested commands directly on developer host machines, risking file corruption or security breaches. | **Docker Sandbox Isolation:** Strict containerization with read-only root filesystems, resource limits, and network gating. |

---

## 3. Goals & Explicit Non-Goals

### 3.1 Primary Goals
1. **AST-Aware Dependency Indexing:** Build an exact symbol table and directed call graph across multi-language codebases using Tree-sitter parsers.
2. **Standardized Model Context Protocol (FastMCP):** Expose codebase intelligence, AST exploration, file patching, and test execution via the open FastMCP standard.
3. **Deterministic Sandbox Verification:** Execute full test suites within ephemeral, isolated Docker containers to collect real-time failure traces.
4. **Self-Healing Code Synthesis:** Orchestrate a LangGraph cyclic state machine (Plan $\rightarrow$ Patch $\rightarrow$ Test $\rightarrow$ Reflect $\rightarrow$ Patch) to resolve regressions autonomously before requesting human review.
5. **Human-in-the-Loop Verification:** Provide a zero-friction, reactive Vue 3 canvas offering side-by-side unified diffs, symbol blast-radius visualization, and one-click commit/rejection workflows.

### 3.2 Explicit Non-Goals
1. **General Conversational Chatbot:** RepoPilot is an autonomous, mission-driven migration agent, not a generic open-ended conversational bot or code autocomplete tool.
2. **Unsandboxed Host Execution:** RepoPilot will never execute test suites or arbitrary scripts directly on the host operating system.
3. **Autonomous Production Deployments:** RepoPilot generates verified pull requests with full audit trails; it does not deploy code directly to staging or production environments without human sign-off.
4. **Cloud-Locked Proprietary Storage:** No repository source code or AST graphs are retained in proprietary cloud vector stores; local Qdrant/pgvector deployments are supported out of the box.

---

## 4. Target Personas & User Journeys

### 4.1 User Personas

#### Persona 1: Marcus, Principal Software Architect
- **Profile:** Oversees technical strategy across 40 microservices; responsible for deprecation cycles and language runtime upgrades.
- **Pain Point:** Upgrading legacy services from Python 3.8 to 3.12 and migrating `requests` to `httpx` async clients is blocked because each service has subtle downstream dependencies.
- **RepoPilot Use:** Launches RepoPilot with a migration recipe; monitors the LangGraph execution trace; inspects the symbol blast-radius map; signs off on clean, tested PRs.

#### Persona 2: Elena, Tech Lead & Senior Backend Engineer
- **Profile:** Manages a team of 8 engineers delivering features against tight roadmaps.
- **Pain Point:** Sprints are constantly interrupted by flaky type errors and technical debt backlogs.
- **RepoPilot Use:** Runs RepoPilot in CI or CLI to ingest `mypy --strict` typing across individual packages overnight, arriving in the morning to validated diffs that pass all existing test suites.

#### Persona 3: David, Developer Experience (DevEx) Platform Lead
- **Profile:** Builds automated tooling, linters, and CI/CD pipelines for 300+ developers.
- **Pain Point:** Lacks standardized agent tooling and fears unsafe scripts running in developer workspaces.
- **RepoPilot Use:** Deploys RepoPilot’s FastMCP server into corporate developer environments with isolated Docker sandboxes and standardized MCP client interfaces.

---

## 5. MVP Feature Scope & Acceptance Criteria

### 5.1 Requirements Traceability Matrix

| Feature ID | Feature Name | Description | Acceptance Criteria | Priority |
| :--- | :--- | :--- | :--- | :--- |
| **FEAT-001** | Tree-sitter AST Graph Extraction | Multi-language parsing of classes, methods, imports, and calls into a directed symbol dependency graph. | - Extracts 100% of top-level and nested functions/classes.<br>- Maps caller $\rightarrow$ callee edges within repository scope.<br>- Emits structured JSON symbol table with start/end byte offsets. | **P0 (Must Have)** |
| **FEAT-002** | Hybrid Code-RAG Pipeline | Syntactic chunking + Qdrant vector search + Rank-BM25 sparse search + FlashRank reranking. | - Chunks adhere to exact AST node boundaries.<br>- Hybrid search combines scores using Reciprocal Rank Fusion ($k=60$).<br>- FlashRank reranks top 20 candidates down to top 5 in $<150$ms. | **P0 (Must Have)** |
| **FEAT-003** | FastMCP Code Server | Standard Model Context Protocol server exposing safe codebase tools. | - Exposes `search_ast_symbols`, `read_file_range`, `apply_unified_diff`, `run_isolated_tests`.<br>- Compatible with standard MCP clients (Claude Desktop, Antigravity, Cursor). | **P0 (Must Have)** |
| **FEAT-004** | LangGraph Cyclic State Engine | Stateful multi-agent graph coordinating planning, synthesis, sandboxed testing, and reflection. | - Implements immutable state transitions with checkpointing.<br>- Executes max 3 self-healing retry cycles on test failure.<br>- Terminates with verified diff or escalates to human review. | **P0 (Must Have)** |
| **FEAT-005** | Ephemeral Docker Sandbox | Isolated test runner executing unit test suites in disposable containers. | - Mounts code into ephemeral container with read-only root.<br>- Enforces CPU (2.0 cores), Memory (2GB), and Execution Timeout (60s).<br>- Captures structured Pytest JSON and stderr stack traces. | **P0 (Must Have)** |
| **FEAT-006** | Vue 3 Reactive Diff Canvas | Real-time browser UI for monitoring migrations, viewing unified diffs, and approving PRs. | - Streams execution logs and agent state changes via Server-Sent Events (SSE).<br>- Interactive split-screen diff viewer with JetBrains Mono syntax highlighting.<br>- Renders symbol blast-radius graph. | **P1 (High)** |
| **FEAT-007** | Langfuse Observability & Tracing | End-to-end tracing of all LLM calls, token usage, latency, and MCP tool invocations. | - Every agent turn tagged with conversation ID and phase.<br>- Records prompt tokens, completion tokens, and model costs.<br>- Captures tool execution metrics and failure traces. | **P1 (High)** |

---

## 6. Success Metrics & Key Performance Indicators (KPIs)

1. **Migration Success Rate:** $\ge 85\%$ of standard modernization recipes (e.g., sync-to-async, Pydantic v1 to v2) pass full test suites without manual intervention.
2. **Autonomous Self-Healing Efficiency:** When tests fail on initial patch synthesis, the reflection agent successfully repairs the failure within $\le 3$ iterations in $\ge 70\%$ of cases.
3. **Zero Host Contamination:** $0$ container escapes, host file corruptions, or unauthorized network calls during sandbox execution.
4. **Context Retrieval Precision:** Top-5 reranked context chunks contain 100% of required caller/callee definitions needed for multi-file refactoring.
5. **Codebase Test Coverage Retention:** Post-migration test coverage must meet or exceed pre-migration coverage (minimum target: 90%).

---

## 7. Security, Isolation & Safety Guardrails

- **Zero Arbitrary Host Execution:** All test commands (`pytest`, `mypy`, `ruff`) run inside ephemeral Docker containers without host network access (`--network none` by default, configurable for package installation steps).
- **Read-Only Original Workspace:** The user's active codebase is mounted read-only into the agent planner; patches are applied to an isolated staging git worktree.
- **AST Validation Guard:** Proposed diffs are checked for syntax correctness via Tree-sitter before being sent to the test sandbox, preventing syntax error token waste.
- **Secret & PII Redaction:** The Code-RAG indexer scrubs API keys, JWTs, and environment variable values before generating embeddings.
- **Deterministic Checkpoint Rollbacks:** If an agent encounters an unrecoverable state or user cancels the run, the state machine rolls back to the initial clean git commit.
