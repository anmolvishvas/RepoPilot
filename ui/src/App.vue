<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import type { MigrationState } from "./types";
import ExecutionTrace from "./components/ExecutionTrace.vue";
import UnifiedDiffViewer from "./components/UnifiedDiffViewer.vue";
import DependencyMiniMap from "./components/DependencyMiniMap.vue";

const state = ref<MigrationState>({
  task_id: "demo_pilot_01",
  repo_path: "/workspace/enterprise-repo",
  recipe: "Upgrade legacy synchronous HTTP requests to async httpx with connection pooling",
  phase: "human_review",
  plan: {
    recipe: "Upgrade legacy synchronous HTTP requests to async httpx with connection pooling",
    steps: [
      {
        step_number: 1,
        file_path: "src/client/http.py",
        transformation_description: "Convert HttpClient.get() to async def with httpx.AsyncClient",
        target_symbol_ids: ["client.http.HttpClient.get"],
      },
      {
        step_number: 2,
        file_path: "src/services/user_service.py",
        transformation_description: "Add await operator to client.get() caller site",
        target_symbol_ids: ["services.user_service.fetch_profile"],
      },
    ],
    affected_files: ["src/client/http.py", "src/services/user_service.py"],
  },
  patches: [
    {
      file_path: "src/client/http.py",
      diff_text: `--- a/src/client/http.py\n+++ b/src/client/http.py\n@@ -12,4 +12,4 @@\n-def get(self, url: str) -> dict:\n-    return requests.get(url).json()\n+async def get(self, url: str) -> dict:\n+    async with httpx.AsyncClient() as client:\n+        resp = await client.get(url)\n+        return resp.json()`,
      target_symbol: "client.http.HttpClient.get",
      explanation: "Upgraded sync requests.get to async httpx.AsyncClient context manager.",
    },
    {
      file_path: "src/services/user_service.py",
      diff_text: `--- a/src/services/user_service.py\n+++ b/src/services/user_service.py\n@@ -45,2 +45,2 @@\n-def fetch_profile(user_id: str):\n-    data = client.get(f"/users/{user_id}")\n+async def fetch_profile(user_id: str):\n+    data = await client.get(f"/users/{user_id}")`,
      target_symbol: "services.user_service.fetch_profile",
      explanation: "Added await operator to newly async HttpClient.get call site.",
    },
  ],
  reflections: [
    {
      iteration: 1,
      root_cause_analysis: "RuntimeWarning: coroutine HttpClient.get was never awaited in user_service.py:46",
      suggested_patch_adjustments: ["Add 'await' operator before client.get invocation"],
      target_files_to_remediate: ["src/services/user_service.py"],
    },
  ],
  tool_traces: [
    {
      tool_name: "planner_agent",
      args: { recipe: "sync-to-async" },
      execution_time_ms: 14.2,
      success: true,
      output_summary: "Generated 2-step topological migration plan.",
    },
    {
      tool_name: "synthesizer_agent",
      args: { target_files: ["src/client/http.py"] },
      execution_time_ms: 82.5,
      success: true,
      output_summary: "Synthesized AST patch for http.py.",
    },
    {
      tool_name: "docker_sandbox_runner",
      args: { repo_path: "/workspace/enterprise-repo" },
      execution_time_ms: 1240.0,
      success: false,
      output_summary: "Tests failed with 1 unawaited coroutine error.",
    },
    {
      tool_name: "critic_agent",
      args: { retry_count: 0 },
      execution_time_ms: 22.1,
      success: true,
      output_summary: "Formulated self-healing reflection to inject 'await'.",
    },
    {
      tool_name: "synthesizer_agent",
      args: { target_files: ["src/services/user_service.py"] },
      execution_time_ms: 64.0,
      success: true,
      output_summary: "Synthesized repair patch adding await.",
    },
    {
      tool_name: "docker_sandbox_runner",
      args: { repo_path: "/workspace/enterprise-repo" },
      execution_time_ms: 1120.0,
      success: true,
      output_summary: "All 18 pytest assertions passed.",
    },
    {
      tool_name: "human_review",
      args: { phase: "verified" },
      execution_time_ms: 0.0,
      success: true,
      output_summary: "Paused at human review checkpoint for operator sign-off.",
    },
  ],
  retry_count: 1,
  max_retries: 3,
  is_terminal: true,
});

const isHumanReview = computed(() => state.value.phase === "human_review");

function handleApprove() {
  state.value.phase = "verified";
  alert("Migration approved! Patches successfully landed to repository.");
}

function handleReject(reason: string) {
  state.value.phase = "failed";
  state.value.error_message = reason;
  alert("Migration rejected by operator.");
}

onMounted(() => {
  // If running in live environment with backend API, connect to SSE stream
  if (window.location.search.includes("task_id=")) {
    const params = new URLSearchParams(window.location.search);
    const taskId = params.get("task_id");
    if (taskId) {
      const eventSource = new EventSource(`/api/v1/migrations/${taskId}/stream`);
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.phase) state.value.phase = data.phase;
        } catch {}
      };
    }
  }
});
</script>

<template>
  <div class="flex flex-col h-screen bg-slate-950 font-sans text-slate-100">
    <!-- Top Navigation Header -->
    <header class="h-14 bg-slate-900 border-b border-slate-800 px-6 flex items-center justify-between flex-shrink-0">
      <div class="flex items-center space-x-4">
        <div class="flex items-center space-x-2">
          <div class="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-white shadow-md">
            RP
          </div>
          <div>
            <h1 class="font-bold text-sm text-slate-100 tracking-tight">RepoPilot</h1>
            <p class="text-[10px] text-slate-400 font-mono">Modernization & Migration Cockpit</p>
          </div>
        </div>

        <div class="h-4 w-px bg-slate-800"></div>

        <div class="flex items-center space-x-2 text-xs font-mono">
          <span class="text-slate-500">Task:</span>
          <span class="text-indigo-400 font-semibold">{{ state.task_id }}</span>
        </div>
      </div>

      <div class="flex items-center space-x-4">
        <!-- Status Badge -->
        <div class="flex items-center space-x-2 px-3 py-1 bg-slate-850 rounded-full border border-slate-800 text-xs">
          <span
            :class="{
              'bg-amber-400': state.phase === 'human_review' || state.phase === 'reflecting',
              'bg-emerald-400': state.phase === 'verified',
              'bg-rose-400': state.phase === 'failed' || state.phase === 'escalated',
              'bg-indigo-400': state.phase === 'synthesizing' || state.phase === 'planning',
            }"
            class="w-2 h-2 rounded-full"
          ></span>
          <span class="capitalize font-mono text-[11px] text-slate-300">{{ state.phase.replace('_', ' ') }}</span>
        </div>

        <span class="text-xs text-slate-400 font-mono">
          Self-Heal: <strong class="text-slate-200">{{ state.retry_count }}</strong> / {{ state.max_retries }}
        </span>
      </div>
    </header>

    <!-- Main Cockpit 3-Column Layout -->
    <main class="flex-1 p-4 grid grid-cols-12 gap-4 overflow-hidden">
      <!-- Left Column: Dependency Mini-Map & Overview (3 cols) -->
      <section class="col-span-3 h-full overflow-hidden">
        <DependencyMiniMap :affected-files="state.plan?.affected_files || []" />
      </section>

      <!-- Center Column: Interactive Unified Diff Viewer (5 cols) -->
      <section class="col-span-5 h-full overflow-hidden">
        <UnifiedDiffViewer
          :patches="state.patches"
          :is-human-review="isHumanReview"
          @approve="handleApprove"
          @reject="handleReject"
        />
      </section>

      <!-- Right Column: Real-time Execution Trace & Stream (4 cols) -->
      <section class="col-span-4 h-full overflow-hidden">
        <ExecutionTrace
          :traces="state.tool_traces"
          :phase="state.phase"
          :retry-count="state.retry_count"
          :max-retries="state.max_retries"
        />
      </section>
    </main>
  </div>
</template>
