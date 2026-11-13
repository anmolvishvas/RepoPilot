## 🎯 Architectural Motivation & Summary

<!--
Provide a concise overview of the change, why it is needed, and how it aligns with RepoPilot's core architecture.
Link any relevant issues or tasks from docs/TASKS.md.
-->

Closes # <!-- issue number -->

---

## 🧩 Subsystems Affected

- [ ] **AST & Code Intelligence** (`src/repopilot/ast/`)
- [ ] **Hybrid Code-RAG** (`src/repopilot/rag/`)
- [ ] **FastMCP Code Server Layer** (`src/repopilot/mcp/`)
- [ ] **Execution Sandbox** (`src/repopilot/sandbox/`)
- [ ] **LangGraph Multi-Agent Engine** (`src/repopilot/agents/`)
- [ ] **Gateway & API Server** (`src/repopilot/server/`)
- [ ] **Reactive UI Canvas** (`ui/`)
- [ ] **CI/CD & Developer Tooling** (`.github/`, root configs)
- [ ] **Documentation** (`docs/`)

---

## 🏷️ Type of Change

- [ ] `feat`: New feature or capability
- [ ] `fix`: Bug fix
- [ ] `refactor`: Code refactoring without behavioral changes
- [ ] `perf`: Performance enhancement (e.g. AST indexing speedup, reranking latency reduction)
- [ ] `docs`: Documentation addition or update
- [ ] `test`: Unit, integration, or e2e test suite additions
- [ ] `chore`: Dependency updates, tooling, or build configuration

---

## ⚠️ Breaking Change Notice

- [ ] **Yes** (Requires migration steps or schema changes; details described below)
- [ ] **No**

*If yes, describe the breaking impact, migration steps, and backward compatibility plan:*

---

## 🧪 Verification & Quality Checklist

Adheres strictly to the principles in [`docs/RULES.md`](docs/RULES.md):

- [ ] **Sandbox Isolation:** No untrusted test executions run on host; ephemeral Docker containers used.
- [ ] **Strict Typing:** `mypy --strict src/ tests/` executes with zero errors.
- [ ] **Code Formatting & Linting:** `ruff check .` and `ruff format --check .` are clean.
- [ ] **Test Coverage:** Unit and/or integration tests added; overall branch coverage remains $\ge 90\%$.
- [ ] **Pydantic Validation:** All schemas utilize strict Pydantic v2 models.
- [ ] **Async & Concurrency Safety:** External I/O operations are guarded with timeouts; `asyncio.CancelledError` properly propagated.
- [ ] **Documentation Synchronized:** `docs/` and `README.md` updated to reflect modifications.

---

## 📸 Screenshots / Execution Traces (Optional)

<!-- Attach terminal outputs, diff previews, or screenshots of the Vue 3 Canvas if applicable -->
