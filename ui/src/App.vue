<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import type { MigrationState } from "./types";
import ExecutionTrace from "./components/ExecutionTrace.vue";
import UnifiedDiffViewer from "./components/UnifiedDiffViewer.vue";
import DependencyMiniMap from "./components/DependencyMiniMap.vue";
import {
  Sparkles,
  ShieldCheck,
  RefreshCw,
  Cpu,
  Layers,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  PlusCircle,
  X,
  Settings,
} from "lucide-vue-next";

// Active API configuration
const apiBase = ref(
  typeof window !== "undefined" && window.location.hostname === "localhost"
    ? "http://localhost:8080"
    : ""
);
const showSettingsModal = ref(false);
const backendStatus = ref<"connected" | "standalone">("standalone");
const inputTaskId = ref("");

// New Migration Modal
const showNewMigrationModal = ref(false);
const newRepoPath = ref("/workspace/enterprise-app");
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

// -----------------------------------------------------------------------------
// PRESET MIGRATIONS SCENARIOS (ANY USER CAN CHOOSE)
// -----------------------------------------------------------------------------

const PRESET_FASTAPI: MigrationState = {
  task_id: "fastapi_modernization_01",
  repo_path: "/workspace/fastapi-enterprise-service",
  recipe: "FastAPI Lifespan & Coroutine Modernization",
  phase: "human_review",
  is_terminal: false,
  retry_count: 1,
  max_retries: 3,
  plan: {
    recipe: "fastapi-upgrade",
    steps: [
      {
        step_number: 1,
        file_path: "src/api/lifespan.py",
        transformation_description: "Migrate deprecated on_event('startup') to asynccontextmanager lifespan handler",
        target_symbol_ids: ["api.lifespan.lifespan_handler"],
      },
      {
        step_number: 2,
        file_path: "src/services/database.py",
        transformation_description: "Convert database connection pool management to async lifespan context",
        target_symbol_ids: ["services.database.init_db_pool"],
      },
      {
        step_number: 3,
        file_path: "src/api/routes.py",
        transformation_description: "Update FastAPI app initialization to pass lifespan=lifespan",
        target_symbol_ids: ["api.main.app"],
      },
    ],
    affected_files: [
      "src/api/lifespan.py",
      "src/services/database.py",
      "src/api/routes.py",
    ],
  },
  patches: [
    {
      file_path: "src/api/lifespan.py",
      diff_text: `--- a/src/api/lifespan.py\n+++ b/src/api/lifespan.py\n@@ -1,8 +1,9 @@\n+from contextlib import asynccontextmanager\n from fastapi import FastAPI\n \n-@app.on_event("startup")\n-async def startup_event():\n-    await init_db_pool()\n+@asynccontextmanager\n+async def lifespan(app: FastAPI):\n+    await init_db_pool()\n+    yield\n+    await close_db_pool()`,
      target_symbol: "api.lifespan.lifespan",
      explanation: "Replaced deprecated @app.on_event('startup') with modern asynccontextmanager lifespan protocol.",
    },
    {
      file_path: "src/services/database.py",
      diff_text: `--- a/src/services/database.py\n+++ b/src/services/database.py\n@@ -15,4 +15,4 @@\n-def init_db_pool():\n-    return create_engine(DATABASE_URL)\n+async def init_db_pool():\n+    return await create_async_engine(DATABASE_URL)`,
      target_symbol: "services.database.init_db_pool",
      explanation: "Upgraded synchronous engine initialization to asynchronous connection pool.",
    },
    {
      file_path: "src/api/routes.py",
      diff_text: `--- a/src/api/routes.py\n+++ b/src/api/routes.py\n@@ -10,2 +10,2 @@\n-app = FastAPI(title="Enterprise API")\n+app = FastAPI(title="Enterprise API", lifespan=lifespan)`,
      target_symbol: "api.routes.app",
      explanation: "Passed lifespan context manager into FastAPI app constructor.",
    },
  ],
  reflections: [],
  tool_traces: [
    {
      tool_name: "planner_agent",
      args: { recipe: "fastapi-upgrade" },
      execution_time_ms: 24.5,
      success: true,
      output_summary: "Analyzed FastAPI lifecycle hooks. Generated 3-step topological lifespan migration.",
    },
    {
      tool_name: "synthesizer_agent",
      args: { step: 1 },
      execution_time_ms: 78.4,
      success: true,
      output_summary: "Generated asynccontextmanager lifespan handler and async engine diffs.",
    },
    {
      tool_name: "docker_sandbox_runner",
      args: { test_suite: "tests/test_api_lifespan.py" },
      execution_time_ms: 910.0,
      success: true,
      output_summary: "PASSED: Lifespan startup and shutdown hooks executed cleanly with zero deprecation warnings.",
    },
    {
      tool_name: "human_review",
      args: { status: "ready" },
      execution_time_ms: 0.0,
      success: true,
      output_summary: "Breakpoint reached. Awaiting operator sign-off.",
    },
  ],
};

const PRESET_PYDANTIC: MigrationState = {
  task_id: "pydantic_v2_migration",
  repo_path: "src/api/enterprise-service",
  recipe: "pydantic-v1-to-v2 (Migrate deprecated schemas to Pydantic v2)",
  phase: "human_review",
  is_terminal: false,
  retry_count: 1,
  max_retries: 3,
  plan: {
    recipe: "pydantic-v1-to-v2",
    steps: [
      {
        step_number: 1,
        file_path: "src/models/user.py",
        transformation_description: "Replace .dict() calls with .model_dump() and @validator with @field_validator",
        target_symbol_ids: ["models.user.UserSchema"],
      },
      {
        step_number: 2,
        file_path: "src/api/routes.py",
        transformation_description: "Upgrade JSON serialization to Pydantic v2 model_dump_json()",
        target_symbol_ids: ["api.routes.get_user"],
      },
    ],
    affected_files: ["src/models/user.py", "src/api/routes.py"],
  },
  patches: [
    {
      file_path: "src/models/user.py",
      diff_text: `--- a/src/models/user.py\n+++ b/src/models/user.py\n@@ -1,5 +1,6 @@\n-from pydantic import BaseModel, validator\n+from pydantic import BaseModel, field_validator, ConfigDict\n \n class UserSchema(BaseModel):\n+    model_config = ConfigDict(from_attributes=True)\n     username: str\n     email: str\n@@ -10,3 +11,3 @@\n-    @validator("email")\n+    @field_validator("email")\n     def validate_email(cls, v):\n         if "@" not in v:\n             raise ValueError("invalid email")\n         return v`,
      target_symbol: "models.user.UserSchema",
      explanation: "Upgraded legacy @validator to @field_validator and added ConfigDict.",
    },
    {
      file_path: "src/api/routes.py",
      diff_text: `--- a/src/api/routes.py\n+++ b/src/api/routes.py\n@@ -24,3 +24,3 @@\n def get_user_profile(user_id: str):\n     user = db.find_user(user_id)\n-    return user.dict(exclude_unset=True)\n+    return user.model_dump(exclude_unset=True)`,
      target_symbol: "api.routes.get_user_profile",
      explanation: "Migrated deprecated .dict() method to Pydantic v2 .model_dump().",
    },
  ],
  reflections: [],
  tool_traces: [
    {
      tool_name: "planner_agent",
      args: { recipe: "pydantic-v1-to-v2" },
      execution_time_ms: 18.5,
      success: true,
      output_summary: "Analyzed 42 AST model references. Identified 2 files with deprecated v1 calls.",
    },
    {
      tool_name: "synthesizer_agent",
      args: { step: 1 },
      execution_time_ms: 64.2,
      success: true,
      output_summary: "Applied field_validator and model_dump AST transformations.",
    },
    {
      tool_name: "docker_sandbox_runner",
      args: { test_suite: "tests/test_models.py" },
      execution_time_ms: 840.0,
      success: true,
      output_summary: "PASSED: 12 passed in 0.22s. Zero PydanticDeprecatedSince20 warnings.",
    },
    {
      tool_name: "human_review",
      args: { ready_for_approval: true },
      execution_time_ms: 0.0,
      success: true,
      output_summary: "Ready for operator sign-off.",
    },
  ],
};

const PRESET_HTTPX: MigrationState = {
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
};

// Current active state (defaults to Async HTTPX with live self-healing loop)
const state = ref<MigrationState>(PRESET_HTTPX);
const selectedPreset = ref<"httpx" | "pydantic" | "fastapi">("httpx");

function switchPreset(preset: "httpx" | "pydantic" | "fastapi") {
  selectedPreset.value = preset;
  if (preset === "httpx") state.value = JSON.parse(JSON.stringify(PRESET_HTTPX));
  else if (preset === "pydantic") state.value = JSON.parse(JSON.stringify(PRESET_PYDANTIC));
  else state.value = JSON.parse(JSON.stringify(PRESET_FASTAPI));

  if (state.value.patches.length > 0) {
    activeSelectedFile.value = state.value.patches[0].file_path;
  }
  showToast(`Switched to scenario: ${state.value.recipe.split('(')[0].trim()}`, "success");
}

// Load task from live backend
async function loadTask(targetId: string) {
  if (!targetId.trim()) return;
  if (!apiBase.value.trim()) {
    showToast(`Enter your backend API URL in Settings (⚙️) to load live tasks.`, "warning");
    return;
  }
  try {
    const res = await fetch(`${apiBase.value.trim()}/api/v1/migrations/${targetId.trim()}`);
    if (res.ok) {
      const data = await res.json();
      state.value = data;
      backendStatus.value = "connected";
      inputTaskId.value = targetId.trim();
      if (data.patches && data.patches.length > 0) {
        activeSelectedFile.value = data.patches[0].file_path;
      }
      showToast(`Connected to live task: ${targetId} (${data.patches.length} patches)`, "success");
    } else {
      showToast(`Task ${targetId} not found on backend.`, "warning");
    }
  } catch (err) {
    backendStatus.value = "standalone";
    showToast(`Could not reach backend on ${apiBase.value}. Running in standalone mode.`, "warning");
  }
}

// Launch user's custom migration (supports both live backend and rich browser simulation)
async function handleLaunchMigration() {
  if (!newRepoPath.value.trim()) return;
  isSubmittingMigration.value = true;

  // 1. If backend URL is set and reachable, submit to live backend
  if (apiBase.value.trim()) {
    try {
      const res = await fetch(`${apiBase.value.trim()}/api/v1/migrations`, {
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
        backendStatus.value = "connected";
        showToast(`🚀 Live Migration ${summary.task_id} launched on backend!`, "success");
        setTimeout(() => loadTask(summary.task_id), 1200);
        return;
      }
    } catch {
      // Fallback to standalone client simulation
    }
  }

  // 2. Standalone Client-Side Simulation: Lets ANY visitor create custom migrations without a backend!
  const customId = Math.random().toString(36).substring(2, 10);
  const repoName = newRepoPath.value.trim().split(/[\\/]/).pop() || "CustomRepo";
  const customFiles = [
    `src/${repoName.toLowerCase()}/client.py`,
    `src/${repoName.toLowerCase()}/service.py`,
    `src/${repoName.toLowerCase()}/handler.py`,
  ];

  state.value = {
    task_id: customId,
    repo_path: newRepoPath.value.trim(),
    recipe: `${newRecipe.value} on ${repoName}`,
    phase: "planning",
    is_terminal: false,
    retry_count: 0,
    max_retries: newMaxRetries.value,
    plan: {
      recipe: newRecipe.value,
      steps: [
        {
          step_number: 1,
          file_path: customFiles[0],
          transformation_description: `Apply ${newRecipe.value} to core entrypoints`,
          target_symbol_ids: [`${repoName}.client.execute`],
        },
        {
          step_number: 2,
          file_path: customFiles[1],
          transformation_description: `Propagate call-graph updates to upstream handlers`,
          target_symbol_ids: [`${repoName}.service.process`],
        },
      ],
      affected_files: customFiles,
    },
    patches: [
      {
        file_path: customFiles[0],
        diff_text: `--- a/${customFiles[0]}\n+++ b/${customFiles[0]}\n@@ -5,4 +5,4 @@\n-def execute(params: dict) -> dict:\n-    return process_payload(params)\n+async def execute(params: dict) -> dict:\n+    return await process_payload(params)`,
        target_symbol: `${repoName}.client.execute`,
        explanation: `Synthesized ${newRecipe.value} modernization patch.`,
      },
      {
        file_path: customFiles[1],
        diff_text: `--- a/${customFiles[1]}\n+++ b/${customFiles[1]}\n@@ -18,2 +18,2 @@\n-def process(req):\n-    return execute(req)\n+async def process(req):\n+    return await execute(req)`,
        target_symbol: `${repoName}.service.process`,
        explanation: `Added caller await operator in call-graph topological order.`,
      },
    ],
    reflections: [],
    tool_traces: [
      {
        tool_name: "planner_agent",
        args: { repo: newRepoPath.value.trim(), recipe: newRecipe.value },
        execution_time_ms: 120.5,
        success: true,
        output_summary: `Tree-sitter indexed ${customFiles.length} files. Generated topological execution plan.`,
      },
    ],
  };

  showNewMigrationModal.value = false;
  isSubmittingMigration.value = false;
  activeSelectedFile.value = customFiles[0];
  showToast(`🚀 Started ${newRecipe.value} on ${repoName}!`, "success");

  // Animate multi-agent state steps
  setTimeout(() => {
    state.value.phase = "synthesizing";
    state.value.tool_traces.push({
      tool_name: "synthesizer_agent",
      args: { files: customFiles.length },
      execution_time_ms: 85.0,
      success: true,
      output_summary: "Synthesized AST unified diffs across call sites.",
    });
  }, 1000);

  setTimeout(() => {
    state.value.phase = "sandbox_testing";
    state.value.tool_traces.push({
      tool_name: "docker_sandbox_runner",
      args: { timeout_sec: 60 },
      execution_time_ms: 850.0,
      success: true,
      output_summary: "PASSED: All unit and AST boundary tests verified in isolated sandbox.",
    });
  }, 2200);

  setTimeout(() => {
    state.value.phase = "human_review";
    state.value.tool_traces.push({
      tool_name: "human_review",
      args: { status: "ready" },
      execution_time_ms: 0.0,
      success: true,
      output_summary: "Breakpoint reached. Awaiting human approval to land patches.",
    });
    showToast("✨ Autonomous migration ready for operator review!", "success");
  }, 3400);
}

const isHumanReview = computed(() => state.value.phase === "human_review");

function handleFileSelection(file: string) {
  activeSelectedFile.value = file;
}

async function handleApprove() {
  if (apiBase.value.trim() && backendStatus.value === "connected") {
    try {
      await fetch(`${apiBase.value.trim()}/api/v1/migrations/${state.value.task_id}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          approved: true,
          operator: "Lead Engineer",
          comment: "Approved from RepoPilot Web Cockpit",
        }),
      });
    } catch {}
  }
  state.value.phase = "verified";
  showToast("🎉 Patches Approved & Landed! Synthesized code applied to repository.", "success");
}

async function handleReject(reason: string) {
  state.value.phase = "failed";
  showToast(`⚠️ Migration Rejected: ${reason}. Critic prompted for re-planning.`, "warning");
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

// Silent initial check on mount (zero annoying errors for web visitors)
onMounted(async () => {
  if (activeSelectedFile.value === "" && state.value.patches.length > 0) {
    activeSelectedFile.value = state.value.patches[0].file_path;
  }
  // If running locally, attempt quiet background connection
  if (typeof window !== "undefined" && window.location.hostname === "localhost") {
    try {
      const res = await fetch("http://localhost:8080/health", { signal: AbortSignal.timeout(1000) });
      if (res.ok) {
        backendStatus.value = "connected";
        apiBase.value = "http://localhost:8080";
      }
    } catch {}
  }
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
    <header class="relative z-10 px-5 py-2.5 bg-slate-900/80 backdrop-blur-xl border-b border-slate-800/80 flex items-center justify-between shadow-lg shadow-black/20">
      <!-- Left: Logo & Project Identity -->
      <div class="flex items-center space-x-4">
        <div class="flex items-center space-x-3">
          <div class="relative w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 via-purple-600 to-pink-500 p-[1px] shadow-lg shadow-indigo-500/30">
            <div class="w-full h-full bg-slate-950 rounded-[11px] flex items-center justify-center">
              <Sparkles class="w-4 h-4 text-indigo-400" />
            </div>
          </div>
          <div>
            <div class="flex items-center space-x-2">
              <h1 class="font-extrabold text-sm sm:text-base bg-gradient-to-r from-slate-100 via-indigo-200 to-purple-300 bg-clip-text text-transparent tracking-tight">
                RepoPilot
              </h1>
              <span class="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                v0.1.0
              </span>
            </div>
            <p class="text-[9px] sm:text-[10px] text-slate-400 font-mono hidden sm:block">Autonomous Codebase Modernization Cockpit</p>
          </div>
        </div>

        <div class="h-5 w-px bg-slate-800 hidden md:block"></div>

        <!-- Migration Scenario Switcher -->
        <div class="flex items-center space-x-1.5 bg-slate-950/80 p-1 border border-slate-800 rounded-lg text-xs font-mono">
          <span class="text-slate-500 text-[10px] uppercase font-bold px-1.5 hidden lg:inline">Scenario:</span>
          <button
            @click="switchPreset('httpx')"
            :class="selectedPreset === 'httpx' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'"
            class="px-2.5 py-1 rounded text-[11px] transition-all"
            title="Async HTTPX Modernization with Self-Healing Loop"
          >
            Async HTTPX
          </button>
          <button
            @click="switchPreset('pydantic')"
            :class="selectedPreset === 'pydantic' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'"
            class="px-2.5 py-1 rounded text-[11px] transition-all"
            title="Pydantic v1 to v2 Model Dump Modernization"
          >
            Pydantic v2
          </button>
          <button
            @click="switchPreset('fastapi')"
            :class="selectedPreset === 'fastapi' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'"
            class="px-2.5 py-1 rounded text-[11px] transition-all"
            title="FastAPI Lifespan & Async Engine Modernization"
          >
            FastAPI Lifespan
          </button>
        </div>

        <!-- Quick Task ID Input -->
        <div class="hidden xl:flex items-center space-x-1.5 bg-slate-950/80 px-2.5 py-1 border border-slate-800 rounded-lg text-xs font-mono">
          <span class="text-slate-500 text-[10px]">Task:</span>
          <input
            v-model="inputTaskId"
            @keyup.enter="inputTaskId.trim() && loadTask(inputTaskId.trim())"
            placeholder="e.g. 76704270c8b2"
            class="w-28 bg-transparent text-slate-300 placeholder:text-slate-600 focus:outline-none text-[11px]"
          />
          <button
            @click="inputTaskId.trim() && loadTask(inputTaskId.trim())"
            class="px-2 py-0.5 rounded bg-indigo-600/40 hover:bg-indigo-600/60 text-[10px] text-indigo-300 font-semibold transition"
          >
            Load
          </button>
        </div>
      </div>

      <!-- Right: Status Badges & Controls -->
      <div class="flex items-center space-x-2.5">
        <!-- New Custom Migration Button -->
        <button
          @click="showNewMigrationModal = true"
          class="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/25 transition"
        >
          <PlusCircle class="w-3.5 h-3.5" />
          <span>New Migration</span>
        </button>

        <!-- Simulation Button -->
        <button
          @click="simulateSelfHeal"
          class="hidden sm:flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg border border-indigo-500/30 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 text-xs font-mono transition-all"
          title="Trigger a self-healing reflection cycle"
        >
          <RefreshCw class="w-3.5 h-3.5" />
          <span>Simulate Loop</span>
        </button>

        <!-- Phase Badge -->
        <div class="flex items-center space-x-2 px-3 py-1 rounded-full border text-xs font-mono"
          :class="{
            'bg-amber-500/10 border-amber-500/30 text-amber-300': state.phase === 'human_review' || state.phase === 'reflecting',
            'bg-emerald-500/10 border-emerald-500/30 text-emerald-300': state.phase === 'verified',
            'bg-rose-500/10 border-rose-500/30 text-rose-300': state.phase === 'failed' || state.phase === 'escalated',
            'bg-indigo-500/10 border-indigo-500/30 text-indigo-300': state.phase === 'synthesizing' || state.phase === 'planning' || state.phase === 'sandbox_testing',
          }"
        >
          <span
            :class="{
              'bg-amber-400 animate-ping': state.phase === 'human_review',
              'bg-emerald-400': state.phase === 'verified',
              'bg-rose-400': state.phase === 'failed' || state.phase === 'escalated',
              'bg-indigo-400 animate-pulse': state.phase === 'synthesizing' || state.phase === 'planning' || state.phase === 'sandbox_testing',
            }"
            class="w-2 h-2 rounded-full"
          ></span>
          <span class="capitalize text-[11px] font-semibold">{{ state.phase.replace('_', ' ') }}</span>
        </div>

        <!-- Backend Settings Popover -->
        <button
          @click="showSettingsModal = true"
          class="p-2 rounded-lg border border-slate-800 bg-slate-850 hover:bg-slate-800 text-slate-400 hover:text-white transition"
          title="Backend Connection Settings"
        >
          <Settings class="w-4 h-4" />
        </button>

        <!-- GitHub Link -->
        <a
          href="https://github.com/anmolvishvas/RepoPilot"
          target="_blank"
          rel="noopener"
          class="p-2 rounded-lg bg-slate-850 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-white transition-colors"
          title="View on GitHub"
        >
          <ExternalLink class="w-4 h-4" />
        </a>
      </div>
    </header>

    <!-- Context Mission Ribbon -->
    <div class="relative z-10 px-6 py-2 bg-slate-900/40 border-b border-slate-850/80 backdrop-blur-md flex items-center justify-between text-xs">
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
          <Cpu class="w-3.5 h-3.5" :class="backendStatus === 'connected' ? 'text-emerald-400' : 'text-slate-400'" />
          <span>{{ backendStatus === 'connected' ? 'Live API Connected' : 'Interactive Playground' }}</span>
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

    <!-- Modal: Launch New Custom Migration -->
    <div
      v-if="showNewMigrationModal"
      class="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
    >
      <div class="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 shadow-2xl space-y-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-800">
          <div class="flex items-center space-x-2">
            <Sparkles class="w-5 h-5 text-indigo-400" />
            <h3 class="font-bold text-sm text-slate-100">Launch Custom Autonomous Migration</h3>
          </div>
          <button @click="showNewMigrationModal = false" class="text-slate-400 hover:text-white">
            <X class="w-4 h-4" />
          </button>
        </div>

        <div class="space-y-3.5 text-xs">
          <div>
            <div class="flex items-center justify-between mb-1">
              <label class="block font-semibold text-slate-300">Target Repository Path / Name</label>
              <div class="flex items-center space-x-2 text-[10px] font-mono">
                <button
                  type="button"
                  @click="newRepoPath = 'https://github.com/tiangolo/fastapi'"
                  class="text-indigo-400 hover:text-indigo-300 transition"
                >
                  FastAPI
                </button>
                <span class="text-slate-700">•</span>
                <button
                  type="button"
                  @click="newRepoPath = 'https://github.com/encode/httpx'"
                  class="text-indigo-400 hover:text-indigo-300 transition"
                >
                  HTTPX
                </button>
                <span class="text-slate-700">•</span>
                <button
                  type="button"
                  @click="newRepoPath = 'https://github.com/pydantic/pydantic'"
                  class="text-indigo-400 hover:text-indigo-300 transition"
                >
                  Pydantic
                </button>
              </div>
            </div>
            <input
              v-model="newRepoPath"
              type="text"
              placeholder="e.g. /workspace/enterprise-app or https://github.com/myorg/myapp"
              class="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg font-mono text-slate-200 focus:outline-none focus:border-indigo-500"
            />
            <p class="text-[10px] text-slate-500 font-mono mt-1">Local path, cloned directory, or remote GitHub repository URL.</p>
          </div>

          <div>
            <label class="block font-semibold text-slate-300 mb-1">Modernization Recipe</label>
            <select
              v-model="newRecipe"
              class="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:border-indigo-500 font-sans"
            >
              <option value="sync-to-async">sync-to-async (Convert sync functions and callers to non-blocking async coroutines)</option>
              <option value="pydantic-v1-to-v2">pydantic-v1-to-v2 (Migrate deprecated .dict()/.parse_obj() to model_dump())</option>
              <option value="fastapi-v0.111-upgrade">fastapi-upgrade (Upgrade lifespan context managers and dependency syntax)</option>
              <option value="type-annotations">type-annotations (Synthesize strict typing stubs and parameter hints)</option>
              <option value="unittest-to-pytest">unittest-to-pytest (Modernize legacy test suites to pytest fixtures)</option>
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

        <div class="pt-3 border-t border-slate-800 flex items-center justify-between">
          <span class="text-[11px] text-slate-400 font-mono">
            Mode: <strong class="text-indigo-400">{{ backendStatus === 'connected' ? 'Live Backend API' : 'Interactive Playground' }}</strong>
          </span>
          <div class="flex items-center space-x-2.5">
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

    <!-- Modal: Backend Connection Settings -->
    <div
      v-if="showSettingsModal"
      class="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
    >
      <div class="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 shadow-2xl space-y-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-800">
          <div class="flex items-center space-x-2">
            <Settings class="w-5 h-5 text-indigo-400" />
            <h3 class="font-bold text-sm text-slate-100">Backend Connection Settings</h3>
          </div>
          <button @click="showSettingsModal = false" class="text-slate-400 hover:text-white">
            <X class="w-4 h-4" />
          </button>
        </div>

        <div class="space-y-3 text-xs">
          <div>
            <div class="flex items-center justify-between mb-1">
              <label class="block font-semibold text-slate-300">RepoPilot Backend URL</label>
              <div class="flex items-center space-x-2 text-[10px] font-mono">
                <button
                  type="button"
                  @click="apiBase = 'http://localhost:8080'"
                  class="text-indigo-400 hover:text-indigo-300"
                >
                  Local 8080
                </button>
                <span class="text-slate-700">•</span>
                <button
                  type="button"
                  @click="apiBase = ''"
                  class="text-indigo-400 hover:text-indigo-300"
                >
                  Standalone
                </button>
              </div>
            </div>
            <input
              v-model="apiBase"
              type="text"
              placeholder="e.g. http://localhost:8080 or https://repopilot.onrender.com"
              class="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg font-mono text-slate-200 focus:outline-none focus:border-indigo-500"
            />
            <p class="text-[10px] text-slate-500 font-mono mt-1">
              Leave empty for standalone playground mode, or enter your local/tunnel/cloud URL. Note: HTTPS domains (like Vercel) require an HTTPS backend URL (e.g. ngrok or cloud host) to prevent browser mixed-content blocks.
            </p>
          </div>

          <div>
            <label class="block font-semibold text-slate-300 mb-1">Load Specific Task ID</label>
            <div class="flex items-center space-x-2">
              <input
                v-model="inputTaskId"
                type="text"
                placeholder="e.g. 76704270c8b2"
                class="flex-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg font-mono text-slate-200 focus:outline-none focus:border-indigo-500"
              />
              <button
                @click="loadTask(inputTaskId); showSettingsModal = false"
                class="px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-bold transition text-xs"
              >
                Fetch
              </button>
            </div>
          </div>
        </div>

        <div class="pt-3 border-t border-slate-800 flex justify-end">
          <button
            @click="showSettingsModal = false; showToast('Settings updated', 'success')"
            class="px-4 py-2 rounded-lg bg-slate-850 hover:bg-slate-800 text-white text-xs font-semibold"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
