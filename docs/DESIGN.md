# UI/UX Specification: Vue 3 / Nuxt 3 Reactive Canvas

## RepoPilot: Autonomous Codebase Modernization & Migration Agent

**Author:** Anmol Vishvas (<anmol23vishvas@gmail.com>)  
**Target Repository:** [https://github.com/anmolvishvas/RepoPilot](https://github.com/anmolvishvas/RepoPilot)  
**Status:** Design Specification Baseline  

---

## 1. Design Philosophy & UX Principles

The RepoPilot Reactive Canvas is engineered for Senior Engineers and Platform Architects who demand deep situational awareness during autonomous codebase transformations. It departs from verbose, conversational AI interfaces and embraces an IDE-grade, cockpit-style dashboard focused on:

1. **Information Density:** Prioritize structured tabular metrics, syntax-highlighted diffs, and directed graph visuals over conversational fluff.
2. **Zero-Latency Visual Feedback:** Provide sub-50ms reactive updates via persistent Server-Sent Events (SSE) connections streaming agent thoughts, active MCP tool executions, and Docker sandbox stdout.
3. **Instant State Recognition:** Enable operators to distinguish between planning, synthesizing, test execution, and self-healing phases at a glance through purposeful color coding.
4. **Deterministic Operator Agency:** Human-in-the-loop controls (Approve & Commit, Request Changes, Rollback) are persistently anchored and impossible to trigger accidentally.

---

## 2. Color Palette & Design Tokens

The interface utilizes a dark-mode first aesthetic built upon Tailwind CSS variables, optimized for prolonged high-focus engineering sessions.

### 2.1 Core Palette Tokens

```css
:root {
  /* Surface & Background */
  --bg-primary: #0f172a;       /* Slate 900 (Main Canvas Background) */
  --bg-surface: #1e293b;       /* Slate 800 (Card & Panel Surface) */
  --bg-elevated: #334155;      /* Slate 700 (Hover States, Borders, Tooltips) */
  --border-subtle: #334155;    /* Slate 700 */
  --border-focus: #6366f1;     /* Indigo 500 */

  /* Text & Typography */
  --text-primary: #f8fafc;     /* Slate 50 */
  --text-secondary: #94a3b8;   /* Slate 400 */
  --text-muted: #64748b;       /* Slate 500 */

  /* Brand & Primary Actions */
  --brand-primary: #6366f1;    /* Indigo 500 (Primary CTAs & Active Nodes) */
  --brand-hover: #4f46e5;      /* Indigo 600 */
  --brand-subtle: #312e81;     /* Indigo 900 */

  /* Semantic Feedback & State States */
  --status-success: #10b981;   /* Emerald 500 (Tests Passing, Clean Diffs) */
  --status-success-bg: #064e3b;/* Emerald 900 */
  --status-warning: #f59e0b;   /* Amber 500 (Agent Reflection, Retries, Warnings) */
  --status-warning-bg: #78350f;/* Amber 900 */
  --status-error: #f43f5e;     /* Rose 500 (Test Failures, Syntax Errors, Rejections) */
  --status-error-bg: #881337;  /* Rose 900 */
  --status-info: #0ea5e9;      /* Sky 500 (Tool Calls, Information) */
}
```

---

## 3. Typography Scale & Font Pairings

- **UI & Controls Font:** `Inter`, `-apple-system`, `BlinkMacSystemFont`, `sans-serif`. Clean, high-legibility geometric sans-serif for UI labels, metadata tags, and metric cards.
- **Code, Diffs & Terminal Logs:** `JetBrains Mono`, `Fira Code`, `monospace`. Ligature-enabled, fixed-pitch font for AST nodes, unified diffs, line numbers, and terminal output.

```css
/* Typography Scale */
--font-sans: 'Inter', sans-serif;
--font-mono: 'JetBrains Mono', monospace;

--text-xs:   0.75rem / 1.0rem;   /* 12px - Timestamps, badges, metadata */
--text-sm:   0.875rem / 1.25rem; /* 14px - Code diffs, log streams, table rows */
--text-base: 1.0rem / 1.5rem;    /* 16px - Standard UI prose, inputs */
--text-lg:   1.125rem / 1.75rem; /* 18px - Panel titles, card headers */
--text-xl:   1.25rem / 1.75rem;  /* 20px - Section headlines */
--text-2xl:  1.5rem / 2.0rem;    /* 24px - Metric heroes, page titles */
```

---

## 4. Layout Architecture & Component Anatomy

The canvas is structured as a 3-column cockpit layout maximizing vertical screen real estate:

```
+---------------------------------------------------------------------------------------------------------+
| [RepoPilot Header]  Project: /my-repo  | Recipe: sync-to-async | Status: REFLECTING (Cycle 2/3)  [ACTIONS]|
+------------------------------------+------------------------------------+-------------------------------+
| PANEL 1: Execution Trace (30%)     | PANEL 2: Unified Diff Viewer (45%) | PANEL 3: Dependency Graph(25%)|
|                                    |                                    |                               |
| [SSE Live Agent Stream]            | File: src/services/client.py       | [Symbol Blast Radius MiniMap] |
| 15:42:01 Planner: AST resolved     | Split: Before (Sync) / After(Async)|                               |
| 15:42:03 Tool: search_ast_symbols  |  42 - def get(self, url: str):     |    [client.py]                |
| 15:42:05 Patch: generated diff     |  42 + async def get(self, url):    |         │                     |
| 15:42:09 Sandbox: Pytest started   |  43 -   res = requests.get(url)    |         ▼                     |
| 15:42:15 Sandbox: 1 Failed (Assert)|  43 +   res = await client.get(url)|    [service.py]               |
| 15:42:16 Critic: Missing await     |                                    |         │                     |
| 15:42:18 Synthesizer: Repairing... | [Inline AST Comment Annotations]   |         ▼                     |
|                                    |                                    |    [handlers.py]              |
|                                    |                                    |                               |
| [Docker Sandbox Live Logs]         |                                    | [Affected Files Table]        |
| > pytest -v tests/test_client.py   |                                    | - client.py (2 symbols)       |
| FAILED test_get_timeout - Assert   |                                    | - service.py (4 symbols)      |
+------------------------------------+------------------------------------+-------------------------------+
| FOOTER: [Rollback to Clean Commit]             [Request Agent Changes]           [Approve & Commit PR]  |
+---------------------------------------------------------------------------------------------------------+
```

---

### 4.1 Component 1: Real-Time Agent Execution Trace (`ExecutionTrace.vue`)
- **SSE Connection:** Consumes `/api/stream/events?task_id={id}` using `EventSource`.
- **State Badges:** Displays dynamic state pills:
  - `PLANNING` (Indigo)
  - `SYNTHESIZING` (Sky)
  - `SANDBOX_TESTING` (Amber with pulse animation)
  - `REFLECTING` (Amber with wrench icon)
  - `VERIFIED` (Emerald with checkmark)
  - `FAILED` (Rose with alert icon)
- **Tool Invocations:** Collapsible accordion rows detailing tool names (`run_isolated_tests`, `apply_unified_diff`), input arguments, execution latencies (ms), and response payloads.
- **Terminal Emulator:** Embedded ANSI-capable terminal output rendering real-time Docker sandbox logs with color-coded pass/fail assertions.

---

### 4.2 Component 2: Interactive Split-Screen Diff Viewer (`UnifiedDiffViewer.vue`)
- **View Modes:** Toggle between Split-Screen (side-by-side) and Unified (inline).
- **Syntax Highlighting:** Integrated Monaco Editor or Prism.js highlighting for Python, TypeScript, and Go.
- **AST Semantic Breadcrumb:** Displays current class and function scope above each diff hunk (e.g., `HttpClient > async def fetch_data()`).
- **Interactive Annotations:** Shows agent comments explaining *why* a particular AST transformation was performed (e.g., `"Added await keyword because httpx.AsyncClient returns a Coroutine"`).
- **Line-Level Granularity:** Red background (`--status-error-bg`) for deletions with bright red strikethrough; Green background (`--status-success-bg`) for additions.

---

### 4.3 Component 3: Dependency Graph Mini-Map (`DependencyMiniMap.vue`)
- **Interactive Force-Directed Graph:** Rendered using D3.js or SVG, displaying nodes for files, classes, and functions.
- **Visual Node Encoding:**
  - **Green Node:** Direct target of current migration patch.
  - **Amber Node:** Downstream dependent affected by blast radius.
  - **Gray Node:** Unmodified caller in caller-tree.
- **Hover Inspection:** Hovering over any node displays incoming/outgoing call edges, parameter signature changes, and current test pass rate.
- **Quick Navigation:** Clicking an AST node centers the diff viewer directly on that file's patch hunk.

---

## 5. User Interaction Workflows & State Transitions

1. **Task Initialization:** User enters target directory and migration recipe (e.g., `repopilot migrate --recipe sync-to-async`). The UI renders the initial AST dependency tree.
2. **Streamed Execution:** As the agent iterates through planning and sandbox testing, the execution trace auto-scrolls, highlighting failing tests in red.
3. **Self-Healing Reflection:** When tests fail, the UI visually animates an amber transition to the `Critic` node, updating the retry counter badge (`Attempt 2 of 3`).
4. **Final Operator Sign-Off:** Once tests pass (`100% Passing` in emerald), the `Approve & Commit PR` button glows indigo. Clicking opens a modal previewing the commit message, branch name, and complete multi-file unified diff.
