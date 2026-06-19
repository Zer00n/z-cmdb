<script setup lang="ts">
/**
 * 资产变化时间线 — 滚动列表
 */
import { ref, onMounted, onUnmounted } from 'vue'
import type { AssetChangeItem, DrillTarget } from '@/types/dashboard'

const props = defineProps<{ data: AssetChangeItem[] }>()
const emit = defineEmits<{ drill: [target: DrillTarget] }>()

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

const TYPE_LABELS: Record<string, string> = {
  new: '新发现', changed: '变更', restored: '恢复', missing: '消失',
}
const TYPE_COLORS: Record<string, string> = {
  new: '#10B981', changed: '#F59E0B', restored: '#3B82F6', missing: '#EF4444',
}

function handleClick(item: AssetChangeItem) {
  emit('drill', { route: '/assets', query: { search: item.ip_address } })
}
</script>

<template>
  <div class="panel-inner" @mouseenter="isPaused = true" @mouseleave="isPaused = false">
    <div class="panel-title">资产变化时间线</div>
    <div ref="scrollRef" class="scroll-body">
      <div v-for="(item, i) in (data || [])" :key="i" class="scroll-row" @click="handleClick(item)">
        <span class="type-badge" :style="{ color: TYPE_COLORS[item.diff_type] || '#9CA3AF', borderColor: TYPE_COLORS[item.diff_type] || '#9CA3AF' }">
          {{ TYPE_LABELS[item.diff_type] || item.diff_type }}
        </span>
        <span class="col-ip">{{ item.ip_address }}</span>
        <span class="col-host">{{ item.hostname || '-' }}</span>
        <span class="col-svc">{{ item.service_name || '-' }}{{ item.port_number ? ':' + item.port_number : '' }}</span>
      </div>
      <div v-if="!data?.length" class="empty-row">暂无变化记录</div>
    </div>
  </div>
</template>

<style scoped>
.panel-inner { height: 100%; display: flex; flex-direction: column; }
.panel-title { font-size: 13px; color: var(--neutral-500); padding: 6px 10px 0; flex-shrink: 0; }
.scroll-body { flex: 1; overflow: hidden; min-height: 0; padding-top: 4px; }
.scroll-row {
  display: flex; align-items: center; gap: 8px;
  padding: 5px 10px; font-size: 12px; color: var(--neutral-700);
  cursor: pointer; border-bottom: 1px solid var(--neutral-100);
  transition: background 0.15s;
}
.scroll-row:hover { background: var(--neutral-50); }
.type-badge {
  font-size: 10px; padding: 1px 6px; border: 1px solid; border-radius: 3px;
  flex-shrink: 0; width: 44px; text-align: center;
}
.col-ip { width: 100px; flex-shrink: 0; }
.col-host { width: 80px; flex-shrink: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.col-svc { flex: 1; color: var(--neutral-400); font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.empty-row { text-align: center; color: var(--neutral-300); padding: 20px; font-size: 13px; }
</style>
