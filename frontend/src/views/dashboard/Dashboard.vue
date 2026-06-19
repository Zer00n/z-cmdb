<script setup lang="ts">
/**
 * 资产总览 — 严格对齐 Asset Overview.html 设计稿
 */
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useDashboardStore } from '@/stores/dashboard'
import * as echarts from 'echarts/core'
import { GraphChart, PieChart, BarChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { DashboardSummary, KpiData, DangerousPortItem } from '@/types/dashboard'

echarts.use([GraphChart, PieChart, BarChart, TooltipComponent, LegendComponent, GridComponent, CanvasRenderer])

const router = useRouter()
const store = useDashboardStore()
const summary = computed(() => store.summary)
const kpi = computed(() => summary.value?.kpi)

// ── KPI 定义 ───────────────────────────────────────────────
interface KpiDef {
  key: string
  label: string
  cssClass: string
  getVal: (k: KpiData) => number
  suffix: string
  route?: string
  query?: Record<string, string>
}

const KPI_DEFS: KpiDef[] = [
  { key: 'total', label: '资产总数', cssClass: 'kpi-neutral', getVal: k => k.total_assets, suffix: '' },
  { key: 'online', label: '在线', cssClass: 'kpi-success', getVal: k => k.online, suffix: '', route: '/assets', query: { status: 'online' } },
  { key: 'offline', label: '离线', cssClass: 'kpi-warning', getVal: k => k.offline, suffix: '', route: '/assets', query: { status: 'offline' } },
  { key: 'decom', label: '已下线', cssClass: 'kpi-muted', getVal: k => k.decommissioned, suffix: '', route: '/assets', query: { status: 'decommissioned' } },
  { key: 'danger', label: '危险端口', cssClass: 'kpi-danger', getVal: k => k.dangerous_ports, suffix: '' },
  { key: 'shadow', label: '影子资产', cssClass: 'kpi-alert', getVal: k => k.shadow_assets, suffix: '' },
  { key: 'changes', label: '本月变更', cssClass: 'kpi-purple', getVal: k => k.changes_this_month, suffix: '' },
  { key: 'coverage', label: '扫描覆盖', cssClass: 'kpi-cyan', getVal: k => k.scan_coverage.total > 0 ? Math.round((k.scan_coverage.covered / k.scan_coverage.total) * 100) : 0, suffix: '%' },
]

// KPI 翻牌动画
const kpiNumRefs = ref<HTMLElement[]>([])
function setKpiRef(el: any, idx: number) { if (el) kpiNumRefs.value[idx] = el }
function animateCounter(el: HTMLElement, target: number, suffix: string) {
  if (target === 0) { el.textContent = '0' + suffix; return }
  const duration = 900, startTime = performance.now()
  function step(now: number) {
    const progress = Math.min((now - startTime) / duration, 1)
    const ease = 1 - Math.pow(1 - progress, 3)
    el.textContent = Math.round(ease * target) + suffix
    if (progress < 1) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}
watch(kpi, (val) => {
  if (!val) return
  nextTick(() => {
    KPI_DEFS.forEach((def, i) => {
      const el = kpiNumRefs.value[i]
      if (el) animateCounter(el, def.getVal(val), def.suffix)
    })
  })
}, { immediate: true })

function handleKpiClick(def: KpiDef) {
  if (def.route) router.push({ path: def.route, query: def.query })
}

// ── 资产分布 Tab ───────────────────────────────────────────
const distTab = ref<'by_zone' | 'by_type' | 'by_importance' | 'by_os'>('by_zone')
const distTabs = [
  { key: 'by_zone' as const, label: '网络区域' },
  { key: 'by_type' as const, label: '资产类型' },
  { key: 'by_importance' as const, label: '重要性' },
  { key: 'by_os' as const, label: '操作系统' },
]

// ── 危险端口 ───────────────────────────────────────────────
const dangerousPorts = computed(() => summary.value?.dangerous_ports || [])
const highCount = computed(() => dangerousPorts.value.filter(d => d.severity === 'high').length)
const medCount = computed(() => dangerousPorts.value.filter(d => d.severity === 'medium').length)

function zoneLabel(z: string) {
  const m: Record<string, string> = { dmz: 'DMZ', intranet: '内网', office: '办公网', management: '管理网', aliyun: '阿里云', tencent: '腾讯云', huawei: '华为云', aws: 'AWS', azure: 'Azure', gcp: 'GCP', other_cloud: '其他云', other: '其他' }
  return m[z] || z
}

// ── ECharts 实例 ───────────────────────────────────────────
let chartTopo: echarts.ECharts | null = null
let chartDist: echarts.ECharts | null = null
let chartPortBar: echarts.ECharts | null = null
let chartPortZone: echarts.ECharts | null = null

const ZONE_COLORS: Record<string, string> = {
  intranet: '#2563EB', office: '#0E7490', dmz: '#B45309', management: '#6D28D9',
  aliyun: '#EA580C', tencent: '#0891B2', huawei: '#CF0A2C', aws: '#FF9900',
  azure: '#0078D4', gcp: '#4285F4', other_cloud: '#94A3B8', other: '#94A3B8',
}
const TYPE_COLORS = ['#2563EB', '#0E7490', '#EA580C', '#6D28D9', '#94A3B8']
const IMP_COLORS = ['#DC2626', '#D97706', '#94A3B8']
const OS_COLORS = ['#2563EB', '#0E7490', '#94A3B8']

const TOOLTIP = { backgroundColor: '#fff', borderColor: '#E2E8F0', borderWidth: 1, textStyle: { color: '#334155', fontSize: 12 } }

function renderTopo() {
  const el = document.getElementById('chart-topo')
  if (!el || !summary.value) return
  if (!chartTopo) chartTopo = echarts.init(el)
  const zones = summary.value.zone_topology.zones
  const hubValue = zones.reduce((s, z) => s + z.asset_count, 0)
  const nodes = [
    { id: 'hub', name: '组织网络', value: hubValue, symbolSize: 60, itemStyle: { color: '#334155', borderColor: '#E2E8F0', borderWidth: 3 } },
    ...zones.map(z => ({
      id: z.zone, name: z.zone, value: z.asset_count,
      symbolSize: Math.max(24, Math.min(52, z.asset_count * 5 + 16)),
      itemStyle: { color: ZONE_COLORS[z.zone] || '#94A3B8', borderColor: z.core_count > 0 ? '#DC2626' : 'transparent', borderWidth: z.core_count > 0 ? 2.5 : 0 },
    })),
  ]
  const edges = zones.map(z => ({ source: 'hub', target: z.zone }))
  chartTopo.setOption({
    backgroundColor: 'transparent', animation: true, animationDuration: 1200,
    tooltip: { ...TOOLTIP, trigger: 'item', formatter: (p: any) => p.dataType === 'node' ? `<b>${p.data.name}</b><br/>资产数：${p.data.value}` : '' },
    series: [{
      type: 'graph', layout: 'force', data: nodes, edges, roam: true,
      label: { show: true, position: 'bottom', fontSize: 12, color: '#334155', formatter: (p: any) => `${p.data.name}\n${p.data.value}` },
      edgeSymbol: ['none', 'none'], lineStyle: { color: '#E2E8F0', width: 1.5, curveness: 0.15 },
      emphasis: { focus: 'adjacency', lineStyle: { width: 2.5, color: '#2563EB' } },
      force: { repulsion: 320, gravity: 0.06, edgeLength: [80, 160], layoutAnimation: true },
      itemStyle: { borderColor: 'transparent', borderWidth: 0, shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.08)' },
    }],
  }, { notMerge: true })
}

function renderDist() {
  const el = document.getElementById('chart-dist')
  if (!el || !summary.value) return
  if (!chartDist) chartDist = echarts.init(el)
  const raw = summary.value.asset_distribution[distTab.value] || []
  const palette = distTab.value === 'by_zone' ? [] : distTab.value === 'by_type' ? TYPE_COLORS : distTab.value === 'by_importance' ? IMP_COLORS : OS_COLORS
  const data = raw.map((item, i) => ({
    value: item.count, name: item.label,
    itemStyle: { color: distTab.value === 'by_zone' ? (ZONE_COLORS[item.label] || '#94A3B8') : palette[i % palette.length] },
  }))
  const total = data.reduce((s, d) => s + d.value, 0)
  chartDist.setOption({
    backgroundColor: 'transparent', animation: true, animationDuration: 700,
    tooltip: { ...TOOLTIP, trigger: 'item', formatter: '{b}：{c} ({d}%)' },
    legend: { orient: 'vertical', right: 24, top: 'center', itemWidth: 10, itemHeight: 10, icon: 'roundRect', textStyle: { color: '#334155', fontSize: 12 }, itemGap: 10 },
    series: [{
      type: 'pie', radius: ['46%', '68%'], center: ['36%', '50%'], data,
      label: { show: true, position: 'center', formatter: `{total|${total}}\n{sub|台资产}`, rich: { total: { fontSize: 26, fontWeight: 700, color: '#334155', fontFamily: '"JetBrains Mono", monospace', lineHeight: 34 }, sub: { fontSize: 12, color: '#94A3B8', lineHeight: 18 } } },
      emphasis: { itemStyle: { shadowBlur: 12, shadowColor: 'rgba(0,0,0,0.1)' } },
      labelLine: { show: false },
    }],
  }, { notMerge: true })
}

function renderPortBar() {
  const el = document.getElementById('chart-port-bar')
  if (!el || !summary.value) return
  if (!chartPortBar) chartPortBar = echarts.init(el)
  const DANGEROUS_PORTS = new Set([21, 22, 23, 135, 139, 445, 1433, 1521, 2375, 3306, 3389, 5432, 5984, 6379, 8080, 8888, 9200, 11211, 27017])
  const ports = (summary.value.port_exposure.top_ports || []).slice(0, 10)
  chartPortBar.setOption({
    backgroundColor: 'transparent', animation: true, animationDuration: 900,
    grid: { left: 56, right: 20, top: 8, bottom: 8, containLabel: false },
    tooltip: { ...TOOLTIP, trigger: 'axis', axisPointer: { type: 'none' }, formatter: (p: any) => { const d = ports[p[0].dataIndex]; const badge = DANGEROUS_PORTS.has(d.port) ? ' <span style="color:#DC2626;font-weight:600;">危险</span>' : ''; return `端口 ${d.port}${badge}<br/>开放数：${d.count}` } },
    xAxis: { type: 'value', show: false },
    yAxis: { type: 'category', data: ports.map(p => String(p.port)), axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: '#334155', fontFamily: '"JetBrains Mono", monospace', fontSize: 11, margin: 8 } },
    series: [{ type: 'bar', data: ports.map(p => ({ value: p.count, itemStyle: { color: DANGEROUS_PORTS.has(p.port) ? '#DC2626' : '#2563EB', borderRadius: [0, 3, 3, 0] } })), barMaxWidth: 14, label: { show: true, position: 'right', fontSize: 11, fontFamily: '"JetBrains Mono", monospace', color: '#334155' } }],
  }, { notMerge: true })
}

function renderPortZone() {
  const el = document.getElementById('chart-port-zone')
  if (!el || !summary.value) return
  if (!chartPortZone) chartPortZone = echarts.init(el)
  const zones = summary.value.port_exposure.by_zone || []
  const data = zones.map(z => ({ value: z.port_count, name: z.zone, itemStyle: { color: ZONE_COLORS[z.zone] || '#94A3B8' } }))
  chartPortZone.setOption({
    backgroundColor: 'transparent', animation: true, animationDuration: 900,
    tooltip: { ...TOOLTIP, trigger: 'item', formatter: '{b}：{d}%' },
    legend: { orient: 'vertical', right: 16, top: 'center', itemWidth: 8, itemHeight: 8, icon: 'roundRect', textStyle: { color: '#334155', fontSize: 11 }, itemGap: 8 },
    series: [{
      type: 'pie', radius: ['40%', '62%'], center: ['38%', '50%'], data,
      emphasis: { itemStyle: { shadowBlur: 12, shadowColor: 'rgba(0,0,0,0.1)' }, label: { show: true, formatter: (p: any) => `{v|${p.percent.toFixed(0)}%}\n{n|${p.name}}`, rich: { v: { fontSize: 20, fontWeight: 700, color: '#334155', fontFamily: '"JetBrains Mono", monospace', lineHeight: 26 }, n: { fontSize: 11, color: '#94A3B8', lineHeight: 16 } } } },
      labelLine: { show: false },
    }],
  }, { notMerge: true })
}

function renderAllCharts() { renderTopo(); renderDist(); renderPortBar(); renderPortZone() }

watch(distTab, () => nextTick(renderDist))
watch(summary, () => nextTick(renderAllCharts), { deep: true })

// 危险端口自动滚动
const alertListRef = ref<HTMLElement>()
const alertScrolling = ref(true)
let alertRaf = 0
function startAlertScroll() {
  function step() {
    if (!alertScrolling.value || !alertListRef.value) { alertRaf = requestAnimationFrame(step); return }
    const el = alertListRef.value
    el.scrollTop += 0.5
    if (el.scrollTop + el.clientHeight >= el.scrollHeight - 2) el.scrollTop = 0
    alertRaf = requestAnimationFrame(step)
  }
  setTimeout(() => { alertRaf = requestAnimationFrame(step) }, 2000)
}

onMounted(async () => {
  await store.fetchSummary()
  await nextTick()
  renderAllCharts()
  startAlertScroll()
  window.addEventListener('resize', handleResize)
})
onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  cancelAnimationFrame(alertRaf)
  chartTopo?.dispose(); chartDist?.dispose(); chartPortBar?.dispose(); chartPortZone?.dispose()
})
function handleResize() { [chartTopo, chartDist, chartPortBar, chartPortZone].forEach(c => c?.resize()) }
</script>

<template>
  <div class="dash-page">
    <!-- 页头 -->
    <div class="page-head">
      <div class="page-head-left">
        <h1>资产总览</h1>
        <div class="sub" v-if="summary">
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="8" r="6"/><path d="M8 4.5V8l2 1.5"/></svg>
          数据更新于 <span class="ts">{{ new Date(summary.generated_at).toLocaleString('zh-CN') }}</span>
        </div>
      </div>
      <button class="btn-refresh" :disabled="store.loading || undefined" @click="store.fetchSummary()">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M13.5 2.5v4h-4"/><path d="M2.5 13.5v-4h4"/><path d="M13.5 6.5A5.5 5.5 0 0 0 3.8 3.8"/><path d="M2.5 9.5a5.5 5.5 0 0 0 9.7 2.7"/></svg>
        刷新数据
      </button>
    </div>

    <!-- KPI 行 -->
    <div class="kpi-row" v-if="kpi">
      <div
        v-for="(def, i) in KPI_DEFS"
        :key="def.key"
        :class="['kpi', def.cssClass]"
        @click="handleKpiClick(def)"
      >
        <div class="kpi-icon">
          <svg v-if="def.key==='total'" width="15" height="15" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="14" height="5" rx="1.5"/><rect x="2" y="10" width="14" height="5" rx="1.5"/><circle cx="4.5" cy="5.5" r=".8" fill="currentColor" stroke="none"/><circle cx="4.5" cy="12.5" r=".8" fill="currentColor" stroke="none"/></svg>
          <svg v-else-if="def.key==='online'" width="15" height="15" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="9" r="7"/><path d="M5.5 9l2.5 2.5 4.5-5"/></svg>
          <svg v-else-if="def.key==='offline'" width="15" height="15" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="9" r="7"/><path d="M9 5.5v4"/><circle cx="9" cy="12.5" r=".8" fill="currentColor" stroke="none"/></svg>
          <svg v-else-if="def.key==='decom'" width="15" height="15" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="9" r="7"/><path d="M5.5 9h7"/></svg>
          <svg v-else-if="def.key==='danger'" width="15" height="15" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 2L2 14h14L9 2z"/><path d="M9 7v3.5"/><circle cx="9" cy="12.5" r=".8" fill="currentColor" stroke="none"/></svg>
          <svg v-else-if="def.key==='shadow'" width="15" height="15" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="9" r="7"/><path d="M9 5v4l3 3"/><path d="M4 4l10 10" stroke-dasharray="2 2"/></svg>
          <svg v-else-if="def.key==='changes'" width="15" height="15" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="6" height="6" rx="1"/><rect x="10" y="2" width="6" height="6" rx="1"/><rect x="2" y="10" width="6" height="6" rx="1"/><rect x="10" y="10" width="6" height="6" rx="1"/></svg>
          <svg v-else-if="def.key==='coverage'" width="15" height="15" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="9" r="7"/><path d="M9 2a7 7 0 0 1 0 14"/><path d="M5 5.5C6.2 4.2 8 3.5 9 3.5"/></svg>
        </div>
        <div class="kpi-num" :ref="(el) => setKpiRef(el, i)">0{{ def.suffix }}</div>
        <div class="kpi-label">{{ def.label }}</div>
      </div>
    </div>

    <!-- Row 2: 网络区域拓扑 | 资产分布 -->
    <div class="grid-2">
      <div class="card">
        <div class="card-head">
          <div class="ttl">
            <span class="ttl-ico">
              <svg width="14" height="14" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="4" r="2"/><circle cx="3.5" cy="14" r="2"/><circle cx="14.5" cy="14" r="2"/><path d="M9 6v3.5M9 9.5L3.5 12M9 9.5L14.5 12"/></svg>
            </span>
            网络区域拓扑
            <span class="ttl-meta">force-directed</span>
          </div>
        </div>
        <div id="chart-topo" class="chart-box" style="height:340px;"></div>
      </div>

      <div class="card" style="display:flex;flex-direction:column;">
        <div class="card-head">
          <div class="ttl">
            <span class="ttl-ico">
              <svg width="14" height="14" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="9" r="7"/><path d="M9 2a7 7 0 0 1 7 7H9V2z" fill="currentColor" fill-opacity=".12"/></svg>
            </span>
            资产分布
          </div>
        </div>
        <div class="tab-bar">
          <button v-for="tab in distTabs" :key="tab.key" :class="['tab-btn', { active: distTab === tab.key }]" @click="distTab = tab.key">{{ tab.label }}</button>
        </div>
        <div id="chart-dist" class="chart-box" style="height:296px;"></div>
      </div>
    </div>

    <!-- Row 3: 端口暴露面 | 危险端口告警 -->
    <div class="grid-2">
      <div class="card">
        <div class="card-head">
          <div class="ttl">
            <span class="ttl-ico" style="background:rgba(220,38,38,0.08); color:#DC2626;">
              <svg width="14" height="14" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="12" height="12" rx="2"/><path d="M9 6v6M6 9h6"/></svg>
            </span>
            端口暴露面
          </div>
          <div class="tools"><button class="tool-btn">Top 10</button></div>
        </div>
        <div class="port-split">
          <div>
            <div class="split-label">开放端口 Top 10</div>
            <div id="chart-port-bar" style="height:288px;"></div>
          </div>
          <div class="ps-divider"></div>
          <div>
            <div class="split-label">按区域分布</div>
            <div id="chart-port-zone" style="height:288px;"></div>
          </div>
        </div>
      </div>

      <div class="card" style="display:flex; flex-direction:column;">
        <div class="card-head">
          <div class="ttl">
            <span class="ttl-ico" style="background:rgba(220,38,38,0.08); color:#DC2626;">
              <svg width="14" height="14" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 2L2 14h14L9 2z"/><path d="M9 7v3.5"/><circle cx="9" cy="12.5" r=".8" fill="currentColor" stroke="none"/></svg>
            </span>
            危险端口告警
          </div>
          <div class="sev-counts">
            <span class="sev-tag h">高危 {{ highCount }}</span>
            <span class="sev-tag m">中危 {{ medCount }}</span>
          </div>
        </div>
        <div class="alert-thead">
          <div style="width:3px; flex-shrink:0;"></div>
          <div class="th-ip">IP</div>
          <div class="th-port">端口</div>
          <div class="th-svc">服务</div>
          <div class="th-zone">区域</div>
          <div class="th-lvl">级别</div>
        </div>
        <div class="alert-table-wrap" style="flex:1;">
          <ul
            ref="alertListRef"
            class="alert-list"
            @mouseenter="alertScrolling = false"
            @mouseleave="alertScrolling = true"
          >
            <li
              v-for="(item, i) in dangerousPorts"
              :key="i"
              :class="['alert-row', item.severity === 'high' ? 'high' : 'med']"
            >
              <div class="sev-bar"></div>
              <div class="ip">{{ item.ip_address }}</div>
              <div class="port">{{ item.port_number }}/{{ item.protocol }}</div>
              <div class="svc">{{ item.service_name || '-' }}</div>
              <div class="zone">{{ zoneLabel(item.network_zone) }}</div>
              <div class="lvl">{{ item.severity === 'high' ? '🔴 高危' : '🟠 中危' }}</div>
            </li>
            <li v-if="!dangerousPorts.length" class="alert-row" style="justify-content:center; color:var(--neutral-400);">暂无危险端口</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dash-page { max-width: 1400px; }

/* 页头 */
.page-head { display: flex; align-items: center; justify-content: space-between; gap: var(--space-4); margin-bottom: var(--space-6); }
.page-head-left h1 { margin: 0; font-size: var(--fs-h2, 22px); font-weight: 700; color: var(--neutral-900); }
.page-head-left .sub { font-size: 12px; color: var(--neutral-500); display: flex; align-items: center; gap: 6px; margin-top: 4px; }
.page-head-left .sub .ts { font-family: var(--font-mono, monospace); color: var(--neutral-700); }
.btn-refresh {
  display: inline-flex; align-items: center; gap: 6px; height: 34px; padding: 0 var(--space-4);
  background: var(--color-primary-500, #2563EB); color: #fff; border: 0; border-radius: var(--radius-md, 6px);
  font-size: 13px; font-weight: 500; cursor: pointer; transition: background 0.12s;
}
.btn-refresh:hover { background: var(--color-primary-600, #1D4ED8); }

/* KPI 行 */
.kpi-row { display: grid; grid-template-columns: repeat(8, 1fr); gap: var(--space-3, 12px); margin-bottom: var(--space-5, 20px); }
.kpi {
  background: var(--neutral-0, #fff); border: 1px solid var(--neutral-200, #E2E8F0); border-radius: var(--radius-lg, 10px);
  padding: var(--space-4, 16px) var(--space-4, 16px) var(--space-3, 12px); display: flex; flex-direction: column; gap: 6px;
  position: relative; overflow: hidden; cursor: default;
}
.kpi::after { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 2px; border-radius: 10px 10px 0 0; background: var(--kpi-accent, #E2E8F0); opacity: .7; }
.kpi .kpi-icon { width: 30px; height: 30px; border-radius: var(--radius-md, 6px); background: var(--kpi-icon-bg, #F1F5F9); color: var(--kpi-accent, #64748B); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.kpi .kpi-num { font-family: var(--font-mono, monospace); font-weight: 700; font-size: 28px; line-height: 1; letter-spacing: -0.03em; color: var(--kpi-accent, #0F172A); margin-top: 4px; }
.kpi .kpi-label { font-size: 12px; color: var(--neutral-500, #64748B); font-weight: 500; white-space: nowrap; }
.kpi.kpi-neutral  { --kpi-accent: #2563EB; --kpi-icon-bg: rgba(37,99,235,0.06); }
.kpi.kpi-success  { --kpi-accent: #16A34A; --kpi-icon-bg: rgba(22,163,74,0.06); }
.kpi.kpi-warning  { --kpi-accent: #D97706; --kpi-icon-bg: rgba(217,119,6,0.06); }
.kpi.kpi-muted    { --kpi-accent: #94A3B8; --kpi-icon-bg: #F1F5F9; }
.kpi.kpi-danger   { --kpi-accent: #DC2626; --kpi-icon-bg: rgba(220,38,38,0.06); }
.kpi.kpi-alert    { --kpi-accent: #EA580C; --kpi-icon-bg: rgba(234,88,12,0.06); }
.kpi.kpi-purple   { --kpi-accent: #7C3AED; --kpi-icon-bg: #EDE9FE; }
.kpi.kpi-cyan     { --kpi-accent: #0891B2; --kpi-icon-bg: rgba(8,145,178,0.06); }

/* 双列网格 */
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-4, 16px); margin-bottom: var(--space-4, 16px); align-items: start; }

/* 卡片 */
.card { background: var(--neutral-0, #fff); border: 1px solid var(--neutral-200, #E2E8F0); border-radius: var(--radius-lg, 10px); overflow: hidden; }
.card-head { display: flex; align-items: center; justify-content: space-between; padding: var(--space-4, 16px) var(--space-4, 16px) 12px; border-bottom: 1px solid var(--neutral-100, #F1F5F9); gap: var(--space-3, 12px); }
.card-head .ttl { display: flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 600; color: var(--neutral-900, #0F172A); }
.card-head .ttl-ico { width: 24px; height: 24px; border-radius: 4px; background: rgba(37,99,235,0.06); color: #2563EB; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.card-head .ttl-meta { font-size: 12px; color: var(--neutral-500, #64748B); font-weight: 400; font-family: var(--font-mono, monospace); }
.card-head .tools { display: flex; align-items: center; gap: 6px; }
.tool-btn { height: 26px; padding: 0 8px; border: 1px solid var(--neutral-200, #E2E8F0); background: #fff; border-radius: 4px; font-size: 12px; color: var(--neutral-500, #64748B); cursor: pointer; font-family: inherit; }

/* Tab 栏 */
.tab-bar { display: flex; align-items: center; gap: 2px; padding: 0 var(--space-4, 16px); border-bottom: 1px solid var(--neutral-100, #F1F5F9); }
.tab-btn { height: 36px; padding: 0 12px; border: 0; background: transparent; font-size: 13px; color: var(--neutral-500, #64748B); cursor: pointer; font-family: inherit; border-bottom: 2px solid transparent; margin-bottom: -1px; transition: color 0.1s, border-color 0.1s; }
.tab-btn:hover { color: var(--neutral-900, #0F172A); }
.tab-btn.active { color: #2563EB; border-bottom-color: #2563EB; font-weight: 500; }

/* 端口暴露面分栏 */
.port-split { display: grid; grid-template-columns: 1fr 1fr; gap: 0; }
.port-split .ps-divider { width: 1px; background: var(--neutral-100, #F1F5F9); margin: var(--space-4, 16px) 0; }
.split-label { padding: 10px var(--space-4, 16px) 4px; font-size: 11px; font-weight: 600; color: var(--neutral-400, #94A3B8); text-transform: uppercase; letter-spacing: 0.04em; }

/* 危险端口告警 */
.sev-counts { display: flex; align-items: center; gap: 6px; }
.sev-tag { display: inline-flex; align-items: center; gap: 4px; font-size: 12px; font-weight: 600; font-family: var(--font-mono, monospace); padding: 2px 8px; border-radius: 4px; }
.sev-tag.h { background: rgba(220,38,38,0.08); color: #DC2626; }
.sev-tag.m { background: rgba(234,88,12,0.08); color: #EA580C; }
.alert-thead { display: flex; align-items: center; padding: 6px var(--space-4, 16px); gap: var(--space-3, 12px); background: var(--neutral-50, #F8FAFC); border-bottom: 1px solid var(--neutral-100, #F1F5F9); font-size: 11px; font-weight: 600; color: var(--neutral-500, #64748B); letter-spacing: 0.03em; text-transform: uppercase; }
.alert-thead .th-ip { min-width: 120px; } .alert-thead .th-port { min-width: 72px; } .alert-thead .th-svc { flex: 1; } .alert-thead .th-zone { min-width: 60px; } .alert-thead .th-lvl { min-width: 56px; }
.alert-table-wrap { position: relative; overflow: hidden; }
.alert-list { list-style: none; margin: 0; padding: 0; overflow-y: auto; height: 340px; }
.alert-list::-webkit-scrollbar { width: 4px; } .alert-list::-webkit-scrollbar-thumb { background: #E2E8F0; border-radius: 2px; }
.alert-row { display: flex; align-items: center; padding: 8px var(--space-4, 16px); gap: var(--space-3, 12px); border-bottom: 1px solid var(--neutral-50, #F8FAFC); }
.alert-row:last-child { border-bottom: 0; } .alert-row:hover { background: var(--neutral-50, #F8FAFC); }
.alert-row .sev-bar { width: 3px; height: 32px; border-radius: 2px; flex-shrink: 0; }
.alert-row.high .sev-bar { background: #DC2626; } .alert-row.med .sev-bar { background: #EA580C; }
.alert-row .ip { font-family: var(--font-mono, monospace); font-size: 12px; font-weight: 500; color: #0F172A; min-width: 120px; }
.alert-row .port { font-family: var(--font-mono, monospace); font-size: 12px; color: #334155; min-width: 72px; }
.alert-row .svc { font-size: 12px; color: #64748B; flex: 1; }
.alert-row .zone { font-size: 11px; padding: 2px 6px; border-radius: 4px; background: #F1F5F9; color: #475569; white-space: nowrap; flex-shrink: 0; }
.alert-row .lvl { flex-shrink: 0; font-size: 11px; font-weight: 600; padding: 2px 7px; border-radius: 4px; }
.alert-row.high .lvl { background: rgba(220,38,38,0.08); color: #DC2626; } .alert-row.med .lvl { background: rgba(234,88,12,0.08); color: #EA580C; }
@keyframes rowPulse { 0%,100%{ background: transparent; } 50%{ background: rgba(220,38,38,0.04); } }
.alert-row.high { animation: rowPulse 3s ease-in-out infinite; } .alert-row.high:hover { animation: none; background: var(--neutral-50, #F8FAFC); }
</style>
