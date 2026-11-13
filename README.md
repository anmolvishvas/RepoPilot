# RepoPilot 🚀

> **Autonomous Codebase Modernization & Migration Agent powered by FastMCP, Tree-sitter Code-Graph RAG, and Self-Healing LangGraph State Machines.**

[![CI Pipeline](https://github.com/anmolvishvas/RepoPilot/actions/workflows/ci.yml/badge.svg)](https://github.com/anmolvishvas/RepoPilot/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Coverage](https://img.shields.io/badge/coverage-90%25%2B-brightgreen.svg)](https://github.com/anmolvishvas/RepoPilot)
[![Type Checking: Mypy Strict](https://img.shields.io/badge/mypy-strict-blueviolet.svg)](https://mypy.readthedocs.io/)
[![Linter: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![MCP Compliant](https://img.shields.io/badge/MCP-FastMCP%20v1.0-orange.svg)](https://github.com/jlowin/fastmcp)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

---

## 💡 Overview

Modernizing enterprise codebases—such as **sync-to-async migrations**, **framework upgrades (e.g., Pydantic v1 to v2)**, **type-stub additions**, and **breaking API deprecations**—is high-risk, labor-intensive, and context-blind. Existing LLM coding tools operate over shallow, single-file contexts or naive text chunking that shatters caller/callee AST relationships, hallucinates invalid imports, and lacks an automated, sandboxed test execution loop to detect regressions and self-heal before landing code.

**RepoPilot** solves this by establishing a deterministic, cybernetic engineering loop:
1. **Parses** the entire repository using **Tree-sitter** to extract an unambiguous AST symbol table and directed call-graph.
2. **Retrieves** context with **Hybrid Code-RAG** combining Qdrant dense vector embeddings, Rank-BM25 sparse lexical search, and FlashRank cross-encoder reranking.
3. **Exposes** codebase capabilities through a standardized **FastMCP** server.
4. **Executes** multi-agent migration workflows in **LangGraph**, generating unified diffs, running test suites in **ephemeral Docker sandboxes**, and **self-healing** runtime regressions iteratively.
5. **Surfaces** changes on an interactive **Vue 3 / Nuxt 3 Reactive Canvas** for human-in-the-loop review and approval.

---

## 🏛️ System Architecture

```
                       +-------------------------------------------------------------+
                       |              RepoPilot Reactive Canvas (Vue 3)              |
                       +------------------------------+------------------------------+
                                                      | SSE / HTTP REST
                                                      v
+----------------------------------------------------------------------------------------------------+
|                                    FastAPI & FastMCP Gateway                                       |
+---------------------------------------------+------------------------------------------------------+
                                              |
                                              v
+----------------------------------------------------------------------------------------------------+
|                               LangGraph Multi-Agent State Machine                                  |
|                                                                                                    |
|    +-------------------+       +--------------------+       +---------------------------------+    |
|    |  Planner Agent    | ----> |  Synthesizer Agent | ----> | Dockerized Test Sandbox Critic  |    |
|    |  (AST Dependency) |       |  (Unified Diff)    |       | (Pytest / JUnit Capture)        |    |
|    +-------------------+       +--------------------+       +----------------+----------------+    |
|              ^                           ^                                   |                     |
|              |                           |           Self-Healing Loop       |                     |
|              |                           +-----------------------------------+ (Tests Failed)      |
|              |                                                               |                     |
|              |                   +-------------------------------------------+ (Tests Passed)      |
|              |                   v                                                                 |
|              |         +-----------------------+                                                   |
|              +-------- | Human Review & Commit |                                                   |
|                        +-----------------------+                                                   |
+----------------------------------------------------------------------------------------------------+
       |                                                                       |
       v                                                                       v
+---------------------------------------------------+       +----------------------------------------+
|          Code Intelligence & Hybrid RAG           |       |      Docker Sandbox Environment        |
|  - Tree-sitter AST & Call-Graph Builder           |       |  - Ephemeral Test Runner Containers    |
|  - Qdrant Vector Store + FastEmbed                |       |  - Read-Only Root & Zero Network       |
|  - Rank-BM25 Index + FlashRank Reranker           |       |  - Automated Stacktrace Parser         |
+---------------------------------------------------+       +----------------------------------------+
```

---

## 📚 Engineering Documentation

The complete architectural specifications, design documents, and operational rulebooks are maintained in [`docs/`](docs/):

| Document | Purpose |
| :--- | :--- |
| 📄 [**Product Requirements Document (PRD.md)**](docs/PRD.md) | High-level vision, problem statement, personas, and feature acceptance criteria. |
| 🏛️ [**System Architecture (ARCHITECTURE.md)**](docs/ARCHITECTURE.md) | Subsystem deep-dives, Mermaid diagrams, technology rationale, and directory structure. |
| 📏 [**Engineering Rulebook (RULES.md)**](docs/RULES.md) | Inviolable principles: sandbox isolation, idempotency, strict typing, and concurrency rules. |
| 🎨 [**UI/UX Design Specification (DESIGN.md)**](docs/DESIGN.md) | Vue 3 Canvas design tokens, color palette, typography, and component anatomy. |
| 📋 [**Implementation Tasks (TASKS.md)**](docs/TASKS.md) | Granular 7-phase implementation backlog with concrete acceptance criteria. |
| 🧠 [**Project Memory & ADRs (MEMORY.md)**](docs/MEMORY.md) | Living project tracker, Architectural Decision Records (ADRs), and risk register. |

---

## ✨ Key Capabilities

- **Tree-sitter AST Symbol & Call-Graph Resolution:** Extracts 100% of callable symbols, imports, and cross-file references. Computes exact blast-radius matrices before touching a single line of code.
- **Syntactic Hybrid Code-RAG:** Chunks code strictly at AST node boundaries (functions, classes). Melds dense vector search with Rank-BM25 sparse search via Reciprocal Rank Fusion ($k=60$) and reranks with CPU-optimized FlashRank ($<150$ms).
- **Standardized FastMCP Code Server:** Exposes safe, validated tools (`search_ast_symbols`, `read_file_range`, `apply_unified_diff`, `run_isolated_tests`) to any MCP client (Claude Desktop, Cursor, Antigravity).
- **Self-Healing LangGraph Feedback Loop:** Synthesizes code, validates syntax with Tree-sitter, applies diffs to a staging git worktree, and runs tests in disposable Docker containers. If tests fail, the Critic agent parses the traceback and automatically coordinates repairs.
- **Real-Time Vue 3 / Nuxt 3 Cockpit:** Streams execution traces via Server-Sent Events (SSE), provides side-by-side syntax-highlighted diffs with Monaco, and renders interactive D3 dependency mini-maps.

---

## ⚡ Quickstart Guide

### Prerequisites
- **Python 3.11+**
- **Docker Engine** (running locally for test sandboxing)
- **Node.js 18+** (for the Nuxt 3 UI dashboard)
- **uv** or **Poetry** (recommended Python package manager)

### 1. Clone & Install Dependencies
```bash
# Clone the repository
git clone https://github.com/anmolvishvas/RepoPilot.git
cd RepoPilot

# Install Python dependencies using uv (or poetry install)
uv pip install -e ".[dev]"

# Verify strict type-checking and linting
ruff check .
mypy --strict src/
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your LLM API Keys (OpenAI, Anthropic, or Gemini)
# export OPENAI_API_KEY="your-key"
# export LANGFUSE_PUBLIC_KEY="your-key" (optional)
```

### 3. Build Sandbox Docker Image
```bash
docker build -f Dockerfile.sandbox -t repopilot-sandbox:latest .
```

### 4. Launch the FastMCP Server
```bash
# Run FastMCP code server over STDIO
python -m repopilot.mcp.server
```

### 5. Run an Autonomous Migration
```bash
# Execute an autonomous sync-to-async migration on a target repo
repopilot migrate \
  --repo-path /path/to/legacy-repo \
  --recipe sync-to-async \
  --test-cmd "pytest tests/" \
  --max-retries 3
```

### 6. Launch the Real-Time Web Canvas
```bash
# In a separate terminal, launch the FastAPI SSE gateway & Nuxt frontend
repopilot server --port 8000 &
cd ui && npm install && npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser to inspect real-time agent execution traces, interactive unified diffs, and the dependency blast-radius mini-map.

---

## 👤 Author & Maintainer

**Anmol Vishvas**  
- **Email:** [anmol23vishvas@gmail.com](mailto:anmol23vishvas@gmail.com)  
- **GitHub:** [@anmolvishvas](https://github.com/anmolvishvas)  
- **Project Repository:** [https://github.com/anmolvishvas/RepoPilot](https://github.com/anmolvishvas/RepoPilot)

---

## 📄 License

This project is licensed under the Apache 2.0 License. See the [LICENSE](LICENSE) file for details.
