<script setup lang="ts">
/**
 * KPI 图标 — 按 name 渲染对应线性 SVG
 * name 取自 Dashboard.vue 中 KPI_DEFS 的 key
 */
defineProps<{ name: string }>()
</script>

<template>
  <svg v-if="name === 'total'" width="15" height="15" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="14" height="5" rx="1.5"/><rect x="2" y="10" width="14" height="5" rx="1.5"/><circle cx="4.5" cy="5.5" r=".8" fill="currentColor" stroke="none"/><circle cx="4.5" cy="12.5" r=".8" fill="currentColor" stroke="none"/></svg>
  <svg v-else-if="name === 'online'" width="15" height="15" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="9" r="7"/><path d="M5.5 9l2.5 2.5 4.5-5"/></svg>
  <svg v-else-if="name === 'offline'" width="15" height="15" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="9" r="7"/><path d="M9 5.5v4"/><circle cx="9" cy="12.5" r=".8" fill="currentColor" stroke="none"/></svg>
  <svg v-else-if="name === 'decom'" width="15" height="15" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="9" r="7"/><path d="M5.5 9h7"/></svg>
  <svg v-else-if="name === 'danger'" width="15" height="15" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 2L2 14h14L9 2z"/><path d="M9 7v3.5"/><circle cx="9" cy="12.5" r=".8" fill="currentColor" stroke="none"/></svg>
  <svg v-else-if="name === 'shadow'" width="15" height="15" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="9" r="7"/><path d="M9 5v4l3 3"/><path d="M4 4l10 10" stroke-dasharray="2 2"/></svg>
  <svg v-else-if="name === 'changes'" width="15" height="15" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="6" height="6" rx="1"/><rect x="10" y="2" width="6" height="6" rx="1"/><rect x="2" y="10" width="6" height="6" rx="1"/><rect x="10" y="10" width="6" height="6" rx="1"/></svg>
  <svg v-else-if="name === 'coverage'" width="15" height="15" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="9" r="7"/><path d="M9 2a7 7 0 0 1 0 14"/><path d="M5 5.5C6.2 4.2 8 3.5 9 3.5"/></svg>
</template>
