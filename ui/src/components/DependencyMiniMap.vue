<script setup lang="ts">
import { computed, ref } from "vue";
import { Network, ArrowUpRight, Search } from "lucide-vue-next";

const props = defineProps<{
  affectedFiles: string[];
  activeFile?: string;
}>();

const emit = defineEmits<{
  (e: "selectFile", file: string): void;
}>();

const searchQuery = ref("");

// Show up to 5 representative nodes in the visual SVG map
const graphNodes = computed(() => {
  const sample = props.affectedFiles.slice(0, 5);
  return sample.map((file, idx) => {
    const fileName = file.split("/").pop() || file;
    const isPrimary = idx === 0;
    const x = 35 + idx * 52;
    const y = idx % 2 === 0 ? 55 : 85;
    return {
      file,
      fileName,
      isPrimary,
      x,
      y,
      radius: isPrimary ? 16 : 14,
      rank: idx + 1,
    };
  });
});

const filteredFiles = computed(() => {
  if (!searchQuery.value.trim()) {
    return props.affectedFiles.slice(0, 50); // Show first 50 for smooth performance
  }
  const q = searchQuery.value.toLowerCase();
  return props.affectedFiles.filter((f) => f.toLowerCase().includes(q)).slice(0, 50);
});
</script>

<template>
  <div class="flex flex-col h-full bg-slate-900/90 backdrop-blur-xl border border-slate-800/80 rounded-xl overflow-hidden shadow-2xl shadow-black/40">
    <!-- Header -->
    <div class="px-4 py-3 bg-gradient-to-r from-slate-900 to-slate-850 border-b border-slate-800/80 flex items-center justify-between">
      <div class="flex items-center space-x-2.5">
        <div class="p-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
          <Network class="w-4 h-4" />
        </div>
        <div>
          <h3 class="font-semibold text-xs text-slate-100 uppercase tracking-wider">AST Blast Radius</h3>
          <p class="text-[10px] text-slate-400 font-mono">Dependency Impact Graph</p>
        </div>
      </div>
      <span class="px-2 py-0.5 rounded-full text-[11px] font-mono bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
        {{ affectedFiles.length }} files
      </span>
    </div>

    <div class="flex-1 p-3.5 overflow-y-auto space-y-3.5">
      <!-- SVG Graph Canvas -->
      <div class="relative bg-slate-950/80 border border-slate-800/80 rounded-xl p-3 overflow-hidden shadow-inner">
        <svg class="w-full h-36" viewBox="0 0 260 130">
          <defs>
            <pattern id="miniGrid" width="12" height="12" patternUnits="userSpaceOnUse">
              <path d="M 12 0 L 0 0 0 12" fill="none" stroke="#1e293b" stroke-width="0.5" />
            </pattern>
            <linearGradient id="edgeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="#6366f1" stop-opacity="0.8" />
              <stop offset="100%" stop-color="#a855f7" stop-opacity="0.8" />
            </linearGradient>
            <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="2" result="glow" />
              <feComposite in="SourceGraphic" in2="glow" operator="over" />
            </filter>
          </defs>

          <!-- Grid surface -->
          <rect width="100%" height="100%" fill="url(#miniGrid)" opacity="0.6" />

          <!-- Connecting Curved Lines -->
          <g v-for="i in Math.max(0, graphNodes.length - 1)" :key="'edge-' + i">
            <path
              v-if="graphNodes[i] && graphNodes[i + 1]"
              :d="`M ${graphNodes[i].x} ${graphNodes[i].y} C ${graphNodes[i].x + 25} ${graphNodes[i].y}, ${graphNodes[i + 1].x - 25} ${graphNodes[i + 1].y}, ${graphNodes[i + 1].x} ${graphNodes[i + 1].y}`"
              fill="none"
              stroke="url(#edgeGradient)"
              stroke-width="1.5"
              stroke-dasharray="3 2"
              class="animate-pulse"
            />
          </g>

          <!-- Graph Nodes -->
          <g
            v-for="node in graphNodes"
            :key="node.file"
            class="cursor-pointer group transition-all duration-300"
            @click="emit('selectFile', node.file)"
          >
            <!-- Glowing halo on active -->
            <circle
              v-if="activeFile === node.file"
              :cx="node.x"
              :cy="node.y"
              :r="node.radius + 4"
              fill="none"
              stroke="#818cf8"
              stroke-width="1.5"
              stroke-opacity="0.6"
              filter="url(#glow)"
            />

            <!-- Core Node Circle -->
            <circle
              :cx="node.x"
              :cy="node.y"
              :r="node.radius"
              :fill="activeFile === node.file ? '#4f46e5' : node.isPrimary ? '#1e1b4b' : '#0f172a'"
              :stroke="activeFile === node.file ? '#a5b4fc' : node.isPrimary ? '#6366f1' : '#334155'"
              stroke-width="1.5"
              class="transition-transform group-hover:scale-110 duration-150"
            />

            <!-- Node Rank Number -->
            <text
              :x="node.x"
              :y="node.y + 4"
              text-anchor="middle"
              fill="#ffffff"
              font-size="9.5"
              font-family="'JetBrains Mono', monospace"
              font-weight="bold"
            >
              {{ node.rank }}
            </text>

            <!-- File Name Label below Node -->
            <text
              :x="node.x"
              :y="node.y + node.radius + 12"
              text-anchor="middle"
              :fill="activeFile === node.file ? '#c7d2fe' : '#94a3b8'"
              font-size="8.5"
              font-family="'JetBrains Mono', monospace"
            >
              {{ node.fileName.slice(0, 8) }}
            </text>
          </g>
        </svg>

        <div class="mt-1 pt-1.5 border-t border-slate-900/60 flex items-center justify-between text-[10px] text-slate-500 font-mono">
          <span class="flex items-center space-x-1">
            <span class="w-1.5 h-1.5 rounded-full bg-indigo-500"></span>
            <span>Origin Leaf</span>
          </span>
          <span class="flex items-center space-x-1">
            <span class="w-1.5 h-1.5 rounded-full bg-purple-500"></span>
            <span>Upstream Caller</span>
          </span>
        </div>
      </div>

      <!-- Search & Filter Bar -->
      <div class="relative">
        <Search class="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
        <input
          v-model="searchQuery"
          type="text"
          :placeholder="`Filter ${affectedFiles.length} affected files...`"
          class="w-full pl-8 pr-3 py-1.5 bg-slate-950/80 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500/50"
        />
      </div>

      <!-- Affected Files List -->
      <div class="space-y-1.5 max-h-[300px] overflow-y-auto pr-1">
        <div
          v-for="(file, idx) in filteredFiles"
          :key="idx"
          @click="emit('selectFile', file)"
          :class="activeFile === file 
            ? 'bg-indigo-950/60 border-indigo-500/50 shadow-md shadow-indigo-500/10' 
            : 'bg-slate-950/60 hover:bg-slate-850/80 border-slate-800/80'"
          class="group p-2 border rounded-lg cursor-pointer transition-all duration-150 flex items-center justify-between"
        >
          <div class="flex items-center space-x-2 truncate">
            <div :class="idx === 0 ? 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30' : 'bg-slate-800 text-slate-400 border-slate-700'"
              class="w-4 h-4 rounded flex items-center justify-center text-[9px] font-mono font-bold border shrink-0">
              {{ idx + 1 }}
            </div>
            <div class="truncate">
              <p class="text-xs font-mono font-medium truncate" :class="activeFile === file ? 'text-indigo-200' : 'text-slate-200 group-hover:text-white'">
                {{ file.split('/').pop() }}
              </p>
              <p class="text-[9px] text-slate-500 font-mono truncate">{{ file }}</p>
            </div>
          </div>

          <div class="flex items-center space-x-1 shrink-0 ml-1.5">
            <ArrowUpRight class="w-3.5 h-3.5 text-slate-500 group-hover:text-indigo-400 transition-colors" />
          </div>
        </div>

        <div v-if="filteredFiles.length === 0" class="text-center py-6 text-slate-500 text-xs font-mono">
          No matching files found.
        </div>
      </div>
    </div>
  </div>
</template>
