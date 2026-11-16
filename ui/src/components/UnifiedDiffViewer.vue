<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { DiffHunk } from "../types";
import { FileCode2, CheckCircle2, XCircle, Sparkles, GitCommit, Search } from "lucide-vue-next";

const props = defineProps<{
  patches: DiffHunk[];
  isHumanReview: boolean;
  activeFile?: string;
}>();

const emit = defineEmits<{
  (e: "approve"): void;
  (e: "reject", reason: string): void;
  (e: "selectFile", file: string): void;
}>();

const selectedPatchIndex = ref(0);
const patchSearch = ref("");

// Filter patches based on search input
const filteredPatches = computed(() => {
  if (!patchSearch.value.trim()) return props.patches;
  const q = patchSearch.value.toLowerCase();
  return props.patches.filter((p) => p.file_path.toLowerCase().includes(q));
});

// Sync with activeFile if passed from parent
watch(
  () => props.activeFile,
  (newFile) => {
    if (!newFile) return;
    const foundIdx = props.patches.findIndex((p) => p.file_path === newFile);
    if (foundIdx !== -1) {
      selectedPatchIndex.value = foundIdx;
    }
  }
);

const activePatch = computed(() => props.patches[selectedPatchIndex.value] || props.patches[0]);

interface DiffLine {
  type: "header" | "add" | "del" | "ctx";
  text: string;
  oldNum?: number | string;
  newNum?: number | string;
}

const parsedLines = computed<DiffLine[]>(() => {
  if (!activePatch.value) return [];
  const rawLines = activePatch.value.diff_text.split("\n");
  const result: DiffLine[] = [];
  let oldLine = 1;
  let newLine = 1;

  for (const line of rawLines) {
    if (line.startsWith("@@")) {
      const match = line.match(/@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
      if (match) {
        oldLine = parseInt(match[1], 10);
        newLine = parseInt(match[2], 10);
      }
      result.push({ type: "header", text: line, oldNum: "...", newNum: "..." });
    } else if (line.startsWith("---") || line.startsWith("+++")) {
      result.push({ type: "header", text: line, oldNum: "", newNum: "" });
    } else if (line.startsWith("+")) {
      result.push({ type: "add", text: line.substring(1), oldNum: "", newNum: newLine++ });
    } else if (line.startsWith("-")) {
      result.push({ type: "del", text: line.substring(1), oldNum: oldLine++, newNum: "" });
    } else {
      const text = line.startsWith(" ") ? line.substring(1) : line;
      result.push({ type: "ctx", text, oldNum: oldLine++, newNum: newLine++ });
    }
  }
  return result;
});

const stats = computed(() => {
  if (!activePatch.value) return { adds: 0, dels: 0 };
  const raw = activePatch.value.diff_text.split("\n");
  const adds = raw.filter((l) => l.startsWith("+") && !l.startsWith("+++")).length;
  const dels = raw.filter((l) => l.startsWith("-") && !l.startsWith("---")).length;
  return { adds, dels };
});
</script>

<template>
  <div class="flex flex-col h-full bg-slate-900/90 backdrop-blur-xl border border-slate-800/80 rounded-xl overflow-hidden shadow-2xl shadow-black/40">
    <!-- Top Header -->
    <div class="px-4 py-3 bg-gradient-to-r from-slate-900 to-slate-850 border-b border-slate-800/80 flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <div class="p-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
          <FileCode2 class="w-4 h-4" />
        </div>
        <div>
          <h3 class="font-semibold text-xs text-slate-100 uppercase tracking-wider">Unified Patch Diff</h3>
          <p class="text-[10px] text-slate-400 font-mono">
            Showing patch {{ selectedPatchIndex + 1 }} of {{ patches.length }}
          </p>
        </div>
      </div>

      <div class="flex items-center space-x-2">
        <span class="px-2 py-0.5 rounded text-[11px] font-mono bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
          +{{ stats.adds }}
        </span>
        <span class="px-2 py-0.5 rounded text-[11px] font-mono bg-rose-500/10 text-rose-300 border border-rose-500/20">
          -{{ stats.dels }}
        </span>
      </div>
    </div>

    <!-- Search & Multi-File Tabs Strip -->
    <div class="bg-slate-950 border-b border-slate-800/80 p-2 flex items-center space-x-2 overflow-hidden">
      <div class="relative w-44 shrink-0">
        <Search class="w-3.5 h-3.5 text-slate-500 absolute left-2 top-2" />
        <input
          v-model="patchSearch"
          type="text"
          placeholder="Search patches..."
          class="w-full pl-7 pr-2 py-1 bg-slate-900 border border-slate-800 rounded text-xs font-mono text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500/40"
        />
      </div>

      <!-- Scrollable Tab Strip -->
      <div class="flex items-center space-x-1.5 overflow-x-auto flex-1 py-0.5">
        <button
          v-for="(p, idx) in filteredPatches.slice(0, 30)"
          :key="idx"
          @click="selectedPatchIndex = patches.indexOf(p); emit('selectFile', p.file_path)"
          :class="patches[selectedPatchIndex]?.file_path === p.file_path
            ? 'bg-slate-850 text-indigo-300 border-indigo-500/40 shadow-sm'
            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900 border-transparent'"
          class="px-2.5 py-1 rounded-lg border text-xs font-mono flex items-center space-x-1.5 shrink-0 transition-all duration-150"
        >
          <span class="w-1.5 h-1.5 rounded-full" :class="patches[selectedPatchIndex]?.file_path === p.file_path ? 'bg-indigo-400' : 'bg-slate-600'"></span>
          <span class="truncate max-w-[140px]">{{ p.file_path.split('/').pop() }}</span>
        </button>

        <span v-if="filteredPatches.length > 30" class="text-[10px] text-slate-500 font-mono px-2 shrink-0">
          +{{ filteredPatches.length - 30 }} more
        </span>
      </div>
    </div>

    <!-- Main Diff Body -->
    <div v-if="patches.length === 0" class="flex-1 flex flex-col items-center justify-center text-slate-500 p-8 space-y-2">
      <GitCommit class="w-8 h-8 text-slate-600 animate-pulse" />
      <p class="text-xs font-mono">No patch diffs synthesized yet for this task.</p>
    </div>

    <div v-else class="flex-1 flex flex-col overflow-hidden">
      <!-- Rationale Callout Card -->
      <div v-if="activePatch?.explanation" class="mx-4 mt-3 p-3 rounded-lg bg-gradient-to-r from-indigo-950/40 to-purple-950/30 border border-indigo-500/20 flex items-start space-x-3">
        <Sparkles class="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
        <div class="text-xs">
          <span class="font-semibold text-indigo-300">AST Modernization Rationale:</span>
          <span class="text-slate-300 ml-1 leading-relaxed">{{ activePatch.explanation }}</span>
          <div class="mt-1 flex items-center space-x-2 text-[11px] font-mono text-slate-400">
            <span class="text-slate-500">File:</span>
            <code class="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-indigo-300">{{ activePatch.file_path }}</code>
          </div>
        </div>
      </div>

      <!-- Diff Code View -->
      <div class="flex-1 overflow-y-auto mt-3 p-3 font-mono text-xs bg-slate-950/70 select-text leading-relaxed">
        <div class="border border-slate-850 rounded-lg overflow-hidden bg-slate-950">
          <table class="w-full border-collapse">
            <tbody>
              <tr
                v-for="(line, idx) in parsedLines"
                :key="idx"
                :class="{
                  'bg-emerald-950/40 text-emerald-200 border-l-2 border-emerald-500': line.type === 'add',
                  'bg-rose-950/40 text-rose-200 border-l-2 border-rose-500': line.type === 'del',
                  'bg-indigo-950/20 text-indigo-400 font-semibold border-l-2 border-indigo-500/40': line.type === 'header',
                  'text-slate-300 hover:bg-slate-900/60': line.type === 'ctx',
                }"
                class="transition-colors group"
              >
                <!-- Line Numbers -->
                <td class="w-10 py-0.5 px-2 text-right text-[10px] text-slate-600 select-none border-r border-slate-900 font-mono">
                  {{ line.oldNum }}
                </td>
                <td class="w-10 py-0.5 px-2 text-right text-[10px] text-slate-600 select-none border-r border-slate-900 font-mono">
                  {{ line.newNum }}
                </td>
                <!-- Marker -->
                <td class="w-4 py-0.5 pl-2 select-none text-center font-bold font-mono">
                  <span v-if="line.type === 'add'" class="text-emerald-400">+</span>
                  <span v-else-if="line.type === 'del'" class="text-rose-400">-</span>
                  <span v-else-if="line.type === 'header'" class="text-indigo-400">@</span>
                </td>
                <!-- Code Text -->
                <td class="py-0.5 pl-2 pr-4 font-mono whitespace-pre overflow-x-auto text-xs">
                  {{ line.text }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Sticky Operator Review Dock -->
      <div v-if="isHumanReview" class="p-3 bg-gradient-to-t from-slate-950 to-slate-900/90 border-t border-slate-800/80 flex items-center justify-between">
        <div class="flex items-center space-x-2 text-xs">
          <span class="w-2 h-2 rounded-full bg-amber-400 animate-ping"></span>
          <span class="font-medium text-amber-300 font-mono">Awaiting Human Sign-off</span>
        </div>

        <div class="flex items-center space-x-3">
          <button
            @click="emit('reject', 'Rejected by operator: manual review requested revision')"
            class="px-4 py-1.5 rounded-lg border border-rose-500/30 bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 text-xs font-semibold flex items-center space-x-1.5 transition-all shadow-sm"
          >
            <XCircle class="w-3.5 h-3.5" />
            <span>Reject & Remediate</span>
          </button>

          <button
            @click="emit('approve')"
            class="px-5 py-1.5 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 text-xs font-bold flex items-center space-x-1.5 transition-all shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/30"
          >
            <CheckCircle2 class="w-4 h-4 text-slate-950" />
            <span>Approve & Land Patches</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
