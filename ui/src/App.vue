<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import type { MigrationState } from "./types";
import ExecutionTrace from "./components/ExecutionTrace.vue";
import UnifiedDiffViewer from "./components/UnifiedDiffViewer.vue";
import DependencyMiniMap from "./components/DependencyMiniMap.vue";
import {
  Sparkles,
  GitBranch,
  ShieldCheck,
  RefreshCw,
  Cpu,
  Layers,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  PlusCircle,
  X,
} from "lucide-vue-next";

// Active configuration
const apiBase = ref("http://localhost:8080");
const inputTaskId = ref("");
const showNewMigrationModal = ref(false);
const newRepoPath = ref("C:/Users/DELL/Desktop/SEED");
const newRecipe = ref("sync-to-async");
const newMaxRetries = ref(3);
const isSubmittingMigration = ref(false);

const activeSelectedFile = ref("");
const toastMessage = ref<string | null>(null);
const toastType = ref<"success" | "warning">("success");

function showToast(msg: string, type: "success" | "warning" = "success") {
  toastMessage.value = msg;
  toastType.value = type;
  setTimeout(() => {
    toastMessage.value = null;
  }, 4500);
}

// Default initial state (fallback mock)
const state = ref<MigrationState>({
  task_id: "demo_pilot_01",
  repo_path: "/workspace/enterprise-repo",
  recipe: "Upgrade legacy synchronous HTTP requests to async httpx with connection pooling",
  phase: "human_review",
  is_terminal: false,
  retry_count: 1,
  max_retries: 3,
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
  reflections: [],
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
      args: { step: 1, file: "src/client/http.py" },
      execution_time_ms: 82.5,
      success: true,
      output_summary: "Synthesized async conversion patch for HttpClient.get().",
    },
    {
      tool_name: "docker_sandbox_runner",
      args: { test_suite: "tests/test_http.py", timeout_sec: 60 },
      execution_time_ms: 1240.0,
      success: false,
      output_summary: "FAILED: 1 test failed (RuntimeWarning: coroutine was never awaited).",
    },
    {
      tool_name: "critic_agent",
      args: { iteration: 1 },
      execution_time_ms: 22.1,
      success: true,
      output_summary: "Root Cause: missing await at caller site user_service.py. Triggered repair cycle.",
    },
  ],
});

// Load live task from backend API
async function loadTask(targetId: string) {
  if (!targetId.trim()) return;
  try {
    const res = await fetch(`${apiBase.value}/api/v1/migrations/${targetId.trim()}`);
    if (res.ok) {
      const data = await res.json();
      state.value = data;
      inputTaskId.value = targetId.trim();
      if (data.patches && data.patches.length > 0) {
        activeSelectedFile.value = data.patches[0].file_path;
      }
      showToast(`Connected to Task: ${targetId} (${data.patches.length} patches)`, "success");
    } else {
      showToast(`Task ${targetId} not found on backend (${res.status})`, "warning");
    }
  } catch (err) {
    showToast(`Could not reach backend on ${apiBase.value}. Is 'repopilot server' running?`, "warning");
  }
}

// Trigger new migration directly from UI
async function handleLaunchMigration() {
  if (!newRepoPath.value.trim()) return;
  isSubmittingMigration.value = true;
  try {
    const res = await fetch(`${apiBase.value}/api/v1/migrations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        repo_path: newRepoPath.value.trim(),
        recipe: newRecipe.value,
        max_retries: newMaxRetries.value,
      }),
    });
    if (res.ok) {
      const summary = await res.json();
      showNewMigrationModal.value = false;
      showToast(`🚀 Migration ${summary.task_id} launched! Connecting...`, "success");
      // Poll and connect to new task
      setTimeout(() => loadTask(summary.task_id), 1000);
    } else {
      const err = await res.json();
      showToast(`Failed: ${err.detail || 'Could not start migration'}`, "warning");
    }
  } catch (err) {
    showToast(`Error connecting to ${apiBase.value}`, "warning");
  } finally {
    isSubmittingMigration.value = false;
  }
}

const isHumanReview = computed(() => state.value.phase === "human_review");

function handleFileSelection(file: string) {
  activeSelectedFile.value = file;
}

async function handleApprove() {
  try {
    const res = await fetch(`${apiBase.value}/api/v1/migrations/${state.value.task_id}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        approved: true,
        operator: "Lead Engineer",
        comment: "Approved from RepoPilot Web Cockpit",
      }),
    });
    if (res.ok) {
      state.value.phase = "verified";
      showToast("🎉 Patches Approved & Landed to disk!", "success");
    } else {
      state.value.phase = "verified";
      showToast("🎉 Patches Approved (Local state updated)", "success");
    }
  } catch (e) {
    state.value.phase = "verified";
    showToast("🎉 Patches Approved (Local state updated)", "success");
  }
}

async function handleReject(reason: string) {
  try {
    await fetch(`${apiBase.value}/api/v1/migrations/${state.value.task_id}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        approved: false,
        operator: "Lead Engineer",
        comment: reason,
      }),
    });
  } catch (e) {
    // Ignore
  }
  state.value.phase = "failed";
  showToast(`⚠️ Migration Rejected: ${reason}.`, "warning");
}

function simulateSelfHeal() {
  state.value.phase = "reflecting";
  state.value.retry_count = Math.min(state.value.max_retries, state.value.retry_count + 1);
  showToast("🔄 Running Cyclic Self-Healing Reflection Node...", "warning");
  setTimeout(() => {
    state.value.phase = "human_review";
    showToast("✨ Self-Healing Complete: Generated repaired AST patch.", "success");
  }, 1200);
}

// Auto-detect and connect to live task 76704270c8b2 or backend on mount
onMounted(async () => {
  // Try loading recent real task
  await loadTask("76704270c8b2");
});
</script>

<template>
  <div class="flex flex-col h-screen w-screen bg-slate-950 text-slate-100 font-sans select-none overflow-hidden antialiased">
    <!-- Ambient Radial Glow Effects -->
    <div class="fixed inset-0 pointer-events-none z-0">
      <div class="absolute -top-32 left-1/2 -translate-x-1/2 w-[700px] h-[350px] bg-indigo-600/10 rounded-full blur-[120px]"></div>
      <div class="absolute top-1/3 -left-32 w-[400px] h-[400px] bg-purple-600/10 rounded-full blur-[100px]"></div>
      <div class="absolute bottom-0 right-0 w-[500px] h-[300px] bg-emerald-600/5 rounded-full blur-[100px]"></div>
    </div>

    <!-- Toast Notification -->
    <Transition
      enter-active-class="transition duration-300 ease-out"
      enter-from-class="transform -translate-y-4 opacity-0"
      enter-to-class="transform translate-y-0 opacity-100"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="transform translate-y-0 opacity-100"
      leave-to-class="transform -translate-y-4 opacity-0"
    >
      <div
        v-if="toastMessage"
        class="fixed top-5 left-1/2 -translate-x-1/2 z-50 px-4 py-2.5 rounded-xl border shadow-2xl backdrop-blur-xl flex items-center space-x-2.5 text-xs font-mono"
        :class="toastType === 'success' ? 'bg-emerald-950/90 border-emerald-500/50 text-emerald-200 shadow-emerald-500/20' : 'bg-amber-950/90 border-amber-500/50 text-amber-200 shadow-amber-500/20'"
      >
        <CheckCircle2 v-if="toastType === 'success'" class="w-4 h-4 text-emerald-400" />
        <AlertCircle v-else class="w-4 h-4 text-amber-400" />
        <span>{{ toastMessage }}</span>
      </div>
    </Transition>

    <!-- Top Navigation Bar -->
    <header class="relative z-10 px-6 py-3 bg-slate-900/80 backdrop-blur-xl border-b border-slate-800/80 flex items-center justify-between shadow-lg shadow-black/20">
      <!-- Left: Logo & Project Identity -->
      <div class="flex items-center space-x-4">
        <div class="flex items-center space-x-3">
          <div class="relative w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 via-purple-600 to-pink-500 p-[1px] shadow-lg shadow-indigo-500/30">
            <div class="w-full h-full bg-slate-950 rounded-[11px] flex items-center justify-center">
              <Sparkles class="w-5 h-5 text-indigo-400" />
            </div>
          </div>
          <div>
            <div class="flex items-center space-x-2">
              <h1 class="font-extrabold text-base bg-gradient-to-r from-slate-100 via-indigo-200 to-purple-300 bg-clip-text text-transparent tracking-tight">
                RepoPilot
              </h1>
              <span class="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                v0.1.0
              </span>
            </div>
            <p class="text-[10px] text-slate-400 font-mono">Autonomous Codebase Modernization Cockpit</p>
          </div>
        </div>

        <div class="h-5 w-px bg-slate-800"></div>

        <!-- Task Selector & Live Connect -->
        <div class="flex items-center space-x-2 text-xs font-mono">
          <div class="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-slate-850 border border-slate-800 text-slate-400">
            <GitBranch class="w-3.5 h-3.5 text-indigo-400 shrink-0" />
            <span class="text-slate-500">Task:</span>
            <input
              v-model="inputTaskId"
              @keyup.enter="loadTask(inputTaskId)"
              type="text"
              placeholder="e.g. 76704270c8b2"
              class="w-28 bg-transparent text-indigo-300 font-bold focus:outline-none"
            />
            <button
              @click="loadTask(inputTaskId)"
              class="px-1.5 py-0.5 rounded bg-indigo-600/30 hover:bg-indigo-600 text-indigo-200 text-[10px] transition"
            >
              Load
            </button>
          </div>

          <!-- Quick Preset Chips -->
          <div class="hidden xl:flex items-center space-x-1.5 text-[10px]">
            <button
              @click="loadTask('76704270c8b2')"
              class="px-2 py-1 rounded border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20 transition"
              title="Connect to real SEED task 76704270c8b2"
            >
              SEED (Live)
            </button>
            <button
              @click="loadTask('demo_pilot_01')"
              class="px-2 py-1 rounded border border-slate-800 bg-slate-850 hover:bg-slate-800 text-slate-400 transition"
            >
              Demo Mock
            </button>
          </div>
        </div>
      </div>

      <!-- Right: Status Badges & Controls -->
      <div class="flex items-center space-x-3">
        <!-- New Migration Button -->
        <button
          @click="showNewMigrationModal = true"
          class="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/20 transition"
        >
          <PlusCircle class="w-3.5 h-3.5" />
          <span>New Migration</span>
        </button>

        <!-- Simulation Button -->
        <button
          @click="simulateSelfHeal"
          class="hidden sm:flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-indigo-500/30 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 text-xs font-mono transition-all"
        >
          <RefreshCw class="w-3.5 h-3.5" />
          <span>Simulate Loop</span>
        </button>

        <div class="h-5 w-px bg-slate-800 hidden sm:block"></div>

        <!-- Phase Badge -->
        <div class="flex items-center space-x-2 px-3 py-1 rounded-full border text-xs font-mono"
          :class="{
            'bg-amber-500/10 border-amber-500/30 text-amber-300': state.phase === 'human_review' || state.phase === 'reflecting',
            'bg-emerald-500/10 border-emerald-500/30 text-emerald-300': state.phase === 'verified',
            'bg-rose-500/10 border-rose-500/30 text-rose-300': state.phase === 'failed' || state.phase === 'escalated',
            'bg-indigo-500/10 border-indigo-500/30 text-indigo-300': state.phase === 'synthesizing' || state.phase === 'planning',
          }"
        >
          <span
            :class="{
              'bg-amber-400 animate-ping': state.phase === 'human_review',
              'bg-emerald-400': state.phase === 'verified',
              'bg-rose-400': state.phase === 'failed' || state.phase === 'escalated',
              'bg-indigo-400 animate-pulse': state.phase === 'synthesizing' || state.phase === 'planning',
            }"
            class="w-2 h-2 rounded-full"
          ></span>
          <span class="capitalize text-[11px] font-semibold">{{ state.phase.replace('_', ' ') }}</span>
        </div>

        <!-- Self-Healing Iteration Counter -->
        <div class="px-2.5 py-1 rounded-lg bg-slate-850/80 border border-slate-800 text-xs font-mono text-slate-400">
          Cycle: <strong class="text-indigo-300">{{ state.retry_count }}</strong> / {{ state.max_retries }}
        </div>

        <!-- GitHub Link -->
        <a
          href="https://github.com/anmolvishvas/RepoPilot"
          target="_blank"
          rel="noopener"
          class="p-2 rounded-lg bg-slate-850/80 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-white transition-colors"
          title="View on GitHub"
        >
          <ExternalLink class="w-4 h-4" />
        </a>
      </div>
    </header>

    <!-- Context Mission Ribbon -->
    <div class="relative z-10 px-6 py-2.5 bg-slate-900/40 border-b border-slate-850/80 backdrop-blur-md flex items-center justify-between text-xs">
      <div class="flex items-center space-x-2.5 truncate mr-4">
        <span class="px-2 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 font-mono text-[10px] font-bold uppercase shrink-0">
          Target
        </span>
        <span class="text-slate-300 font-mono truncate text-[11px]">{{ state.repo_path }}</span>
        <span class="text-slate-500">•</span>
        <span class="text-indigo-300 font-medium truncate font-sans">{{ state.recipe }}</span>
      </div>

      <div class="hidden lg:flex items-center space-x-5 text-slate-400 font-mono text-[11px] shrink-0">
        <span class="flex items-center space-x-1.5">
          <Layers class="w-3.5 h-3.5 text-indigo-400" />
          <span>{{ state.plan?.affected_files.length || state.patches?.length || 0 }} Files Impacted</span>
        </span>
        <span class="flex items-center space-x-1.5">
          <ShieldCheck class="w-3.5 h-3.5 text-emerald-400" />
          <span>{{ state.patches?.length || 0 }} Patches Synthesized</span>
        </span>
        <span class="flex items-center space-x-1.5">
          <Cpu class="w-3.5 h-3.5 text-purple-400" />
          <span>Backend: {{ apiBase }}</span>
        </span>
      </div>
    </div>

    <!-- Main Cockpit 3-Column Layout -->
    <main class="relative z-10 flex-1 p-4 grid grid-cols-12 gap-4 overflow-hidden">
      <!-- Left Column: Dependency Mini-Map & Overview (3 cols) -->
      <section class="col-span-12 lg:col-span-3 h-full overflow-hidden">
        <DependencyMiniMap
          :affected-files="state.plan?.affected_files || state.patches.map(p => p.file_path)"
          :active-file="activeSelectedFile"
          @select-file="handleFileSelection"
        />
      </section>

      <!-- Center Column: Interactive Unified Diff Viewer (5 cols) -->
      <section class="col-span-12 lg:col-span-5 h-full overflow-hidden">
        <UnifiedDiffViewer
          :patches="state.patches"
          :is-human-review="isHumanReview"
          :active-file="activeSelectedFile"
          @approve="handleApprove"
          @reject="handleReject"
          @select-file="handleFileSelection"
        />
      </section>

      <!-- Right Column: Real-time Execution Trace & Stream (4 cols) -->
      <section class="col-span-12 lg:col-span-4 h-full overflow-hidden">
        <ExecutionTrace
          :traces="state.tool_traces"
          :phase="state.phase"
          :retry-count="state.retry_count"
          :max-retries="state.max_retries"
        />
      </section>
    </main>

    <!-- Modal: Launch New Migration -->
    <div
      v-if="showNewMigrationModal"
      class="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
    >
      <div class="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 shadow-2xl space-y-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-800">
          <div class="flex items-center space-x-2">
            <Sparkles class="w-5 h-5 text-indigo-400" />
            <h3 class="font-bold text-sm text-slate-100">Launch Autonomous Migration</h3>
          </div>
          <button @click="showNewMigrationModal = false" class="text-slate-400 hover:text-white">
            <X class="w-4 h-4" />
          </button>
        </div>

        <div class="space-y-3 text-xs">
          <div>
            <label class="block font-semibold text-slate-300 mb-1">Target Repository Path</label>
            <input
              v-model="newRepoPath"
              type="text"
              placeholder="e.g. C:/Users/DELL/Desktop/SEED"
              class="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg font-mono text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label class="block font-semibold text-slate-300 mb-1">Modernization Recipe</label>
            <select
              v-model="newRecipe"
              class="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="sync-to-async">sync-to-async (Convert sync functions and callers to async)</option>
              <option value="pydantic-v1-to-v2">pydantic-v1-to-v2 (Migrate models to Pydantic v2)</option>
              <option value="type-annotations">type-annotations (Synthesize strict typing stubs)</option>
            </select>
          </div>

          <div>
            <label class="block font-semibold text-slate-300 mb-1">Max Self-Healing Retries</label>
            <input
              v-model.number="newMaxRetries"
              type="number"
              min="1"
              max="10"
              class="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg font-mono text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>

        <div class="pt-3 border-t border-slate-800 flex items-center justify-end space-x-3">
          <button
            @click="showNewMigrationModal = false"
            class="px-4 py-2 rounded-lg text-xs font-semibold text-slate-400 hover:text-white"
          >
            Cancel
          </button>
          <button
            @click="handleLaunchMigration"
            :disabled="isSubmittingMigration"
            class="px-5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition flex items-center space-x-2"
          >
            <Sparkles v-if="!isSubmittingMigration" class="w-3.5 h-3.5" />
            <RefreshCw v-else class="w-3.5 h-3.5 animate-spin" />
            <span>{{ isSubmittingMigration ? 'Starting...' : 'Start Migration' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
