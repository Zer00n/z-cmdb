<script setup lang="ts">
/**
 * 成本总览 — 对齐 Cost Overview 设计稿
 */
import { ref, computed, shallowRef, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useDebounceFn, useEventListener } from '@vueuse/core'
import { fetchCostSummary } from '@/api/cost'
import type { CostSummary, GovernanceItem } from '@/api/cost'
import { useCostCurrency } from '@/composables/useCostCurrency'
import { useTimeFormat } from '@/composables/useTimeFormat'
import * as echarts from 'echarts/core'
import { BarChart, PieChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([BarChart, PieChart, LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const { t, tm, locale } = useI18n()
const router = useRouter()
const { currency, symbol, loadCurrency, formatMoney, formatCompact, formatCompactInt } = useCostCurrency()
const { currentMonth, recentMonths: getRecentMonths, nowFormatted, now } = useTimeFormat()

// ── Data ──────────────────────────────────────────────────
const loading = ref(true)
const data = ref<CostSummary | null>(null)

// ── Period selector ───────────────────────────────────────
const selectedPeriod = ref(currentMonth())
const showPeriodPicker = ref(false)

const periodLabel = computed(() => selectedPeriod.value)

function selectPeriod(month: string) {
  selectedPeriod.value = month
  showPeriodPicker.value = false
  loadData()
}

function shiftPeriod(delta: number) {
  const base = now()
  const [y, m] = selectedPeriod.value.split('-').map(Number)
  selectedPeriod.value = base.year(y).month(m - 1).add(delta, 'month').format('YYYY-MM')
  loadData()
}

// Recent 12 months for dropdown
const recentMonths = computed(() => getRecentMonths(12))

// ── Governance tabs ───────────────────────────────────────
type GovTab = 'all' | 'shadow_cost' | 'low_utilization' | 'depreciation_expiring' | 'missing_data'
const govTab = ref<GovTab>('all')

const govTabs = computed(() => [
  { key: 'all' as GovTab, label: t('cost.overview.govAll'), filter: '' },
  { key: 'shadow_cost' as GovTab, label: t('cost.overview.govShadow'), filter: 'shadow_cost' },
  { key: 'low_utilization' as GovTab, label: t('cost.overview.govUtilization'), filter: 'low_utilization' },
  { key: 'depreciation_expiring' as GovTab, label: t('cost.overview.govExpiring'), filter: 'depreciation_expiring' },
  { key: 'missing_data' as GovTab, label: t('cost.overview.govMissing'), filter: 'missing_data' },
])

const filteredGovernance = computed(() => {
  if (!data.value) return []
  const items = data.value.governance
  if (govTab.value === 'all') return items
  const tab = govTabs.value.find(t => t.key === govTab.value)
  if (!tab) return items
  return items.filter(item => item.type === tab.filter)
})

// ── Helpers ───────────────────────────────────────────────
function formatCurrency(val: number): string {
  return formatMoney(val)
}

function severityClass(sev: string): string {
  if (sev === 'critical') return 'critical'
  if (sev === 'warning') return 'warning'
  return 'info'
}

function govTagClass(item: GovernanceItem): string {
  return severityClass(item.severity)
}

function govTagLabel(item: GovernanceItem): string {
  if (item.type === 'shadow_cost') return t('cost.overview.govShadow')
  if (item.type === 'low_utilization') return t('cost.overview.govUtilization')
  if (item.type === 'depreciation_expiring') return t('cost.overview.govExpiring')
  if (item.type === 'missing_data') return t('cost.overview.govMissing')
  return item.type
}

// ── KPI definitions ───────────────────────────────────────
const kpis = computed(() => {
  if (!data.value) return []
  const d = data.value
  return [
    {
      label: t('cost.overview.monthlyTotal'),
      value: formatCurrency(d.total_monthly),
      cssClass: 'accent',
      dotColor: '#2563EB',
      deltaText: `${t('cost.overview.vsLastMonth')}`,
      deltaClass: 'up',
    },
    {
      label: t('cost.overview.annualized'),
      value: formatMoney(d.annualized),
      unit: 'K',
      cssClass: '',
      dotColor: '#8B5CF6',
      deltaText: t('cost.overview.basedOnCurrentRate'),
      deltaClass: 'neutral',
    },
    {
      label: t('cost.overview.capexRatio'),
      value: d.capex_ratio.toFixed(1),
      unit: '%',
      cssClass: '',
      dotColor: '#0891B2',
      deltaText: `${formatCurrency(d.capex_monthly)} ${t('cost.overview.perMonth')}`,
      deltaClass: 'neutral',
    },
    {
      label: t('cost.overview.opexRatio'),
      value: d.opex_ratio.toFixed(1),
      unit: '%',
      cssClass: '',
      dotColor: '#16A34A',
      deltaText: `${formatCurrency(d.opex_monthly)} ${t('cost.overview.perMonth')}`,
      deltaClass: 'neutral',
    },
    {
      label: t('cost.overview.newAssets'),
      value: String(d.new_cost_assets),
      unit: '',
      cssClass: 'warn',
      dotColor: '#D97706',
      deltaText: t('cost.overview.vsLastMonth'),
      deltaClass: 'up',
    },
    {
      label: t('cost.overview.missingData'),
      value: String(d.missing_cost_data),
      unit: '',
      cssClass: 'danger-soft',
      dotColor: '#DC2626',
      deltaText: '',
      deltaClass: 'up',
    },
  ]
})

// ── ECharts ───────────────────────────────────────────────
const deptRankEl = ref<HTMLElement>()
const typeDonutEl = ref<HTMLElement>()
const cloudBarEl = ref<HTMLElement>()
const trendLineEl = ref<HTMLElement>()

const chartDeptRank = shallowRef<echarts.ECharts | null>(null)
const chartTypeDonut = shallowRef<echarts.ECharts | null>(null)
const chartCloudBar = shallowRef<echarts.ECharts | null>(null)
const chartTrendLine = shallowRef<echarts.ECharts | null>(null)

const TOOLTIP = {
  backgroundColor: '#fff',
  borderColor: '#E2E8F0',
  borderWidth: 1,
  textStyle: { color: '#334155', fontSize: 12 },
}

const COLORS = {
  primary: '#2563EB',
  primary2: '#5A82F4',
  cyan: '#0891B2',
  amber: '#D97706',
  orange: '#EA580C',
  purple: '#8B5CF6',
  slate: '#94A3B8',
  gridLine: '#F1F5F9',
  axisLabel: '#64748B',
  catLabel: '#334155',
}

// Blue gradient for horizontal bar
const BAR_GRADIENT = ['#DBE5FE', '#BFDBFE', '#93C5FD', '#60A5FA', '#3B82F6', '#2563EB']

function renderDeptRank() {
  if (!deptRankEl.value || !data.value) return
  if (!chartDeptRank.value) chartDeptRank.value = echarts.init(deptRankEl.value)
  const ranking = data.value.dept_ranking
  const categories = ranking.map(r => r.name)
  const values = ranking.map(r => r.monthly_cost)
  const barData = values.map((v, i) => ({
    value: v,
    itemStyle: {
      color: BAR_GRADIENT[Math.min(i, BAR_GRADIENT.length - 1)],
      borderRadius: [0, 4, 4, 0],
    },
  }))
  chartDeptRank.value.setOption({
    backgroundColor: 'transparent',
    animation: true,
    animationDuration: 900,
    tooltip: {
      ...TOOLTIP,
      trigger: 'axis',
      axisPointer: { type: 'none' },
      formatter: (p: any) =>
        `${p[0].name}<br/>${t('cost.overview.monthlyTotal')}：<b>${formatCurrency(p[0].value)}</b>`,
    },
    grid: { left: 72, right: 60, top: 8, bottom: 28 },
    xAxis: {
      type: 'value',
      axisLabel: {
        fontSize: 11,
        color: COLORS.axisLabel,
        formatter: (v: number) => formatCompactInt(v),
      },
      splitLine: { lineStyle: { color: COLORS.gridLine } },
    },
    yAxis: {
      type: 'category',
      axisLabel: { fontSize: 13, color: COLORS.catLabel },
      data: categories,
    },
    series: [
      {
        type: 'bar',
        barMaxWidth: 20,
        label: {
          show: true,
          position: 'right',
          formatter: (p: any) => formatCompact(p.value),
          fontSize: 12,
          color: COLORS.axisLabel,
        },
        data: barData,
      },
    ],
  }, { notMerge: true })
}

function renderTypeDonut() {
  if (!typeDonutEl.value || !data.value) return
  if (!chartTypeDonut.value) chartTypeDonut.value = echarts.init(typeDonutEl.value)
  const breakdown = data.value.type_breakdown
  const palette = [COLORS.primary, COLORS.primary2, COLORS.cyan, COLORS.amber, COLORS.orange, COLORS.purple, COLORS.slate]
  const chartData = breakdown.map((item, i) => ({
    name: item.name,
    value: item.value,
    itemStyle: { color: palette[i % palette.length] },
  }))
  chartTypeDonut.value.setOption({
    backgroundColor: 'transparent',
    animation: true,
    animationDuration: 700,
    tooltip: {
      ...TOOLTIP,
      trigger: 'item',
      formatter: (p: any) =>
        `<b>${p.name}</b><br/>${formatCurrency(p.value)} &nbsp;(${p.percent}%)`,
    },
    legend: {
      orient: 'vertical',
      right: 0,
      top: 'center',
      textStyle: { fontSize: 12, color: COLORS.catLabel },
      itemWidth: 9,
      itemHeight: 9,
    },
    series: [
      {
        type: 'pie',
        radius: ['44%', '70%'],
        center: ['38%', '50%'],
        data: chartData,
        itemStyle: { borderWidth: 2, borderColor: '#ffffff' },
        label: { show: false },
        emphasis: { scale: true, scaleSize: 5 },
      },
    ],
  }, { notMerge: true })
}

function renderCloudBar() {
  if (!cloudBarEl.value || !data.value) return
  if (!chartCloudBar.value) chartCloudBar.value = echarts.init(cloudBarEl.value)
  // Mock months label — in real app these would come from API
  const months = tm('cost.overview.months') as string[]
  const idcData = [95000, 95500, 96500, 97800, 97200, 96500]
  const cloudData = [8500, 9200, 9800, 10200, 11200, 10500]
  chartCloudBar.value.setOption({
    backgroundColor: 'transparent',
    animation: true,
    animationDuration: 900,
    tooltip: {
      ...TOOLTIP,
      trigger: 'axis',
      formatter: (p: any) =>
        `${p[0].axisValue}<br/>` +
        p.map((s: any) => `${s.marker}${s.seriesName}：<b>${formatCurrency(s.value)}</b>`).join('<br/>'),
    },
    legend: { bottom: 0, textStyle: { fontSize: 12 } },
    grid: { left: 56, right: 16, top: 8, bottom: 36 },
    xAxis: { data: months, axisLabel: { fontSize: 12, color: COLORS.axisLabel } },
    yAxis: {
      axisLabel: {
        fontSize: 11,
        color: COLORS.axisLabel,
        formatter: (v: number) => formatCompactInt(v),
      },
      splitLine: { lineStyle: { color: COLORS.gridLine } },
    },
    series: [
      {
        name: t('cost.overview.localIdc'),
        type: 'bar',
        barMaxWidth: 22,
        barGap: '10%',
        itemStyle: { color: COLORS.primary, borderRadius: [4, 4, 0, 0] },
        data: idcData,
      },
      {
        name: t('cost.overview.cloud'),
        type: 'bar',
        barMaxWidth: 22,
        itemStyle: { color: COLORS.purple, borderRadius: [4, 4, 0, 0] },
        data: cloudData,
      },
    ],
  }, { notMerge: true })
}

function renderTrendLine() {
  if (!trendLineEl.value || !data.value) return
  if (!chartTrendLine.value) chartTrendLine.value = echarts.init(trendLineEl.value)
  const months = tm('cost.overview.months') as string[]
  const trendData = [103500, 104700, 106300, 108000, 108400, 107000]
  chartTrendLine.value.setOption({
    backgroundColor: 'transparent',
    animation: true,
    animationDuration: 900,
    tooltip: {
      ...TOOLTIP,
      trigger: 'axis',
      formatter: (p: any) =>
        `${p[0].axisValue}<br/>${t('cost.overview.monthlyTotal')}：<b>${formatCurrency(p[0].value)}</b>`,
    },
    grid: { left: 60, right: 16, top: 12, bottom: 28 },
    xAxis: { data: months, axisLabel: { fontSize: 12, color: COLORS.axisLabel } },
    yAxis: {
      min: 95000,
      axisLabel: {
        fontSize: 11,
        color: COLORS.axisLabel,
        formatter: (v: number) => formatCompact(v),
      },
      splitLine: { lineStyle: { color: COLORS.gridLine } },
    },
    series: [
      {
        type: 'line',
        smooth: 0.4,
        symbol: 'circle',
        symbolSize: 7,
        itemStyle: { color: COLORS.primary, borderWidth: 2, borderColor: '#fff' },
        lineStyle: { color: COLORS.primary, width: 2.5 },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(37,99,235,0.14)' },
              { offset: 1, color: 'rgba(37,99,235,0)' },
            ],
          },
        },
        data: trendData,
      },
    ],
  }, { notMerge: true })
}

function renderAllCharts() {
  renderDeptRank()
  renderTypeDonut()
  renderCloudBar()
  renderTrendLine()
}

// Re-render on language change
watch(locale, () => nextTick(renderAllCharts))

// Resize debounce
const handleResize = useDebounceFn(() => {
  chartDeptRank.value?.resize()
  chartTypeDonut.value?.resize()
  chartCloudBar.value?.resize()
  chartTrendLine.value?.resize()
}, 150)
useEventListener(window, 'resize', handleResize)

// ── Fetch & mount ─────────────────────────────────────────
async function loadData() {
  loading.value = true
  try {
    data.value = await fetchCostSummary()
    await nextTick()
    renderAllCharts()
  } catch (e) {
    console.error('[CostOverview] fetch error:', e)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadCurrency()
  loadData()
})

// ── CSV Export ────────────────────────────────────────────
function exportCSV() {
  if (!data.value) return
  const d = data.value
  const lines: string[] = []

  // KPI section
  lines.push(`=== ${t('cost.overview.csvKpi')} ===`)
  lines.push(`${t('cost.overview.csvPeriod')},${selectedPeriod.value}`)
  lines.push(`${t('cost.overview.csvMonthlyTotal')},${currency.value} ${d.total_monthly}`)
  lines.push(`${t('cost.overview.csvAnnualized')},${currency.value} ${d.annualized}`)
  lines.push(`${t('cost.overview.csvCapexRatio')},${d.capex_ratio}%`)
  lines.push(`${t('cost.overview.csvOpexRatio')},${d.opex_ratio}%`)
  lines.push(`${t('cost.overview.csvMissingData')},${d.missing_cost_data}`)
  lines.push('')

  // Department ranking
  lines.push(`=== ${t('cost.overview.csvDeptRanking')} ===`)
  lines.push(`${t('cost.overview.csvDept')},${t('cost.overview.csvMonthlyCost')} (${currency.value})`)
  for (const dept of d.dept_ranking) {
    lines.push(`${dept.name},${dept.monthly_cost}`)
  }
  lines.push('')

  // Type breakdown
  lines.push(`=== ${t('cost.overview.csvTypeBreakdown')} ===`)
  lines.push(`${t('cost.overview.csvAssetType')},${t('cost.overview.csvMonthlyCost')} (${currency.value})`)
  for (const item of d.type_breakdown) {
    lines.push(`${item.name},${item.value}`)
  }
  lines.push('')

  // Governance
  if (d.governance.length) {
    lines.push(`=== ${t('cost.overview.csvGovernance')} ===`)
    lines.push(`${t('cost.overview.csvGovType')},${t('cost.overview.csvGovSeverity')},${t('cost.overview.csvGovAsset')},${t('cost.overview.csvGovMessage')}`)
    for (const g of d.governance) {
      lines.push(`${g.type},${g.severity},${g.asset_no || '-'},${g.message}`)
    }
  }

  const blob = new Blob(['﻿' + lines.join('\n')], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `cost_overview_${selectedPeriod.value}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

onUnmounted(() => {
  chartDeptRank.value?.dispose()
  chartTypeDonut.value?.dispose()
  chartCloudBar.value?.dispose()
  chartTrendLine.value?.dispose()
})
</script>

<template>
  <div class="cost-overview" v-loading="loading">
    <!-- Page head -->
    <div class="page-head">
      <div>
        <h1>{{ t('cost.overview.title') }}</h1>
        <div class="sub">
          {{ t('cost.overview.subtitle', {
            period: periodLabel,
            date: nowFormatted('MM-DD HH:mm'),
            currency: currency,
          }) }}
        </div>
      </div>
      <div class="actions">
        <el-dropdown trigger="click" @command="selectPeriod">
          <button class="btn sm">
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6.5l4 4 4-4"/></svg>
            {{ periodLabel }}
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item
                v-for="m in recentMonths"
                :key="m"
                :command="m"
                :class="{ 'is-active': m === selectedPeriod }"
              >{{ m }}</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <button class="btn sm primary" @click="exportCSV">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M8 2.5v8M4.5 7L8 10.5 11.5 7"/><path d="M2.5 13h11"/></svg>
          {{ t('cost.overview.exportReport') }}
        </button>
      </div>
    </div>

    <!-- KPI strip -->
    <div class="kpi-strip" v-if="kpis.length">
      <div
        v-for="(kpi, i) in kpis"
        :key="i"
        :class="['kpi-card', kpi.cssClass]"
      >
        <div class="k-label">
          <span class="k-dot" :style="{ background: kpi.dotColor }" />
          {{ kpi.label }}
        </div>
        <div class="k-val">
          {{ kpi.value }}<span v-if="kpi.unit" class="k-unit">{{ kpi.unit }}</span>
        </div>
        <div v-if="kpi.deltaText" :class="['k-delta', kpi.deltaClass]">
          {{ kpi.deltaText }}
        </div>
      </div>
    </div>

    <!-- Charts 2x2 -->
    <div class="charts-grid">
      <!-- Dept cost ranking -->
      <div class="chart-card">
        <div class="cc-head">
          <span class="cc-title">{{ t('cost.overview.deptRanking') }}</span>
          <span class="cc-sub">{{ t('cost.overview.monthlyTotal') }} · {{ currency }}</span>
        </div>
        <div ref="deptRankEl" style="height: 240px;" />
      </div>

      <!-- Asset type donut -->
      <div class="chart-card">
        <div class="cc-head">
          <span class="cc-title">{{ t('cost.overview.typeDonut') }}</span>
          <span class="cc-sub">{{ t('cost.overview.typeDonutSub') }}</span>
        </div>
        <div ref="typeDonutEl" style="height: 240px;" />
      </div>

      <!-- Cloud vs on-prem -->
      <div class="chart-card">
        <div class="cc-head">
          <span class="cc-title">{{ t('cost.overview.cloudVsLocal') }}</span>
          <span class="cc-sub">{{ t('cost.overview.cloudVsLocalSub', { currency: currency }) }}</span>
        </div>
        <div ref="cloudBarEl" style="height: 220px;" />
      </div>

      <!-- Cost trend -->
      <div class="chart-card">
        <div class="cc-head">
          <span class="cc-title">{{ t('cost.overview.costTrend') }}</span>
          <span class="cc-sub">{{ t('cost.overview.costTrendSub', { currency: currency }) }}</span>
        </div>
        <div ref="trendLineEl" style="height: 220px;" />
      </div>
    </div>

    <!-- Governance section -->
    <div class="gov-section">
      <div class="gov-head">
        <h3>{{ t('cost.overview.governance') }}</h3>
        <div class="gov-right">
          <div class="gh-tabs">
            <button
              v-for="tab in govTabs"
              :key="tab.key"
              :class="['gov-tab', { active: govTab === tab.key }]"
              @click="govTab = tab.key"
            >
              {{ tab.label }}
            </button>
          </div>
          <span class="gov-count" v-if="data">
            {{ t('cost.overview.itemsNeedAction', { count: data.governance_count }) }}
          </span>
        </div>
      </div>

      <template v-if="filteredGovernance.length">
        <div
          v-for="(item, idx) in filteredGovernance"
          :key="idx"
          class="gov-item"
        >
          <div :class="['gov-sev', severityClass(item.severity)]" />
          <div class="gov-body">
            <div class="gov-title">
              <span>{{ item.asset_no || item.message }}</span>
              <span :class="['gov-tag', govTagClass(item)]">{{ govTagLabel(item) }}</span>
              <span
                v-if="item.severity === 'critical'"
                :class="['gov-tag', 'critical']"
              >
                {{ item.severity === 'critical' ? t('cost.overview.severityCritical') : t('cost.overview.severityWarning') }}
              </span>
            </div>
            <div class="gov-meta">{{ item.message }}</div>
          </div>
          <div class="gov-actions">
            <template v-if="item.type === 'shadow_cost'">
              <button class="btn sm">{{ t('cost.overview.stopBilling') }}</button>
              <button class="btn sm btn-ghost" @click="item.asset_id && router.push(`/assets/${item.asset_id}`)">{{ t('cost.overview.viewDetail') }}</button>
            </template>
            <template v-else-if="item.type === 'low_utilization'">
              <button class="btn sm">{{ t('cost.overview.createTicket') }}</button>
              <button class="btn sm btn-ghost">{{ t('cost.overview.dismiss') }}</button>
            </template>
            <template v-else-if="item.type === 'depreciation_expiring'">
              <button class="btn sm">{{ t('cost.overview.selectStrategy') }}</button>
              <button class="btn sm btn-ghost" @click="item.asset_id && router.push(`/assets/${item.asset_id}`)">{{ t('cost.overview.viewDetail') }}</button>
            </template>
            <template v-else-if="item.type === 'missing_data'">
              <button class="btn sm" @click="router.push('/assets')">{{ t('cost.overview.batchFill') }}</button>
              <button class="btn sm btn-ghost" @click="router.push('/assets')">{{ t('cost.overview.viewList') }}</button>
            </template>
            <template v-else>
              <button class="btn sm" @click="item.asset_id && router.push(`/assets/${item.asset_id}`)">{{ t('cost.overview.viewDetail') }}</button>
            </template>
          </div>
        </div>
      </template>
      <div v-else class="gov-empty">
        {{ t('cost.overview.noGovernanceItems') }}
      </div>
    </div>

    <div style="height: var(--space-6);" />
  </div>
</template>

<style scoped>
.cost-overview { max-width: 1400px; }

/* ── Page head ──────────────────────────────────────────── */
.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: var(--space-6);
}
.page-head h1 {
  margin: 0;
  font-size: var(--fs-h2, 22px);
  font-weight: 700;
  color: var(--neutral-900);
  line-height: var(--lh-h2, 1.3);
}
.page-head .sub {
  margin-top: 4px;
  font-size: var(--fs-caption, 12px);
  color: var(--neutral-500);
  font-family: var(--font-mono, monospace);
}
.actions {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
}
.btn {
  height: 36px;
  border-radius: var(--radius-md, 6px);
  padding: 0 14px;
  font-size: var(--fs-body, 14px);
  border: 1px solid var(--neutral-300, #CBD5E1);
  background: var(--neutral-0, #fff);
  color: var(--neutral-700, #334155);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: background-color 0.12s, border-color 0.12s, color 0.12s;
  white-space: nowrap;
  font-family: inherit;
}
.btn:hover {
  background: var(--neutral-50, #F8FAFC);
  border-color: var(--neutral-400, #94A3B8);
}
.btn.primary {
  background: var(--color-primary-500, #2563EB);
  border-color: var(--color-primary-500, #2563EB);
  color: #fff;
}
.btn.primary:hover { background: var(--color-primary-600, #1D4ED8); }
.btn.sm { height: 32px; padding: 0 10px; font-size: 13px; }
.btn-ghost {
  border: 0;
  background: transparent;
  color: var(--neutral-500, #64748B);
}
.btn-ghost:hover { color: var(--neutral-900, #0F172A); }

/* ── KPI strip ──────────────────────────────────────────── */
.kpi-strip {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: var(--space-4, 16px);
  margin-bottom: var(--space-6, 24px);
}
.kpi-card {
  background: var(--neutral-0, #fff);
  border: 1px solid var(--neutral-200, #E2E8F0);
  border-radius: var(--radius-lg, 10px);
  padding: var(--space-4, 16px);
}
.kpi-card .k-label {
  font-size: var(--fs-caption, 12px);
  color: var(--neutral-500, #64748B);
  margin-bottom: 5px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.kpi-card .k-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.kpi-card .k-val {
  font-size: 24px;
  line-height: 32px;
  font-weight: 700;
  color: var(--neutral-900, #0F172A);
  font-family: var(--font-mono, monospace);
  letter-spacing: -0.02em;
}
.kpi-card .k-val .k-unit {
  font-size: 14px;
  font-weight: 400;
  color: var(--neutral-500, #64748B);
  margin-left: 2px;
}
.kpi-card .k-delta {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 12px;
  margin-top: 4px;
  font-family: var(--font-mono, monospace);
}
.kpi-card .k-delta.up { color: #B45309; }
.kpi-card .k-delta.down { color: #15803D; }
.kpi-card .k-delta.neutral { color: var(--neutral-500, #64748B); }
.kpi-card.accent {
  border-color: var(--color-primary-200, #BFDBFE);
  background: linear-gradient(135deg, var(--color-primary-50, #EFF6FF) 0%, #fff 100%);
}
.kpi-card.accent .k-val { color: var(--color-primary-700, #1D4ED8); }
.kpi-card.warn {
  border-color: #FDE68A;
  background: #FFFBEB;
}
.kpi-card.warn .k-val { color: #B45309; }
.kpi-card.danger-soft {
  border-color: #FECDD3;
  background: #FFF1F2;
}
.kpi-card.danger-soft .k-val { color: #B91C1C; }

/* ── Charts grid ────────────────────────────────────────── */
.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4, 16px);
  margin-bottom: var(--space-6, 24px);
}
.chart-card {
  background: var(--neutral-0, #fff);
  border: 1px solid var(--neutral-200, #E2E8F0);
  border-radius: var(--radius-lg, 10px);
  padding: var(--space-4, 16px) var(--space-6, 24px);
  overflow: hidden;
}
.chart-card .cc-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4, 16px);
}
.chart-card .cc-title {
  font-size: var(--fs-body, 14px);
  font-weight: 600;
  color: var(--neutral-900, #0F172A);
}
.chart-card .cc-sub {
  font-size: var(--fs-caption, 12px);
  color: var(--neutral-500, #64748B);
}

/* ── Governance section ─────────────────────────────────── */
.gov-section {
  background: var(--neutral-0, #fff);
  border: 1px solid var(--neutral-200, #E2E8F0);
  border-radius: var(--radius-lg, 10px);
  overflow: hidden;
}
.gov-head {
  padding: var(--space-4, 16px) var(--space-6, 24px);
  border-bottom: 1px solid var(--neutral-200, #E2E8F0);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.gov-head h3 {
  margin: 0;
  font-size: var(--fs-h4, 16px);
  font-weight: 600;
  color: var(--neutral-900, #0F172A);
  line-height: var(--lh-h4, 1.4);
}
.gov-right {
  display: flex;
  align-items: center;
  gap: var(--space-4, 16px);
}
.gh-tabs {
  display: flex;
  gap: 2px;
  background: var(--neutral-100, #F1F5F9);
  border-radius: var(--radius-md, 6px);
  padding: 3px;
}
.gov-tab {
  padding: 4px 12px;
  border-radius: var(--radius-sm, 4px);
  font-size: 13px;
  color: var(--neutral-600, #475569);
  cursor: pointer;
  border: 0;
  background: transparent;
  font-family: inherit;
  transition: background-color 0.12s, color 0.12s;
}
.gov-tab:hover { color: var(--neutral-900, #0F172A); }
.gov-tab.active {
  background: var(--neutral-0, #fff);
  color: var(--neutral-900, #0F172A);
  font-weight: 500;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}
.gov-count {
  font-size: var(--fs-caption, 12px);
  color: var(--neutral-500, #64748B);
  font-family: var(--font-mono, monospace);
}
.gov-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-4, 16px);
  padding: var(--space-4, 16px) var(--space-6, 24px);
  border-bottom: 1px solid var(--neutral-100, #F1F5F9);
}
.gov-item:last-child { border-bottom: 0; }
.gov-sev {
  width: 4px;
  align-self: stretch;
  border-radius: 2px;
  flex-shrink: 0;
  margin-top: 2px;
}
.gov-sev.critical { background: var(--color-danger, #DC2626); }
.gov-sev.warning { background: var(--color-warning, #D97706); }
.gov-sev.info { background: var(--color-info, #0891B2); }
.gov-body {
  flex: 1;
  min-width: 0;
}
.gov-title {
  font-size: var(--fs-body, 14px);
  font-weight: 500;
  color: var(--neutral-900, #0F172A);
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  flex-wrap: wrap;
}
.gov-meta {
  font-size: var(--fs-caption, 12px);
  color: var(--neutral-500, #64748B);
  margin-top: 3px;
  font-family: var(--font-mono, monospace);
}
.gov-tag {
  display: inline-flex;
  align-items: center;
  font-size: 11px;
  padding: 1px 7px;
  border-radius: 3px;
  white-space: nowrap;
}
.gov-tag.critical {
  background: rgba(220, 38, 38, 0.08);
  color: #B91C1C;
}
.gov-tag.warning {
  background: rgba(217, 119, 6, 0.08);
  color: #B45309;
}
.gov-tag.info {
  background: rgba(8, 145, 178, 0.08);
  color: #0E7490;
}
.gov-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  flex-shrink: 0;
}
.gov-empty {
  padding: var(--space-6, 24px);
  text-align: center;
  color: var(--neutral-400, #94A3B8);
  font-size: 14px;
}

/* ── Responsive ─────────────────────────────────────────── */
@media (max-width: 1280px) {
  .kpi-strip { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 768px) {
  .kpi-strip { grid-template-columns: repeat(2, 1fr); }
  .charts-grid { grid-template-columns: 1fr; }
  .page-head { flex-direction: column; align-items: flex-start; gap: var(--space-3, 12px); }
  .gov-head { flex-direction: column; align-items: flex-start; gap: var(--space-3, 12px); }
  .gov-item { flex-direction: column; }
  .gov-actions { align-self: flex-end; }
}
</style>
