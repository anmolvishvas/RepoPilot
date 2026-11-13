## 🎯 Architectural Motivation & Summary

Implements **Phase 3: Hybrid Code-RAG Pipeline (Qdrant + BM25 + FlashRank)** (TASK-301, TASK-302, TASK-303, TASK-304), giving RepoPilot deep, syntactically-bound semantic and lexical codebase retrieval.

Key additions:
- **AST Syntactic Chunker (`src/repopilot/rag/chunker.py`)**:
  - Slices code along exact semantic AST node boundaries (functions, classes, methods, module globals).
  - Guarantees zero code fractures mid-statement.
  - Enriches chunks with context headers, parent classes, parameters, and imports.
- **Dense Vector Storage with FastEmbed (`src/repopilot/rag/vector_store.py`)**:
  - In-memory or persistent Qdrant client collection management with 384-dimensional cosine distance.
  - Generates semantic embeddings with `BAAI/bge-small-en-v1.5` on CPU.
  - Supports payload metadata filtering (e.g., filtering by file path).
- **Sparse Lexical Search with Rank-BM25 (`src/repopilot/rag/bm25_index.py`)**:
  - Code-aware tokenization decomposing both `snake_case` and `camelCase`/`PascalCase` identifiers.
  - Guarantees exact identifier discovery for function names, variables, and error strings.
- **Reciprocal Rank Fusion (`src/repopilot/rag/fusion.py`)**:
  - Merges dense semantic and sparse lexical ranks using standard RRF ($k=60$), prioritizing chunks that score well in both modalities.
- **Cross-Encoder Reranker (`src/repopilot/rag/reranker.py`)**:
  - FlashRank CPU-optimized cross-encoder (`ms-marco-TinyBERT-L-2-v2`) re-scoring candidates down to top-K high-precision results.
- **Unified Facade (`src/repopilot/rag/engine.py`)**:
  - `HybridCodeRAG` coordinating end-to-end repository indexing, hybrid search, RRF rank merging, and reranking.
- **Unit Test Coverage**:
  - `test_chunker.py`, `test_bm25_index.py`, `test_fusion.py`, `test_hybrid_rag.py`.
  - **42/42 tests passing**, **94.53% overall branch coverage** ($\ge 90\%$ enforced), and 0 errors in `mypy --strict` and `ruff check`.

---

## 🧩 Subsystems Affected

- [x] **Hybrid Code-RAG** (`src/repopilot/rag/`)
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

- [x] **Sandbox Isolation:** All tests run without host contamination.
- [x] **Strict Typing:** `mypy --strict src/ tests/` passes cleanly across 35 source files.
- [x] **Code Formatting & Linting:** `ruff check .` and `ruff format --check .` are 100% clean.
- [x] **Test Coverage:** 42 tests pass with 94.53% coverage ($\ge 90\%$ enforced).
