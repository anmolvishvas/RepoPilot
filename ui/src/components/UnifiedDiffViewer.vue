<script setup lang="ts">
import { computed, ref } from "vue";
import type { DiffHunk } from "../types";

const props = defineProps<{
  patches: DiffHunk[];
  isHumanReview: boolean;
}>();

const emit = defineEmits<{
  (e: "approve"): void;
  (e: "reject", reason: string): void;
}>();

const selectedPatchIndex = ref(0);
const activePatch = computed(() => props.patches[selectedPatchIndex.value]);

interface DiffLine {
  type: "header" | "add" | "del" | "ctx";
  text: string;
}

const parsedLines = computed<DiffLine[]>(() => {
  if (!activePatch.value) return [];
  return activePatch.value.diff_text.split("\n").map((line) => {
    if (line.startsWith("@@") || line.startsWith("---") || line.startsWith("+++")) {
      return { type: "header", text: line };
    } else if (line.startsWith("+")) {
      return { type: "add", text: line };
    } else if (line.startsWith("-")) {
      return { type: "del", text: line };
    }
    return { type: "ctx", text: line };
  });
});
</script>

<template>
  <div class="flex flex-col h-full bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
    <div class="px-4 py-3 bg-slate-850 border-b border-slate-800 flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <h3 class="font-semibold text-sm text-slate-200">Interactive Unified Diff Viewer</h3>
        <span v-if="patches.length > 0" class="px-2 py-0.5 text-xs bg-indigo-500/20 text-indigo-300 rounded-full border border-indigo-500/30">
          {{ patches.length }} patch{{ patches.length > 1 ? 'es' : '' }}
        </span>
      </div>

      <div v-if="isHumanReview" class="flex items-center space-x-2">
        <button
          @click="emit('reject', 'Rejected by operator')"
          class="px-3 py-1 bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 rounded text-xs font-semibold transition"
        >
          Reject
        </button>
        <button
          @click="emit('approve')"
          class="px-3 py-1 bg-emerald-500 hover:bg-emerald-600 text-slate-950 rounded text-xs font-semibold transition shadow-sm"
        >
          Approve & Land
        </button>
      </div>
    </div>

    <div v-if="patches.length === 0" class="flex-1 flex items-center justify-center text-slate-500 text-xs">
      No patches generated yet.
    </div>

    <div v-else class="flex flex-1 overflow-hidden">
      <!-- File Selector Sidebar -->
      <div class="w-64 border-r border-slate-800 bg-slate-950 overflow-y-auto p-2 space-y-1">
        <button
          v-for="(p, idx) in patches"
          :key="idx"
          @click="selectedPatchIndex = idx"
          :class="selectedPatchIndex === idx ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:bg-slate-850 hover:text-slate-200'"
          class="w-full text-left px-2.5 py-1.5 rounded text-xs font-mono truncate transition"
        >
          {{ p.file_path }}
        </button>
      </div>

      <!-- Diff Content -->
      <div class="flex-1 overflow-y-auto p-4 font-mono text-xs bg-slate-950 leading-relaxed">
        <div v-if="activePatch?.explanation" class="mb-4 p-2.5 bg-slate-900 border border-slate-800 rounded text-slate-400 font-sans text-xs">
          <span class="text-indigo-400 font-semibold">AST Modernization Rationale:</span> {{ activePatch.explanation }}
        </div>

        <div class="space-y-0.5">
          <div
            v-for="(line, idx) in parsedLines"
            :key="idx"
            :class="{
              'bg-emerald-950/40 text-emerald-300': line.type === 'add',
              'bg-rose-950/40 text-rose-300': line.type === 'del',
              'text-indigo-400 font-semibold bg-indigo-950/20': line.type === 'header',
              'text-slate-400': line.type === 'ctx',
            }"
            class="px-2 py-0.5 rounded-sm whitespace-pre"
          >
            {{ line.text }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
