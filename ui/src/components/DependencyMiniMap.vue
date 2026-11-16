<script setup lang="ts">
defineProps<{
  affectedFiles: string[];
  activeFile?: string;
}>();

const emit = defineEmits<{
  (e: "selectFile", file: string): void;
}>();
</script>

<template>
  <div class="flex flex-col h-full bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
    <div class="px-4 py-3 bg-slate-850 border-b border-slate-800 flex items-center justify-between">
      <h3 class="font-semibold text-sm text-slate-200">AST Symbol Blast Radius & Mini-Map</h3>
      <span class="text-xs text-slate-400">{{ affectedFiles.length }} nodes</span>
    </div>

    <div class="flex-1 p-4 overflow-y-auto">
      <div v-if="affectedFiles.length === 0" class="flex items-center justify-center h-full text-slate-500 text-xs">
        No symbol dependencies analyzed yet.
      </div>

      <div v-else class="space-y-4">
        <!-- SVG Node-Link Diagram Representation -->
        <div class="bg-slate-950 border border-slate-800 rounded-lg p-3">
          <svg class="w-full h-44" viewBox="0 0 300 150">
            <!-- Connecting lines -->
            <line
              v-for="(_, idx) in affectedFiles.slice(1)"
              :key="'line-' + idx"
              :x1="50 + idx * 70"
              y1="75"
              :x2="120 + idx * 70"
              y2="75"
              stroke="#334155"
              stroke-width="2"
              stroke-dasharray="4"
            />
            <!-- Graph Nodes -->
            <g
              v-for="(file, idx) in affectedFiles.slice(0, 4)"
              :key="'node-' + idx"
              class="cursor-pointer group"
              @click="emit('selectFile', file)"
            >
              <circle
                :cx="50 + idx * 70"
                cy="75"
                r="18"
                :fill="activeFile === file ? '#6366f1' : '#1e293b'"
                :stroke="activeFile === file ? '#818cf8' : '#475569'"
                stroke-width="2"
                class="transition group-hover:stroke-indigo-400"
              />
              <text
                :x="50 + idx * 70"
                y="80"
                text-anchor="middle"
                fill="#f8fafc"
                font-size="11"
                font-family="monospace"
              >
                {{ idx + 1 }}
              </text>
              <text
                :x="50 + idx * 70"
                y="115"
                text-anchor="middle"
                fill="#94a3b8"
                font-size="9"
                font-family="monospace"
              >
                {{ file.split('/').pop()?.slice(0, 9) }}
              </text>
            </g>
          </svg>
        </div>

        <!-- Dependency List -->
        <div class="space-y-1.5">
          <div
            v-for="(f, idx) in affectedFiles"
            :key="idx"
            @click="emit('selectFile', f)"
            class="px-2.5 py-1.5 bg-slate-950 hover:bg-slate-850 border border-slate-800 rounded text-xs font-mono flex items-center justify-between cursor-pointer transition"
          >
            <div class="flex items-center space-x-2 truncate">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              <span class="text-slate-300 truncate">{{ f }}</span>
            </div>
            <span class="text-[10px] text-slate-500 font-sans">Rank #{{ idx + 1 }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
