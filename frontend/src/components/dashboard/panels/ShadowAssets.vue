<script setup lang="ts">
/**
 * 影子资产 — 缺字段/长期离线计数 + 明细滚动
 */
import { ref, onMounted, onUnmounted } from 'vue'
import type { ShadowAssetsData, DrillTarget } from '@/types/dashboard'

const props = defineProps<{ data: ShadowAssetsData }>()
const emit = defineEmits<{ drill: [target: DrillTarget] }>()

const tab = ref<'missing' | 'offline'>('missing')
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

function handleClick(id: number) {
  emit('drill', { route: `/assets/${id}`, query: {} })
}
</script>

<template>
  <div class="panel-inner" @mouseenter="isPaused = true" @mouseleave="isPaused = false">
    <div class="panel-header">
      <span class="panel-title">影子资产</span>
      <div class="counters">
        <span class="counter warn">缺字段 {{ data?.missing_fields_count ?? 0 }}</span>
        <span class="counter offline">长期离线 {{ data?.long_offline_count ?? 0 }}</span>
      </div>
    </div>
    <div class="tab-bar">
      <button :class="['tab', { active: tab === 'missing' }]" @click="tab = 'missing'; scrollTop = 0">缺关键字段</button>
      <button :class="['tab', { active: tab === 'offline' }]" @click="tab = 'offline'; scrollTop = 0">长期离线</button>
    </div>
    <div ref="scrollRef" class="scroll-body">
      <template v-if="tab === 'missing'">
        <div v-for="item in (data?.missing_fields || [])" :key="item.id" class="scroll-row" @click="handleClick(item.id)">
          <span class="col-no">{{ item.asset_no }}</span>
          <span class="col-ip">{{ item.ip_address }}</span>
          <span class="col-host">{{ item.hostname || '-' }}</span>
          <span class="col-reason">{{ item.reason }}</span>
        </div>
        <div v-if="!data?.missing_fields?.length" class="empty-row">暂无</div>
      </template>
      <template v-else>
        <div v-for="item in (data?.long_offline || [])" :key="item.id" class="scroll-row" @click="handleClick(item.id)">
          <span class="col-no">{{ item.asset_no }}</span>
          <span class="col-ip">{{ item.ip_address }}</span>
          <span class="col-host">{{ item.hostname || '-' }}</span>
          <span class="col-count">未扫到 {{ item.missing_count }} 次</span>
        </div>
        <div v-if="!data?.long_offline?.length" class="empty-row">暂无</div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.panel-inner { height: 100%; display: flex; flex-direction: column; }
.panel-header { display: flex; align-items: center; justify-content: space-between; padding: 6px 10px 0; flex-shrink: 0; }
.panel-title { font-size: 13px; color: var(--neutral-500); }
.counters { display: flex; gap: 8px; }
.counter { font-size: 11px; padding: 1px 6px; border-radius: 3px; }
.counter.warn { color: #D97706; background: rgba(245,158,11,0.08); }
.counter.offline { color: var(--neutral-400); background: var(--neutral-100); }

.tab-bar { display: flex; gap: 4px; padding: 6px 10px 4px; flex-shrink: 0; }
.tab {
  padding: 2px 10px; font-size: 11px;
  color: var(--neutral-400); background: var(--surface-base);
  border: 1px solid var(--neutral-200); border-radius: 4px;
  cursor: pointer; transition: all 0.2s;
}
.tab.active { color: #3B82F6; background: rgba(59,130,246,0.08); border-color: rgba(59,130,246,0.4); }
.tab:hover { color: var(--neutral-700); }

.scroll-body { flex: 1; overflow: hidden; min-height: 0; }
.scroll-row {
  display: flex; align-items: center; gap: 0;
  padding: 5px 10px; font-size: 12px; color: var(--neutral-700);
  cursor: pointer; border-bottom: 1px solid var(--neutral-100);
  transition: background 0.15s;
}
.scroll-row:hover { background: var(--neutral-50); }
.col-no { width: 80px; flex-shrink: 0; font-family: 'Roboto Mono', monospace; font-size: 11px; }
.col-ip { width: 100px; flex-shrink: 0; }
.col-host { width: 90px; flex-shrink: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.col-reason, .col-count { flex: 1; color: var(--neutral-400); font-size: 11px; }
.empty-row { text-align: center; color: var(--neutral-300); padding: 20px; font-size: 13px; }
</style>
