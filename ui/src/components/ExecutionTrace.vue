<script setup lang="ts">
import { ref } from "vue";
import type { ToolTrace } from "../types";
import { Terminal, Clock, CheckCircle, XCircle, ChevronDown, ChevronRight, Cpu } from "lucide-vue-next";

defineProps<{
  traces: ToolTrace[];
  phase: string;
  retryCount: number;
  maxRetries: number;
}>();

const expandedIndices = ref<Set<number>>(new Set([0, 1, 2]));

function toggle(idx: number) {
  if (expandedIndices.value.has(idx)) {
    expandedIndices.value.delete(idx);
  } else {
    expandedIndices.value.add(idx);
  }
}
</script>

<template>
  <div class="flex flex-col h-full bg-slate-900/90 backdrop-blur-xl border border-slate-800/80 rounded-xl overflow-hidden shadow-2xl shadow-black/40">
    <!-- Terminal Titlebar -->
    <div class="px-4 py-3 bg-gradient-to-r from-slate-900 to-slate-850 border-b border-slate-800/80 flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <!-- Mac traffic light dots -->
        <div class="flex items-center space-x-1.5">
          <span class="w-2.5 h-2.5 rounded-full bg-rose-500/80"></span>
          <span class="w-2.5 h-2.5 rounded-full bg-amber-500/80"></span>
          <span class="w-2.5 h-2.5 rounded-full bg-emerald-500/80"></span>
        </div>
        <div class="h-3.5 w-px bg-slate-800"></div>
        <div class="flex items-center space-x-2">
          <Terminal class="w-4 h-4 text-indigo-400" />
          <h3 class="font-semibold text-xs text-slate-100 uppercase tracking-wider">Agent Thought Stream</h3>
        </div>
      </div>

      <div class="flex items-center space-x-2">
        <span class="flex items-center space-x-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
          <span>SSE LIVE</span>
        </span>
      </div>
    </div>

    <!-- Cycle Indicator Bar -->
    <div class="px-4 py-2 bg-slate-950/60 border-b border-slate-850 flex items-center justify-between text-xs font-mono">
      <span class="text-slate-400 flex items-center space-x-1.5">
        <Cpu class="w-3.5 h-3.5 text-indigo-400" />
        <span>Self-Healing Loop</span>
      </span>
      <div class="flex items-center space-x-2">
        <span class="text-slate-500 text-[11px]">Iteration</span>
        <span class="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-bold border border-indigo-500/30 text-[11px]">
          {{ retryCount }} / {{ maxRetries }}
        </span>
      </div>
    </div>

    <!-- Timeline Trace Stream -->
    <div class="flex-1 overflow-y-auto p-4 space-y-3 font-mono text-xs">
      <div v-if="traces.length === 0" class="text-slate-500 text-center py-12 flex flex-col items-center space-y-2">
        <Clock class="w-8 h-8 text-slate-700 animate-spin" />
        <p class="text-xs font-mono">Awaiting LangGraph execution events...</p>
      </div>

      <div
        v-for="(trace, idx) in traces"
        :key="idx"
        class="group border border-slate-800/80 rounded-xl bg-slate-950/80 overflow-hidden transition-all duration-200 hover:border-slate-700"
      >
        <!-- Card Header -->
        <div
          @click="toggle(idx)"
          class="px-3.5 py-2.5 flex items-center justify-between cursor-pointer hover:bg-slate-850/60 select-none transition-colors"
        >
          <div class="flex items-center space-x-2.5">
            <span
              :class="trace.success
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                : 'bg-rose-500/10 text-rose-400 border-rose-500/30'"
              class="px-1.5 py-0.5 text-[9px] uppercase font-bold rounded border tracking-wider flex items-center space-x-1"
            >
              <CheckCircle v-if="trace.success" class="w-2.5 h-2.5" />
              <XCircle v-else class="w-2.5 h-2.5" />
              <span>{{ trace.success ? 'PASS' : 'FAIL' }}</span>
            </span>

            <span class="text-slate-200 font-semibold text-xs tracking-tight">
              {{ trace.tool_name }}
            </span>
          </div>

          <div class="flex items-center space-x-3 text-slate-400 text-[11px]">
            <span class="flex items-center space-x-1 text-slate-500">
              <Clock class="w-3 h-3 text-slate-600" />
              <span>{{ trace.execution_time_ms.toFixed(1) }}ms</span>
            </span>
            <component
              :is="expandedIndices.has(idx) ? ChevronDown : ChevronRight"
              class="w-3.5 h-3.5 text-slate-500 transition-transform"
            />
          </div>
        </div>

        <!-- Expanded Drawer -->
        <div
          v-if="expandedIndices.has(idx)"
          class="px-3.5 py-3 border-t border-slate-855 bg-slate-900/40 text-slate-300 space-y-2.5 text-xs"
        >
          <div class="flex items-start space-x-2">
            <span class="text-indigo-400 mt-0.5">↳</span>
            <p class="text-slate-300 leading-relaxed font-sans text-xs">{{ trace.output_summary }}</p>
          </div>

          <div v-if="Object.keys(trace.args).length > 0" class="bg-slate-950 p-2.5 rounded-lg border border-slate-850 text-[11px] overflow-x-auto">
            <span class="text-slate-500 font-mono block text-[10px] uppercase tracking-wider mb-1">State Payload:</span>
            <pre class="text-indigo-300 font-mono leading-relaxed">{{ JSON.stringify(trace.args, null, 2) }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
