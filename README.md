# RepoPilot 🚀

> **Autonomous Codebase Modernization & Migration Agent powered by FastMCP, Tree-sitter Code-Graph RAG, and Self-Healing LangGraph State Machines.**

[![CI Pipeline](https://github.com/anmolvishvas/RepoPilot/actions/workflows/ci.yml/badge.svg)](https://github.com/anmolvishvas/RepoPilot/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Coverage](https://img.shields.io/badge/coverage-92%25%2B-brightgreen.svg)](https://github.com/anmolvishvas/RepoPilot)
[![Type Checking: Mypy Strict](https://img.shields.io/badge/mypy-strict-blueviolet.svg)](https://mypy.readthedocs.io/)
[![Linter: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Security: Bandit](https://img.shields.io/badge/security-bandit%20clean-brightgreen.svg)](https://github.com/PyCQA/bandit)
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
5. **Surfaces** changes on an interactive **Vue 3 Reactive Canvas** for human-in-the-loop review and approval.

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
- **Self-Healing LangGraph Feedback Loop:** Synthesizes code, validates syntax with Tree-sitter, applies diffs to a staging worktree, and runs tests in disposable Docker containers. If tests fail, the Critic agent parses the traceback and automatically coordinates repairs.
- **Real-Time Vue 3 Cockpit Canvas:** Streams execution traces via Server-Sent Events (SSE), provides side-by-side syntax-highlighted diffs, and renders interactive SVG dependency blast-radius mini-maps.

---

## ⚡ Quickstart Guide

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** & `npm`
- **Docker Engine** *(Optional — RepoPilot automatically falls back to secure subprocess test execution if Docker is inactive)*

### 1. Clone & Set Up Environment

```bash
git clone https://github.com/anmolvishvas/RepoPilot.git
cd RepoPilot

# Create and activate virtual environment
python -m venv .venv

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Upgrade pip and install RepoPilot in editable mode
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### 2. Verify Code Quality & Tests

```bash
# Run all 103 unit, benchmark, and sandbox chaos tests with >= 90% coverage
pytest -v --cov=src --cov-fail-under=90

# Verify strict type-checking and linting
ruff check .
ruff format --check .
mypy --strict src/ tests/
bandit -r src/
```

---

## 🚀 How to Use RepoPilot on Real Projects

RepoPilot can modernize **any real Python repository** on your computer. Follow these steps:

### Method 1: Using the REST API & Real-Time Cockpit

#### Step 1: Start the RepoPilot API Gateway
```bash
repopilot server --port 8080
```
> [!TIP]
> RepoPilot runs on port `8080` (or `8000`). Interactive Swagger documentation is instantly available at **http://127.0.0.1:8080/docs**.

#### Step 2: Start the Vue 3 Cockpit UI
In a second terminal window:
```bash
cd ui
npm install
npm run dev
```
Open **http://localhost:5173** (or `:3000`) in your browser to access the dark-mode cockpit.

#### Step 3: Trigger a Migration on Your App
Open **http://127.0.0.1:8080/docs** in your browser, expand **`POST /api/v1/migrations`**, click **Try it out**, and provide your target repository path:

```json
{
  "repo_path": "C:/path/to/your/legacy-app",
  "recipe": "sync-to-async",
  "max_retries": 3
}
```

Or trigger it directly from your terminal using cURL or PowerShell:

```powershell
$body = @{
    repo_path = "C:/path/to/your/legacy-app"
    recipe = "sync-to-async"
    max_retries = 3
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8080/api/v1/migrations" -Method Post -Body $body -ContentType "application/json"
```

#### Step 4: Watch the Autonomous Loop
In the background, RepoPilot will:
1. **Index AST Call-Graph:** Discovers symbol dependencies and computes the blast radius.
2. **Synthesize Patches:** Generates unified diffs according to topological migration order.
3. **Execute Isolated Tests:** Runs `pytest` inside an ephemeral container or secure subprocess.
4. **Self-Heal Regressions:** If any test fails, the Critic agent diagnoses the root cause (e.g., missing `await` or broken import), re-prompts the Synthesizer, and verifies the repair.
5. **Halt at Human Review:** Pauses execution at a safe breakpoint awaiting your confirmation.

#### Step 5: Approve & Land Patches
Review the generated diffs in the cockpit UI or Swagger UI. Once satisfied, send approval to land the changes to disk:

```powershell
$approval = @{
    approved = $true
    operator = "Lead Engineer"
    comment = "Verified async conversion passes all tests."
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8080/api/v1/migrations/<YOUR_TASK_ID>/approval" -Method Post -Body $approval -ContentType "application/json"
```

---

### Method 2: Using Inside Cursor or Claude Desktop (FastMCP)

RepoPilot implements the open **Model Context Protocol (MCP)**, allowing AI assistants like Cursor, Claude Desktop, and Antigravity to use RepoPilot's AST analysis and sandboxed test execution directly inside your editor.

#### Step 1: Start the MCP Server
```bash
repopilot mcp
```

#### Step 2: Configure Claude Desktop / Cursor
Add RepoPilot to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "repopilot": {
      "command": "python",
      "args": ["-m", "repopilot.mcp.server"],
      "cwd": "C:/Users/DELL/Desktop/RepoPilot"
    }
  }
}
```

Now inside Cursor or Claude Desktop, you can prompt:
> *"Inspect the AST call graph of my app using RepoPilot tools, find all callers of `fetch_user`, and migrate them to async."*

---

## 🌐 100% Free Live Cloud Deployment

You can deploy RepoPilot live with zero hosting costs:

| Component | Free Platform | Setup Summary |
| :--- | :--- | :--- |
| **Frontend UI** | [Vercel](https://vercel.com) / [Cloudflare Pages](https://pages.cloudflare.com) | Point Git root directory to `ui/`, build command `npm run build`, output `dist`. Unlimited free bandwidth & SSL. |
| **Backend API** | [Render](https://render.com) / [Hugging Face Spaces](https://huggingface.co/spaces) | Render Web Service: build command `pip install .`, start command `uvicorn repopilot.server.app:app --host 0.0.0.0 --port $PORT`. |

---

## 👤 Author & Maintainer

**Anmol Vishvas**  
- **Email:** [anmol23vishvas@gmail.com](mailto:anmol23vishvas@gmail.com)  
- **GitHub:** [@anmolvishvas](https://github.com/anmolvishvas)  
- **Project Repository:** [https://github.com/anmolvishvas/RepoPilot](https://github.com/anmolvishvas/RepoPilot)

---

## 📄 License

This project is licensed under the Apache 2.0 License. See the [LICENSE](LICENSE) file for details.
