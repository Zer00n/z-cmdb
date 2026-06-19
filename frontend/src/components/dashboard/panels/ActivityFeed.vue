<script setup lang="ts">
/**
 * 审计与 LLM 活动流 — 滚动播报
 */
import { ref, onMounted, onUnmounted } from 'vue'
import type { ActivityItem } from '@/types/dashboard'

const props = defineProps<{ data: ActivityItem[] }>()

const scrollRef = ref<HTMLElement>()
const isPaused = ref(false)
let timer: number | null = null
const scrollTop = ref(0)

function startScroll() {
  stopScroll()
  timer = window.setInterval(() => {
    if (isPaused.value || !scrollRef.value) return
    const el = scrollRef.value
    scrollTop.value += 1
    if (scrollTop.value >= el.scrollHeight - el.clientHeight) scrollTop.value = 0
    el.scrollTop = scrollTop.value
  }, 50)
}
function stopScroll() { if (timer) { clearInterval(timer); timer = null } }
onMounted(startScroll)
onUnmounted(stopScroll)

const ACTION_LABELS: Record<string, string> = {
  LOGIN: '登录', CREATE: '创建', UPDATE: '更新', DELETE: '删除',
  EXPORT: '导出', LLM_CALL: 'LLM', CONFIG: '配置',
}
const ACTION_COLORS: Record<string, string> = {
  LOGIN: '#3B82F6', CREATE: '#10B981', UPDATE: '#F59E0B', DELETE: '#EF4444',
  EXPORT: '#8B5CF6', LLM_CALL: '#06B6D4', CONFIG: '#F97316',
}

function formatTime(ts: string) {
  const d = new Date(ts)
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  const ss = String(d.getSeconds()).padStart(2, '0')
  return `${hh}:${mm}:${ss}`
}
</script>

<template>
  <div class="panel-inner" @mouseenter="isPaused = true" @mouseleave="isPaused = false">
    <div class="panel-title">审计与 LLM 活动流</div>
    <div ref="scrollRef" class="scroll-body">
      <div v-for="(item, i) in (data || [])" :key="i" class="scroll-row">
        <span class="col-time">{{ formatTime(item.timestamp) }}</span>
        <span class="action-badge" :style="{ color: ACTION_COLORS[item.action_type] || '#9CA3AF', borderColor: ACTION_COLORS[item.action_type] || '#9CA3AF' }">
          {{ ACTION_LABELS[item.action_type] || item.action_type }}
        </span>
        <span class="col-user">{{ item.username || '-' }}</span>
        <span class="col-target" :title="item.target">{{ item.target || '-' }}</span>
        <span :class="['col-result', item.result]">{{ item.result === 'success' ? 'OK' : 'FAIL' }}</span>
      </div>
      <div v-if="!data?.length" class="empty-row">暂无活动记录</div>
    </div>
  </div>
</template>

<style scoped>
.panel-inner { height: 100%; display: flex; flex-direction: column; }
.panel-title { font-size: 13px; color: var(--neutral-500); padding: 6px 10px 0; flex-shrink: 0; }
.scroll-body { flex: 1; overflow: hidden; min-height: 0; padding-top: 4px; }
.scroll-row {
  display: flex; align-items: center; gap: 6px;
  padding: 4px 10px; font-size: 12px; color: var(--neutral-700);
  border-bottom: 1px solid var(--neutral-100);
  transition: background 0.15s;
}
.scroll-row:hover { background: var(--neutral-50); }
.col-time { width: 58px; flex-shrink: 0; font-family: 'Roboto Mono', monospace; font-size: 11px; color: var(--neutral-400); }
.action-badge {
  font-size: 10px; padding: 1px 5px; border: 1px solid; border-radius: 3px;
  flex-shrink: 0; width: 40px; text-align: center;
}
.col-user { width: 60px; flex-shrink: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.col-target { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--neutral-400); font-size: 11px; }
.col-result { width: 36px; flex-shrink: 0; text-align: center; font-size: 10px; font-weight: 600; }
.col-result.success { color: #10B981; }
.col-result.failed { color: #EF4444; }
.empty-row { text-align: center; color: var(--neutral-300); padding: 20px; font-size: 13px; }
</style>
