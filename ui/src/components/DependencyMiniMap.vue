<script setup lang="ts">
import { computed } from "vue";
import { Network, Layers, ArrowUpRight } from "lucide-vue-next";

const props = defineProps<{
  affectedFiles: string[];
  activeFile?: string;
}>();

const emit = defineEmits<{
  (e: "selectFile", file: string): void;
}>();

const nodes = computed(() => {
  return props.affectedFiles.map((file, idx) => {
    const fileName = file.split("/").pop() || file;
    const isPrimary = idx === 0;
    // Calculate layout coordinates along a modern curved flow
    const x = 60 + idx * 105;
    const y = idx % 2 === 0 ? 65 : 95;
    return {
      file,
      fileName,
      isPrimary,
      x,
      y,
      radius: isPrimary ? 22 : 18,
      rank: idx + 1,
    };
  });
});
</script>

<template>
  <div class="flex flex-col h-full bg-slate-900/90 backdrop-blur-xl border border-slate-800/80 rounded-xl overflow-hidden shadow-2xl shadow-black/40">
    <!-- Header -->
    <div class="px-4 py-3.5 bg-gradient-to-r from-slate-900 to-slate-850 border-b border-slate-800/80 flex items-center justify-between">
      <div class="flex items-center space-x-2.5">
        <div class="p-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
          <Network class="w-4 h-4" />
        </div>
        <div>
          <h3 class="font-semibold text-xs text-slate-100 uppercase tracking-wider">AST Blast Radius</h3>
          <p class="text-[10px] text-slate-400 font-mono">Call-Graph Dependency Map</p>
        </div>
      </div>
      <span class="px-2 py-0.5 rounded-full text-[11px] font-mono bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
        {{ affectedFiles.length }} affected
      </span>
    </div>

    <div class="flex-1 p-4 overflow-y-auto space-y-4">
      <!-- SVG Graph Canvas -->
      <div class="relative bg-slate-950/80 border border-slate-800/80 rounded-xl p-3 overflow-hidden shadow-inner">
        <!-- Grid Background Pattern -->
        <svg class="w-full h-44" viewBox="0 0 280 160">
          <defs>
            <pattern id="miniGrid" width="14" height="14" patternUnits="userSpaceOnUse">
              <path d="M 14 0 L 0 0 0 14" fill="none" stroke="#1e293b" stroke-width="0.5" />
            </pattern>
            <linearGradient id="edgeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="#6366f1" stop-opacity="0.8" />
              <stop offset="100%" stop-color="#a855f7" stop-opacity="0.8" />
            </linearGradient>
            <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="glow" />
              <feComposite in="SourceGraphic" in2="glow" operator="over" />
            </filter>
          </defs>

          <!-- Grid surface -->
          <rect width="100%" height="100%" fill="url(#miniGrid)" opacity="0.6" />

          <!-- Connecting Curved Lines -->
          <g v-for="i in Math.max(0, nodes.length - 1)" :key="'edge-' + i">
            <path
              v-if="nodes[i] && nodes[i + 1]"
              :d="`M ${nodes[i].x} ${nodes[i].y} C ${nodes[i].x + 40} ${nodes[i].y}, ${nodes[i + 1].x - 40} ${nodes[i + 1].y}, ${nodes[i + 1].x} ${nodes[i + 1].y}`"
              fill="none"
              stroke="url(#edgeGradient)"
              stroke-width="2"
              stroke-dasharray="4 2"
              class="animate-pulse"
            />
          </g>

          <!-- Graph Nodes -->
          <g
            v-for="node in nodes"
            :key="node.file"
            class="cursor-pointer group transition-all duration-300"
            @click="emit('selectFile', node.file)"
          >
            <!-- Glowing halo on active -->
            <circle
              v-if="activeFile === node.file"
              :cx="node.x"
              :cy="node.y"
              :r="node.radius + 6"
              fill="none"
              stroke="#818cf8"
              stroke-width="1.5"
              stroke-opacity="0.5"
              filter="url(#glow)"
            />

            <!-- Core Node Circle -->
            <circle
              :cx="node.x"
              :cy="node.y"
              :r="node.radius"
              :fill="activeFile === node.file ? '#4f46e5' : node.isPrimary ? '#1e1b4b' : '#0f172a'"
              :stroke="activeFile === node.file ? '#a5b4fc' : node.isPrimary ? '#6366f1' : '#334155'"
              stroke-width="2"
              class="transition-transform group-hover:scale-110 duration-200"
            />

            <!-- Node Label / Number -->
            <text
              :x="node.x"
              :y="node.y + 4"
              text-anchor="middle"
              fill="#ffffff"
              font-size="11"
              font-family="'JetBrains Mono', monospace"
              font-weight="bold"
            >
              {{ node.rank }}
            </text>

            <!-- File Name Label below Node -->
            <text
              :x="node.x"
              :y="node.y + node.radius + 14"
              text-anchor="middle"
              :fill="activeFile === node.file ? '#c7d2fe' : '#94a3b8'"
              font-size="9.5"
              font-family="'JetBrains Mono', monospace"
            >
              {{ node.fileName.slice(0, 10) }}
            </text>
          </g>
        </svg>

        <div class="mt-2 pt-2 border-t border-slate-900/60 flex items-center justify-between text-[10px] text-slate-500 font-mono">
          <span class="flex items-center space-x-1">
            <span class="w-2 h-2 rounded-full bg-indigo-500"></span>
            <span>Origin Leaf</span>
          </span>
          <span class="flex items-center space-x-1">
            <span class="w-2 h-2 rounded-full bg-purple-500"></span>
            <span>Transitive Caller</span>
          </span>
        </div>
      </div>

      <!-- Affected Files List -->
      <div class="space-y-2">
        <div class="flex items-center justify-between px-1">
          <span class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center space-x-1.5">
            <Layers class="w-3.5 h-3.5 text-indigo-400" />
            <span>Topological Sequence</span>
          </span>
          <span class="text-[10px] text-slate-500 font-mono">Bottom-Up Order</span>
        </div>

        <div class="space-y-1.5">
          <div
            v-for="(file, idx) in affectedFiles"
            :key="idx"
            @click="emit('selectFile', file)"
            :class="activeFile === file 
              ? 'bg-indigo-950/60 border-indigo-500/50 shadow-md shadow-indigo-500/10' 
              : 'bg-slate-950/60 hover:bg-slate-850/80 border-slate-800/80'"
            class="group p-2.5 border rounded-lg cursor-pointer transition-all duration-200 flex items-center justify-between"
          >
            <div class="flex items-center space-x-2.5 truncate">
              <div :class="idx === 0 ? 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30' : 'bg-slate-800 text-slate-400 border-slate-700'"
                class="w-5 h-5 rounded flex items-center justify-center text-[10px] font-mono font-bold border shrink-0">
                {{ idx + 1 }}
              </div>
              <div class="truncate">
                <p class="text-xs font-mono font-medium truncate" :class="activeFile === file ? 'text-indigo-200' : 'text-slate-200 group-hover:text-white'">
                  {{ file.split('/').pop() }}
                </p>
                <p class="text-[10px] text-slate-500 font-mono truncate">{{ file }}</p>
              </div>
            </div>

            <div class="flex items-center space-x-1 shrink-0 ml-2">
              <span v-if="idx === 0" class="px-1.5 py-0.5 rounded text-[9px] font-mono bg-purple-500/10 text-purple-400 border border-purple-500/20">
                Leaf
              </span>
              <ArrowUpRight class="w-3.5 h-3.5 text-slate-500 group-hover:text-indigo-400 transition-colors" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
