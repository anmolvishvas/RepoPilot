<script setup lang="ts">
import { ref } from "vue";
import type { ToolTrace } from "../types";

defineProps<{
  traces: ToolTrace[];
  phase: string;
  retryCount: number;
  maxRetries: number;
}>();

const expandedIndices = ref<Set<number>>(new Set());

function toggle(idx: number) {
  if (expandedIndices.value.has(idx)) {
    expandedIndices.value.delete(idx);
  } else {
    expandedIndices.value.add(idx);
  }
}
</script>

<template>
  <div class="flex flex-col h-full bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
    <div class="px-4 py-3 bg-slate-850 border-b border-slate-800 flex items-center justify-between">
      <div class="flex items-center space-x-2">
        <span class="w-2.5 h-2.5 rounded-full bg-indigo-500 animate-pulse"></span>
        <h3 class="font-semibold text-sm text-slate-200">Execution Trace & Agent Thought Stream</h3>
      </div>
      <div class="flex items-center space-x-2 text-xs text-slate-400">
        <span>Cycle: {{ retryCount }} / {{ maxRetries }}</span>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto p-4 space-y-3 font-mono text-xs">
      <div v-if="traces.length === 0" class="text-slate-500 text-center py-12">
        Awaiting agent execution events...
      </div>

      <div
        v-for="(trace, idx) in traces"
        :key="idx"
        class="border border-slate-800 rounded bg-slate-950 overflow-hidden"
      >
        <div
          @click="toggle(idx)"
          class="px-3 py-2 flex items-center justify-between cursor-pointer hover:bg-slate-850 select-none transition-colors"
        >
          <div class="flex items-center space-x-2">
            <span
              :class="trace.success ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40' : 'bg-rose-500/20 text-rose-400 border-rose-500/40'"
              class="px-1.5 py-0.5 text-[10px] uppercase font-bold rounded border"
            >
              {{ trace.success ? 'PASS' : 'FAIL' }}
            </span>
            <span class="text-slate-200 font-semibold">{{ trace.tool_name }}</span>
          </div>
          <div class="flex items-center space-x-3 text-slate-400 text-[11px]">
            <span>{{ trace.execution_time_ms.toFixed(1) }}ms</span>
            <span class="text-slate-600">{{ expandedIndices.has(idx) ? '▼' : '▶' }}</span>
          </div>
        </div>

        <div v-if="expandedIndices.has(idx)" class="px-3 py-2.5 border-t border-slate-850 bg-slate-900/60 text-slate-300 space-y-2">
          <p class="text-slate-400 italic">{{ trace.output_summary }}</p>
          <div v-if="Object.keys(trace.args).length > 0" class="bg-slate-950 p-2 rounded text-[11px] overflow-x-auto">
            <span class="text-slate-500">Arguments:</span>
            <pre class="text-indigo-300 mt-1">{{ JSON.stringify(trace.args, null, 2) }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
