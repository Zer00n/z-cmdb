<script setup lang="ts">
/**
 * 部门账单 — 对齐 Department Billing 设计稿
 */
import { ref, computed, shallowRef, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useDebounceFn, useEventListener } from '@vueuse/core'
import * as echarts from 'echarts/core'
import { PieChart, BarChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { ElTable, ElTableColumn } from 'element-plus'
import {
  fetchDepartments,
  fetchDepartmentBill,
  type Department,
  type DepartmentBill,
} from '@/api/cost'
import { useCostCurrency } from '@/composables/useCostCurrency'
import { useTimeFormat } from '@/composables/useTimeFormat'

echarts.use([PieChart, BarChart, TooltipComponent, LegendComponent, GridComponent, CanvasRenderer])

const { t, locale } = useI18n()
const { currency, symbol, loadCurrency, formatMoney, formatMoneyDecimal, formatCompact } = useCostCurrency()
const { today, nowFormatted } = useTimeFormat()

// ── State ────────────────────────────────────────────────
const departments = ref<Department[]>([])
const deptSearch = ref('')
const selectedDeptId = ref<number | null>(null)
const period = ref<'day' | 'month' | 'year' | 'custom'>('month')
const billing = ref<DepartmentBill | null>(null)
const loading = ref(false)

// ── Computed ─────────────────────────────────────────────
const filteredDepts = computed(() => {
  const q = deptSearch.value.trim().toLowerCase()
  if (!q) return departments.value
  return departments.value.filter(d => d.name.toLowerCase().includes(q))
})

const selectedDeptName = computed(() => {
  const dept = departments.value.find(d => d.id === selectedDeptId.value)
  return dept?.name ?? ''
})

const billingResources = computed(() => billing.value?.resources ?? [])

const totals = computed(() => {
  const resources = billingResources.value
  if (!resources.length) return { monthly_cost: 0, daily_rate: 0, period_amount: 0 }
  return {
    monthly_cost: resources.reduce((s, r) => s + r.monthly_cost, 0),
    daily_rate: resources.reduce((s, r) => s + r.daily_rate, 0),
    period_amount: resources.reduce((s, r) => s + r.period_amount, 0),
  }
})

// ── Date helpers ─────────────────────────────────────────
function formatDate(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function getDateRange(p: typeof period.value): { from: string; to: string } {
  const todayStr = today()
  switch (p) {
    case 'day':
      return { from: todayStr, to: todayStr }
    case 'year': {
      const from = `${todayStr.slice(0, 4)}-01-01`
      return { from, to: todayStr }
    }
    case 'custom':
      // Not implemented — show current month
    case 'month':
    default: {
      const from = `${todayStr.slice(0, 7)}-01`
      return { from, to: todayStr }
    }
  }
}

function formatMonth(date: string): string {
  if (!date) return ''
  return date.slice(0, 7) // "2026-06"
}

// ── Money formatter ──────────────────────────────────────
function fmtMoney(v: number): string {
  return formatMoney(v)
}

function fmtMoneyDecimal(v: number): string {
  return formatMoneyDecimal(v)
}

// ── Data fetch ───────────────────────────────────────────
async function loadDepartments() {
  departments.value = await fetchDepartments()
  if (departments.value.length && selectedDeptId.value === null) {
    selectedDeptId.value = departments.value[0].id
  }
}

async function loadBilling() {
  if (!selectedDeptId.value) return
  loading.value = true
  try {
    const { from, to } = getDateRange(period.value)
    billing.value = await fetchDepartmentBill(selectedDeptId.value, from, to, period.value === 'day' ? 'day' : 'month')
  } finally {
    loading.value = false
  }
}

// ── Period tabs ──────────────────────────────────────────
interface PeriodTab {
  key: 'day' | 'month' | 'year' | 'custom'
  label: string
}

const periodTabs = computed<PeriodTab[]>(() => [
  { key: 'day', label: t('cost.billing.periodDay') },
  { key: 'month', label: t('cost.billing.periodMonth') },
  { key: 'year', label: t('cost.billing.periodYear') },
  { key: 'custom', label: t('cost.billing.periodCustom') },
])

function selectPeriod(p: typeof period.value) {
  period.value = p
}

// ── ECharts ──────────────────────────────────────────────
const DONUT_COLORS = ['#8B5CF6', '#D97706', '#0891B2', '#94A3B8', '#EA580C']
const BAR_COLORS = ['#DBE5FE', '#B6CBFD', '#88A8FA', '#5A82F4', '#2563EB']

const donutEl = ref<HTMLElement>()
const barEl = ref<HTMLElement>()
const donutChart = shallowRef<echarts.ECharts | null>(null)
const barChart = shallowRef<echarts.ECharts | null>(null)

const TOOLTIP = { backgroundColor: '#fff', borderColor: '#E2E8F0', borderWidth: 1, textStyle: { color: '#334155', fontSize: 12 } }

function renderDonut() {
  if (!donutEl.value || !billing.value) return
  if (!donutChart.value) donutChart.value = echarts.init(donutEl.value)
  const entries = Object.entries(billing.value.cost_type_totals ?? {})
  const data = entries.map(([name, value], i) => ({
    name,
    value,
    itemStyle: { color: DONUT_COLORS[i % DONUT_COLORS.length] },
  }))
  donutChart.value.setOption({
    backgroundColor: 'transparent',
    animation: true,
    animationDuration: 700,
    tooltip: {
      ...TOOLTIP,
      trigger: 'item',
      formatter: (p: any) => `<b>${p.name}</b><br/>${fmtMoney(p.value)}&nbsp;(${p.percent}%)`,
    },
    legend: {
      orient: 'vertical',
      right: 8,
      top: 'center',
      itemWidth: 9,
      itemHeight: 9,
      textStyle: { fontSize: 12, color: '#334155' },
    },
    series: [
      {
        type: 'pie',
        radius: ['44%', '70%'],
        center: ['36%', '50%'],
        data,
        itemStyle: { borderWidth: 2, borderColor: '#ffffff' },
        label: { show: false },
        emphasis: { scale: true, scaleSize: 5 },
      },
    ],
  }, { notMerge: true })
}

function renderBar() {
  if (!barEl.value || !billing.value) return
  if (!barChart.value) barChart.value = echarts.init(barEl.value)
  // Sort resources by period_amount descending for ranking
  const sorted = [...(billing.value.resources ?? [])].sort((a, b) => b.period_amount - a.period_amount)
  const names = sorted.map(r => r.asset_no)
  const values = sorted.map(r => r.period_amount)
  barChart.value.setOption({
    backgroundColor: 'transparent',
    animation: true,
    animationDuration: 900,
    grid: { left: 110, right: 16, top: 10, bottom: 28 },
    tooltip: {
      ...TOOLTIP,
      trigger: 'axis',
      formatter: (p: any) => `${p[0].name}<br/>${t('cost.billing.periodAmount')}：<b>${fmtMoney(p[0].value)}</b>`,
    },
    xAxis: {
      type: 'value',
      axisLabel: { fontSize: 12, color: '#64748B', formatter: (v: number) => symbol.value + v.toLocaleString() },
    },
    yAxis: {
      type: 'category',
      inverse: true,
      axisLabel: { fontSize: 12, color: '#334155' },
      data: names,
    },
    series: [
      {
        type: 'bar',
        barMaxWidth: 18,
        data: values.map((v, i) => ({
          value: v,
          itemStyle: {
            color: i < BAR_COLORS.length ? BAR_COLORS[BAR_COLORS.length - 1 - Math.min(i, BAR_COLORS.length - 1)] : '#2563EB',
            borderRadius: [0, 4, 4, 0],
          },
        })),
      },
    ],
  }, { notMerge: true })
}

function renderAllCharts() {
  renderDonut()
  renderBar()
}

const handleResize = useDebounceFn(() => {
  donutChart.value?.resize()
  barChart.value?.resize()
}, 150)
useEventListener(window, 'resize', handleResize)

watch([billing, locale], () => nextTick(renderAllCharts))

// ── Type chip class ──────────────────────────────────────
function typeChipClass(assetType: string): string {
  const lower = assetType?.toLowerCase() ?? ''
  if (lower.includes('独占') || lower.includes('exclusive')) return 'type-exclusive'
  if (lower.includes('虚拟') || lower.includes('vm') || lower.includes('virtual')) return 'type-vm'
  return 'type-shared'
}

// ── Type label ───────────────────────────────────────────
function typeLabel(assetType: string): string {
  const lower = assetType?.toLowerCase() ?? ''
  if (lower.includes('独占') || lower.includes('exclusive')) return t('cost.billing.typeExclusive')
  if (lower.includes('虚拟') || lower.includes('vm') || lower.includes('virtual')) return t('cost.billing.typeVm')
  return t('cost.billing.typeShared')
}

// ── Data timestamp ───────────────────────────────────────
const dataTimestamp = computed(() => {
  return today() + ' 00:00'
})

// ── Period subtitle ──────────────────────────────────────
const periodSub = computed(() => {
  if (!billing.value) return ''
  return `${billing.value.date_from} ~ ${billing.value.date_to}`
})

// ── Lifecycle ────────────────────────────────────────────
watch(selectedDeptId, () => {
  if (selectedDeptId.value !== null) loadBilling().then(() => nextTick(renderAllCharts))
})
watch(period, () => {
  if (selectedDeptId.value !== null) loadBilling().then(() => nextTick(renderAllCharts))
})

onMounted(async () => {
  await loadCurrency()
  await loadDepartments()
  await nextTick()
  if (selectedDeptId.value !== null) {
    await loadBilling()
    nextTick(renderAllCharts)
  }
})

onUnmounted(() => {
  donutChart.value?.dispose()
  barChart.value?.dispose()
})

function handleRefresh() {
  loadBilling().then(() => nextTick(renderAllCharts))
}

function handleExport() {
  if (!billing.value) return
  const b = billing.value
  const deptName = selectedDeptName.value || `dept-${b.dept_id}`
  const lines: string[] = []

  lines.push(`${t('cost.billing.csvTitle')},${deptName}`)
  lines.push(`${t('cost.billing.csvPeriod')},${b.date_from} ~ ${b.date_to}`)
  lines.push(`${t('cost.billing.csvGranularity')},${b.granularity}`)
  lines.push(`${t('cost.billing.csvBillDays')},${b.bill_days}`)
  lines.push(`${t('cost.billing.csvTotal')},${currency.value} ${b.total}`)
  lines.push(`${t('cost.billing.csvDailyAvg')},${currency.value} ${b.daily_avg}`)
  lines.push(`${t('cost.billing.csvAnnualized')},${currency.value} ${b.annualized}`)
  lines.push('')

  lines.push(`${t('cost.billing.csvResource')},${t('cost.billing.csvType')},${t('cost.billing.csvBillingMode')},${t('cost.billing.csvMonthlyCost')},${t('cost.billing.csvDailyRate')},${t('cost.billing.csvDaysUsed')},${t('cost.billing.csvPeriodAmount')}`)
  for (const r of b.resources) {
    lines.push(`${r.asset_no},${r.asset_type},${r.billing_mode},${r.monthly_cost},${r.daily_rate},${r.days_used},${r.period_amount}`)
  }
  lines.push(`,,,${totals.value.monthly_cost},${totals.value.daily_rate},,${totals.value.period_amount}`)
  lines.push('')

  if (Object.keys(b.cost_type_totals).length) {
    lines.push(`${t('cost.billing.csvCostType')},${t('cost.billing.csvAmount')}`)
    for (const [ct, amt] of Object.entries(b.cost_type_totals)) {
      lines.push(`${ct},${amt}`)
    }
  }

  const blob = new Blob(['﻿' + lines.join('\n')], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `dept_billing_${deptName}_${b.date_from}_${b.date_to}.csv`
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <div class="dept-billing-page">
    <!-- Page bar -->
    <div class="page-bar">
      <h1>{{ t('cost.billing.title') }}</h1>
      <div class="page-bar-right">
        <span class="data-ts">{{ t('cost.billing.dataAsOf', { date: dataTimestamp }) }}</span>
        <button class="btn sm" :disabled="loading" @click="handleRefresh">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M13.5 4.5A6 6 0 0 0 3 6.5"/><path d="M13.5 2.5v3h-3"/><path d="M2.5 11.5A6 6 0 0 0 13 9.5"/><path d="M2.5 13.5v-3h3"/></svg>
          {{ t('cost.billing.refresh') }}
        </button>
        <button class="btn sm primary" @click="handleExport">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M8 2.5v8M4.5 7L8 10.5 11.5 7"/><path d="M2.5 13h11"/></svg>
          {{ t('cost.billing.exportBill') }}
        </button>
      </div>
    </div>

    <!-- Two-column billing layout -->
    <div class="billing-layout">

      <!-- Dept panel -->
      <div class="dept-panel">
        <div class="dept-search">
          <svg class="dept-search-icon" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><circle cx="7" cy="7" r="4.5"/><path d="M10.5 10.5L13.5 13.5"/></svg>
          <input
            v-model="deptSearch"
            type="text"
            :placeholder="t('cost.billing.searchDept')"
          />
        </div>
        <div class="dept-list">
          <div
            v-for="dept in filteredDepts"
            :key="dept.id"
            :class="['dept-item', { active: dept.id === selectedDeptId }]"
            @click="selectedDeptId = dept.id"
          >
            <span :class="['d-name', { active: dept.id === selectedDeptId }]">{{ dept.name }}</span>
            <span :class="['d-amt', { active: dept.id === selectedDeptId }]">{{ dept.code }}</span>
          </div>
          <div v-if="!filteredDepts.length" class="dept-empty">
            {{ t('cost.billing.searchDept') }}
          </div>
        </div>
      </div>

      <!-- Billing content -->
      <div class="billing-content">

        <!-- Period switcher + summary KPIs -->
        <div class="period-summary">
          <div class="period-tabs">
            <button
              v-for="tab in periodTabs"
              :key="tab.key"
              :class="['period-tab', { active: period === tab.key }]"
              @click="selectPeriod(tab.key)"
            >{{ tab.label }}</button>
          </div>
          <div class="summary-divider"></div>
          <div class="summary-kpi">
            <div class="sk-label">{{ t('cost.billing.monthlyTotal') }}</div>
            <div class="sk-val">{{ billing ? fmtMoney(billing.total) : '--' }}</div>
            <div class="sk-sub">{{ periodSub }}</div>
          </div>
          <div class="summary-divider"></div>
          <div class="summary-kpi">
            <div class="sk-label">{{ t('cost.billing.dailyRate') }}</div>
            <div class="sk-val">{{ billing ? fmtMoneyDecimal(billing.daily_avg) : '--' }}<span>/ {{ t('cost.overview.perDay') }}</span></div>
            <div class="sk-sub">{{ billing?.bill_days ?? 0 }} {{ t('cost.assetCost.months') }}</div>
          </div>
          <div class="summary-divider"></div>
          <div class="summary-kpi">
            <div class="sk-label">{{ t('cost.billing.annualized') }}</div>
            <div class="sk-val">{{ billing ? fmtMoney(billing.annualized) : '--' }}</div>
            <div class="sk-sub">{{ t('cost.overview.basedOnCurrentRate') }}</div>
          </div>
          <div class="period-actions">
            <span class="period-label">{{ selectedDeptName }}{{ periodSub ? ' · ' + formatMonth(billing?.date_from ?? '') : '' }}</span>
          </div>
        </div>

        <!-- Resource detail table -->
        <div class="tbl-card">
          <div class="tbl-card-head">
            <h4>{{ t('cost.billing.resourceDetail') }}</h4>
            <span class="tbl-card-meta">{{ t('cost.billing.items', { count: billing?.resource_count ?? 0 }) }}</span>
          </div>
          <el-table
            :data="billingResources"
            stripe
            style="width: 100%"
            :header-cell-style="{ background: 'var(--neutral-50)', color: 'var(--neutral-700)', fontWeight: 600, fontSize: '13px' }"
            :cell-style="{ fontSize: '14px' }"
            show-summary
            :summary-method="() => []"
          >
            <el-table-column :label="t('cost.billing.resourceName')" min-width="180">
              <template #default="{ row }">
                <div class="res-name">{{ row.asset_no }}</div>
                <div class="res-caption">{{ row.ip_address }}{{ row.asset_type ? ' · ' + row.asset_type : '' }}</div>
              </template>
            </el-table-column>
            <el-table-column :label="t('cost.billing.type')" width="100">
              <template #default="{ row }">
                <span :class="['type-chip', typeChipClass(row.asset_type)]">{{ typeLabel(row.asset_type) }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="t('cost.billing.billingMode')" width="100">
              <template #default>
                <span class="billing-mode-label">{{ t('cost.billing.costPrice') }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="t('cost.billing.monthlyCost')" width="110" align="right">
              <template #default="{ row }">
                <span class="mono">{{ fmtMoney(row.monthly_cost) }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="t('cost.billing.dailyRateCol')" width="100" align="right">
              <template #default="{ row }">
                <span class="mono">{{ fmtMoneyDecimal(row.daily_rate) }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="t('cost.billing.daysUsed')" width="90" align="right">
              <template #default="{ row }">
                {{ row.days_used }}
              </template>
            </el-table-column>
            <el-table-column :label="t('cost.billing.periodAmount')" width="120" align="right">
              <template #default="{ row }">
                <span class="mono period-amt">{{ fmtMoney(row.period_amount) }}</span>
              </template>
            </el-table-column>
          </el-table>
          <!-- Footer totals -->
          <div class="tbl-footer">
            <div class="tf-label">{{ t('cost.billing.total') }}</div>
            <div class="tf-spacer"></div>
            <div class="tf-cell tf-monthly">{{ fmtMoney(totals.monthly_cost) }}</div>
            <div class="tf-cell tf-daily">{{ fmtMoneyDecimal(totals.daily_rate) }}</div>
            <div class="tf-cell tf-days">&mdash;</div>
            <div class="tf-cell tf-period">{{ fmtMoney(totals.period_amount) }}</div>
          </div>
        </div>

        <!-- Charts row -->
        <div class="charts-row">
          <div class="chart-card">
            <div class="cc-head">
              <span class="cc-title">{{ t('cost.billing.costTypeDonut') }}</span>
              <span class="cc-sub">{{ selectedDeptName }}</span>
            </div>
            <div ref="donutEl" class="chart-container"></div>
          </div>
          <div class="chart-card">
            <div class="cc-head">
              <span class="cc-title">{{ t('cost.billing.resourceRanking') }}</span>
              <span class="cc-sub">{{ t('cost.billing.monthlyCost') }}</span>
            </div>
            <div ref="barEl" class="chart-container"></div>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<style scoped>
/* ===== Page layout ===== */
.dept-billing-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  max-width: 1400px;
}

/* Page bar */
.page-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4, 16px);
  flex-shrink: 0;
}
.page-bar h1 {
  margin: 0;
  font-size: var(--fs-h2, 22px);
  font-weight: 700;
  color: var(--neutral-900);
  line-height: var(--lh-h2, 30px);
}
.page-bar-right {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
}
.data-ts {
  font-size: var(--fs-caption, 12px);
  color: var(--neutral-500);
  font-family: var(--font-mono, monospace);
}

/* Buttons */
.btn {
  height: 36px;
  border-radius: var(--radius-md, 6px);
  padding: 0 14px;
  font-size: var(--fs-body, 14px);
  border: 1px solid var(--neutral-300, #CBD5E1);
  background: var(--neutral-0, #fff);
  color: var(--neutral-700);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: background-color .12s, border-color .12s, color .12s;
  white-space: nowrap;
  font-family: inherit;
}
.btn:hover { background: var(--neutral-50, #F8FAFC); border-color: var(--neutral-400, #94A3B8); }
.btn:disabled { opacity: .6; cursor: not-allowed; }
.btn.primary {
  background: var(--color-primary-500, #2563EB);
  border-color: var(--color-primary-500, #2563EB);
  color: #fff;
}
.btn.primary:hover { background: var(--color-primary-600, #1D4FD4); }
.btn.sm { height: 32px; padding: 0 10px; font-size: 13px; }

/* Billing two-column layout */
.billing-layout {
  display: grid;
  grid-template-columns: 216px 1fr;
  gap: var(--space-4, 16px);
  flex: 1;
  min-height: 0;
}

/* ===== Department panel ===== */
.dept-panel {
  background: var(--neutral-0, #fff);
  border: 1px solid var(--neutral-200, #E2E8F0);
  border-radius: var(--radius-lg, 8px);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.dept-search {
  padding: var(--space-3, 12px);
  border-bottom: 1px solid var(--neutral-200, #E2E8F0);
  position: relative;
}
.dept-search-icon {
  position: absolute;
  left: 22px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--neutral-400, #94A3B8);
  pointer-events: none;
}
.dept-search input {
  width: 100%;
  height: 32px;
  border: 1px solid var(--neutral-200, #E2E8F0);
  border-radius: var(--radius-md, 6px);
  padding: 0 10px 0 30px;
  font-family: var(--font-sans);
  font-size: 13px;
  outline: none;
  background: var(--neutral-50, #F8FAFC);
  color: var(--neutral-900);
  transition: border-color .12s, box-shadow .12s;
}
.dept-search input:focus {
  border-color: var(--color-primary-500, #2563EB);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}
.dept-search input::placeholder {
  color: var(--neutral-400, #94A3B8);
}

.dept-list {
  flex: 1;
  overflow-y: auto;
}
.dept-list::-webkit-scrollbar { width: 6px; }
.dept-list::-webkit-scrollbar-thumb { background: var(--neutral-200, #E2E8F0); border-radius: 3px; }

.dept-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px var(--space-4, 16px);
  cursor: pointer;
  border-bottom: 1px solid var(--neutral-100, #F1F5F9);
  transition: background-color .1s;
}
.dept-item:last-child { border-bottom: 0; }
.dept-item:hover { background: var(--color-primary-50, #EFF4FF); }
.dept-item.active {
  background: var(--color-primary-50, #EFF4FF);
  border-right: 2px solid var(--color-primary-500, #2563EB);
}
.dept-item .d-name {
  font-size: var(--fs-body, 14px);
  color: var(--neutral-900);
  font-weight: 500;
}
.dept-item .d-name.active { color: var(--color-primary-700, #1E40AF); }
.dept-item .d-amt {
  font-size: 12px;
  font-family: var(--font-mono, monospace);
  color: var(--neutral-500);
}
.dept-item.active .d-amt { color: var(--color-primary-600, #1D4FD4); }

.dept-empty {
  padding: var(--space-4, 16px);
  text-align: center;
  font-size: 13px;
  color: var(--neutral-400, #94A3B8);
}

/* ===== Billing content ===== */
.billing-content {
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-4, 16px);
}
.billing-content::-webkit-scrollbar { width: 6px; }
.billing-content::-webkit-scrollbar-thumb { background: var(--neutral-200, #E2E8F0); border-radius: 3px; }

/* Period summary */
.period-summary {
  background: var(--neutral-0, #fff);
  border: 1px solid var(--neutral-200, #E2E8F0);
  border-radius: var(--radius-lg, 8px);
  padding: var(--space-4, 16px) var(--space-6, 24px);
  display: flex;
  align-items: center;
  gap: var(--space-8, 32px);
}
.period-tabs {
  display: flex;
  background: var(--neutral-100, #F1F5F9);
  border-radius: var(--radius-md, 6px);
  padding: 3px;
  gap: 2px;
}
.period-tab {
  padding: 5px 14px;
  border-radius: var(--radius-sm, 4px);
  font-size: 13px;
  color: var(--neutral-600);
  cursor: pointer;
  transition: background-color .12s, color .12s;
  border: 0;
  background: transparent;
  font-family: inherit;
}
.period-tab:hover { color: var(--neutral-900); }
.period-tab.active {
  background: var(--neutral-0, #fff);
  color: var(--neutral-900);
  font-weight: 500;
  box-shadow: var(--shadow-subtle);
}
.summary-divider {
  width: 1px;
  height: 40px;
  background: var(--neutral-200, #E2E8F0);
}
.summary-kpi {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.summary-kpi .sk-label {
  font-size: var(--fs-caption, 12px);
  color: var(--neutral-500);
}
.summary-kpi .sk-val {
  font-size: 22px;
  line-height: 28px;
  font-weight: 700;
  color: var(--neutral-900);
  font-family: var(--font-mono, monospace);
  letter-spacing: -0.02em;
}
.summary-kpi .sk-val span {
  font-size: 13px;
  font-weight: 400;
  color: var(--neutral-500);
  margin-left: 2px;
}
.summary-kpi .sk-sub {
  font-size: var(--fs-caption, 12px);
  color: var(--neutral-500);
}
.period-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
}
.period-label {
  font-size: var(--fs-caption, 12px);
  color: var(--neutral-500);
}

/* Table card */
.tbl-card {
  background: var(--neutral-0, #fff);
  border: 1px solid var(--neutral-200, #E2E8F0);
  border-radius: var(--radius-lg, 8px);
  overflow: hidden;
}
.tbl-card-head {
  padding: 12px var(--space-6, 24px);
  border-bottom: 1px solid var(--neutral-200, #E2E8F0);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.tbl-card-head h4 {
  margin: 0;
  font-size: var(--fs-body, 14px);
  font-weight: 600;
  color: var(--neutral-900);
}
.tbl-card-meta {
  font-size: var(--fs-caption, 12px);
  color: var(--neutral-500);
}

/* Resource name two-line cell */
.res-name {
  font-weight: 500;
  color: var(--neutral-900);
}
.res-caption {
  font-size: var(--fs-caption, 12px);
  color: var(--neutral-500);
  font-family: var(--font-mono, monospace);
  margin-top: 2px;
}

.mono {
  font-family: var(--font-mono, monospace);
  font-size: 13px;
  color: var(--neutral-900);
}
.period-amt {
  font-weight: 600;
}
.billing-mode-label {
  font-size: 13px;
  color: var(--neutral-500);
}

/* Type chips */
.type-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  padding: 1px 8px;
  border-radius: var(--radius-sm, 4px);
  white-space: nowrap;
}
.type-chip.type-exclusive { background: #EDE9FE; color: #5B21B6; }
.type-chip.type-vm { background: var(--color-primary-50, #EFF4FF); color: var(--color-primary-700, #1E40AF); }
.type-chip.type-shared { background: var(--neutral-100, #F1F5F9); color: var(--neutral-600); }

/* Table footer */
.tbl-footer {
  display: flex;
  align-items: center;
  padding: 10px var(--space-6, 24px);
  background: var(--neutral-50, #F8FAFC);
  border-top: 1px solid var(--neutral-200, #E2E8F0);
  font-weight: 600;
  color: var(--neutral-900);
  font-size: 14px;
  gap: 0;
}
.tf-label {
  min-width: 180px;
}
.tf-spacer {
  min-width: 200px; /* type + billing mode */
}
.tf-cell {
  font-family: var(--font-mono, monospace);
  text-align: right;
}
.tf-monthly { min-width: 110px; }
.tf-daily { min-width: 100px; }
.tf-days { min-width: 90px; text-align: right; color: var(--neutral-500); }
.tf-period {
  min-width: 120px;
  font-size: var(--fs-h4, 16px);
  color: var(--color-primary-700, #1E40AF);
}

/* Charts row */
.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4, 16px);
}
.chart-card {
  background: var(--neutral-0, #fff);
  border: 1px solid var(--neutral-200, #E2E8F0);
  border-radius: var(--radius-lg, 8px);
  padding: var(--space-4, 16px) var(--space-6, 24px);
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
  color: var(--neutral-900);
}
.chart-card .cc-sub {
  font-size: var(--fs-caption, 12px);
  color: var(--neutral-500);
}
.chart-container {
  height: 240px;
}

/* Responsive */
@media (max-width: 960px) {
  .billing-layout {
    grid-template-columns: 1fr;
  }
  .dept-panel {
    max-height: 200px;
  }
  .charts-row {
    grid-template-columns: 1fr;
  }
}
</style>
