<script setup lang="ts">
/**
 * KPI 翻牌带 — 顶部数字指标
 */
import { ref, watch, onMounted } from 'vue'
import type { KpiData, DrillTarget } from '@/types/dashboard'

const props = defineProps<{ data: KpiData }>()
const emit = defineEmits<{ drill: [target: DrillTarget] }>()

interface KpiItem {
  label: string
  value: number
  key: string
  icon: string
  color: string
  route: string
  query?: Record<string, string>
}

const items = ref<KpiItem[]>([])

function buildItems(kpi: KpiData): KpiItem[] {
  return [
    { label: '资产总数', value: kpi.total_assets, key: 'total', icon: 'Monitor', color: '#3B82F6', route: '/assets' },
    { label: '在线', value: kpi.online, key: 'online', icon: 'CircleCheck', color: '#10B981', route: '/assets', query: { status: 'online' } },
    { label: '离线', value: kpi.offline, key: 'offline', icon: 'CircleClose', color: '#F59E0B', route: '/assets', query: { status: 'offline' } },
    { label: '已下线', value: kpi.decommissioned, key: 'decommissioned', icon: 'Remove', color: '#6B7280', route: '/assets', query: { status: 'decommissioned' } },
    { label: '危险端口', value: kpi.dangerous_ports, key: 'dangerous', icon: 'Warning', color: '#EF4444', route: '/reports' },
    { label: '影子资产', value: kpi.shadow_assets, key: 'shadow', icon: 'QuestionFilled', color: '#F97316', route: '/reports' },
    { label: '本月变更', value: kpi.changes_this_month, key: 'changes', icon: 'TrendCharts', color: '#8B5CF6', route: '/scans' },
    { label: '扫描覆盖', value: kpi.scan_coverage.total > 0 ? Math.round((kpi.scan_coverage.covered / kpi.scan_coverage.total) * 100) : 0, key: 'coverage', icon: 'DataAnalysis', color: '#06B6D4', route: '/reports', query: { suffix: '%' } },
  ]
}

// 翻牌动画
function animateValue(el: HTMLElement, target: number) {
  const duration = 800
  const start = parseInt(el.textContent || '0', 10)
  const diff = target - start
  if (diff === 0) { el.textContent = String(target); return }
  const startTime = performance.now()
  function step(now: number) {
    const progress = Math.min((now - startTime) / duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3) // easeOutCubic
    el.textContent = String(Math.round(start + diff * eased))
    if (progress < 1) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}

const valueRefs = ref<HTMLElement[]>([])
function setValueRef(el: any, idx: number) {
  if (el) valueRefs.value[idx] = el
}

watch(() => props.data, (kpi) => {
  if (!kpi) return
  items.value = buildItems(kpi)
  // 触发翻牌动画
  setTimeout(() => {
    items.value.forEach((item, i) => {
      const el = valueRefs.value[i]
      if (el) animateValue(el, item.key === 'coverage'
        ? (kpi.scan_coverage.total > 0 ? Math.round((kpi.scan_coverage.covered / kpi.scan_coverage.total) * 100) : 0)
        : item.value)
    })
  }, 50)
}, { immediate: true })

onMounted(() => {
  if (props.data) items.value = buildItems(props.data)
})

function handleClick(item: KpiItem) {
  emit('drill', { route: item.route, query: item.query || {} })
}
</script>

<template>
  <div class="kpi-band">
    <div
      v-for="(item, idx) in items"
      :key="item.key"
      class="kpi-item"
      @click="handleClick(item)"
    >
      <div class="kpi-icon" :style="{ color: item.color }">
        <el-icon :size="20"><component :is="item.icon" /></el-icon>
      </div>
      <div class="kpi-info">
        <div class="kpi-value" :style="{ color: item.color }">
          <span :ref="(el) => setValueRef(el, idx)">0</span>
          <span v-if="item.query?.suffix" class="kpi-suffix">{{ item.query.suffix }}</span>
        </div>
        <div class="kpi-label">{{ item.label }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.kpi-band {
  display: flex;
  gap: 12px;
  height: 100%;
  padding: 8px 0;
}
.kpi-item {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: var(--surface-sunken, #F1F4FA);
  border: 1px solid var(--neutral-200, #E5E7EB);
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
}
.kpi-item:hover {
  background: var(--neutral-100, #F3F4F6);
  border-color: var(--neutral-300, #D1D5DB);
}
.kpi-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--neutral-100, #F3F4F6);
  border-radius: 8px;
  flex-shrink: 0;
}
.kpi-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.kpi-value {
  font-family: 'DIN Alternate', 'Roboto Mono', monospace;
  font-size: 24px;
  font-weight: 700;
  line-height: 1.1;
}
.kpi-suffix {
  font-size: 14px;
  opacity: 0.7;
  margin-left: 2px;
}
.kpi-label {
  font-size: 11px;
  color: var(--neutral-500, #6B7280);
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
