<script setup lang="ts">
/**
 * 危险端口告警 — 滚动列表，按严重性着色
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import type { DangerousPortItem, DrillTarget } from '@/types/dashboard'

const props = defineProps<{ data: DangerousPortItem[] }>()
const emit = defineEmits<{ drill: [target: DrillTarget] }>()

const scrollRef = ref<HTMLElement>()
const isPaused = ref(false)
let timer: number | null = null
const scrollTop = ref(0)

const highCount = computed(() => (props.data || []).filter(d => d.severity === 'high').length)
const mediumCount = computed(() => (props.data || []).filter(d => d.severity === 'medium').length)

function startScroll() {
  stopScroll()
  timer = window.setInterval(() => {
    if (isPaused.value || !scrollRef.value) return
    const el = scrollRef.value
    scrollTop.value += 1
    if (scrollTop.value >= el.scrollHeight - el.clientHeight) {
      scrollTop.value = 0
    }
    el.scrollTop = scrollTop.value
  }, 50)
}

function stopScroll() {
  if (timer) { clearInterval(timer); timer = null }
}

onMounted(startScroll)
onUnmounted(stopScroll)

function handleClick(item: DangerousPortItem) {
  emit('drill', { route: `/assets/${item.asset_id}`, query: {} })
}

function zoneLabel(z: string) {
  const map: Record<string, string> = {
    dmz: 'DMZ', intranet: '内网', office: '办公网', management: '管理网',
    aliyun: '阿里云', tencent: '腾讯云', huawei: '华为云',
    aws: 'AWS', azure: 'Azure', gcp: 'GCP', other_cloud: '其他云', other: '其他',
  }
  return map[z] || z
}
</script>

<template>
  <div class="panel-inner"
    @mouseenter="isPaused = true"
    @mouseleave="isPaused = false"
  >
    <div class="panel-header">
      <span class="panel-title">危险端口告警</span>
      <div class="counters">
        <span class="counter high">高危 {{ highCount }}</span>
        <span class="counter medium">中危 {{ mediumCount }}</span>
      </div>
    </div>
    <div class="scroll-head">
      <span class="col-ip">IP</span>
      <span class="col-port">端口</span>
      <span class="col-svc">服务</span>
      <span class="col-zone">区域</span>
      <span class="col-sev">级别</span>
    </div>
    <div ref="scrollRef" class="scroll-body">
      <div
        v-for="(item, i) in (data || [])"
        :key="i"
        :class="['scroll-row', item.severity]"
        @click="handleClick(item)"
      >
        <span class="col-ip" :title="item.ip_address">{{ item.ip_address }}</span>
        <span class="col-port">{{ item.port_number }}/{{ item.protocol }}</span>
        <span class="col-svc" :title="item.service_name || ''">{{ item.service_name || '-' }}</span>
        <span class="col-zone">{{ zoneLabel(item.network_zone) }}</span>
        <span class="col-sev">
          <span :class="['sev-badge', item.severity]">{{ item.severity === 'high' ? '高危' : '中危' }}</span>
        </span>
      </div>
      <div v-if="!data?.length" class="empty-row">暂无危险端口告警</div>
    </div>
  </div>
</template>

<style scoped>
.panel-inner { height: 100%; display: flex; flex-direction: column; }
.panel-header { display: flex; align-items: center; justify-content: space-between; padding: 6px 10px 0; flex-shrink: 0; }
.panel-title { font-size: 13px; color: var(--neutral-500); }
.counters { display: flex; gap: 8px; }
.counter { font-size: 11px; padding: 1px 6px; border-radius: 3px; }
.counter.high { color: #DC2626; background: rgba(239,68,68,0.08); }
.counter.medium { color: #D97706; background: rgba(245,158,11,0.08); }

.scroll-head, .scroll-row {
  display: flex;
  align-items: center;
  padding: 0 10px;
  font-size: 12px;
  gap: 0;
}
.scroll-head {
  color: var(--neutral-400);
  border-bottom: 1px solid var(--neutral-200);
  padding: 4px 10px;
  flex-shrink: 0;
}
.scroll-body { flex: 1; overflow: hidden; min-height: 0; }
.scroll-row {
  padding: 5px 10px;
  color: var(--neutral-700);
  cursor: pointer;
  transition: background 0.15s;
  border-bottom: 1px solid var(--neutral-100);
}
.scroll-row:hover { background: var(--neutral-50); }
.scroll-row.high { border-left: 3px solid #EF4444; }
.scroll-row.medium { border-left: 3px solid #F59E0B; }

.col-ip { width: 110px; flex-shrink: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.col-port { width: 65px; flex-shrink: 0; }
.col-svc { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.col-zone { width: 56px; flex-shrink: 0; text-align: center; }
.col-sev { width: 48px; flex-shrink: 0; text-align: center; }
.sev-badge { font-size: 10px; padding: 1px 5px; border-radius: 3px; }
.sev-badge.high { color: #DC2626; background: rgba(239,68,68,0.1); }
.sev-badge.medium { color: #D97706; background: rgba(245,158,11,0.1); }
.empty-row { text-align: center; color: var(--neutral-300); padding: 20px; font-size: 13px; }
</style>
