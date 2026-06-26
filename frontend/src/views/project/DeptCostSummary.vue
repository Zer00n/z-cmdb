<script setup lang="ts">
/**
 * Department Cost Summary — /projects/billing/departments
 * Aggregates project billing costs grouped by department.
 */
import { ref, computed, onMounted, shallowRef, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts/core'
import { PieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

import { fetchDepartmentBilling } from '@/api/project'
import type { DepartmentBillingItem, DepartmentBillingResponse } from '@/types/project'

echarts.use([PieChart, TooltipComponent, LegendComponent, CanvasRenderer])

const { t } = useI18n()

// ── State ─────────────────────────────────────────────────
const loading = ref(false)
const data = ref<DepartmentBillingResponse | null>(null)
const currentPeriod = computed(() => {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
})
const period = ref(currentPeriod.value)

// ── Chart ─────────────────────────────────────────────────
const chartRef = ref<HTMLElement | null>(null)
const chartInstance = shallowRef<echarts.ECharts | null>(null)

const chartData = computed(() => {
  if (!data.value?.items.length) return []
  return data.value.items
    .filter(item => item.total_cost > 0)
    .map(item => ({ name: item.department, value: item.total_cost }))
})

const COLORS = [
  '#3B82F6', '#8B5CF6', '#EC4899', '#F59E0B', '#10B981',
  '#06B6D4', '#F97316', '#6366F1', '#14B8A6', '#E11D48',
]

function renderChart() {
  if (!chartRef.value || !chartData.value.length) return
  if (!chartInstance.value) {
    chartInstance.value = echarts.init(chartRef.value)
  }
  chartInstance.value.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
    legend: { orient: 'vertical', right: 10, top: 'center', type: 'scroll' },
    color: COLORS,
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['40%', '50%'],
      avoidLabelOverlap: true,
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
      data: chartData.value,
    }],
  })
}

// ── Data loading ──────────────────────────────────────────
async function loadData() {
  loading.value = true
  try {
    data.value = await fetchDepartmentBilling(period.value)
    await nextTick()
    renderChart()
  } catch (e: any) {
    ElMessage.error(e?.message || t('project.deptBilling.loadError'))
  } finally {
    loading.value = false
  }
}

function formatCost(cost: number) {
  return `¥${cost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

onMounted(() => {
  loadData()
  window.addEventListener('resize', () => chartInstance.value?.resize())
})
</script>

<template>
  <div class="ui-page">
    <!-- Page Header -->
    <div class="ui-page-head">
      <div>
        <h1 class="ui-page-title">{{ t('project.deptBilling.title') }}</h1>
      </div>
      <div class="ui-page-actions">
        <el-date-picker
          v-model="period"
          type="month"
          value-format="YYYY-MM"
          :placeholder="t('project.deptBilling.period')"
          style="width: 160px"
          @change="loadData"
        />
      </div>
    </div>

    <!-- KPI Cards -->
    <div class="dept-kpis" v-if="data">
      <div class="dept-kpi-card">
        <div class="dept-kpi-label">{{ t('project.deptBilling.grandTotal') }}</div>
        <div class="dept-kpi-value">{{ formatCost(data.grand_total) }}</div>
      </div>
      <div class="dept-kpi-card">
        <div class="dept-kpi-label">{{ t('project.deptBilling.departmentCount') }}</div>
        <div class="dept-kpi-value">{{ data.items.length }}</div>
      </div>
      <div class="dept-kpi-card">
        <div class="dept-kpi-label">{{ t('project.deptBilling.totalProjects') }}</div>
        <div class="dept-kpi-value">{{ data.items.reduce((s, i) => s + i.project_count, 0) }}</div>
      </div>
    </div>

    <!-- Main content: chart + table -->
    <div class="dept-content" v-loading="loading">
      <!-- Pie chart -->
      <div class="ui-card dept-chart-card">
        <div class="dept-chart-head">{{ t('project.deptBilling.costDistribution') }}</div>
        <div v-if="chartData.length" ref="chartRef" class="dept-chart"></div>
        <div v-else class="dept-empty">{{ t('project.deptBilling.noData') }}</div>
      </div>

      <!-- Table -->
      <div class="ui-card dept-table-card">
        <el-table :data="data?.items || []" :header-cell-style="{ background: '#F8FAFC', color: '#334155', fontWeight: 600, fontSize: '13px' }" show-summary :summary-method="() => []">
          <el-table-column :label="t('project.deptBilling.department')" min-width="160" prop="department" />
          <el-table-column :label="t('project.deptBilling.projectCount')" width="100" align="center" prop="project_count" />
          <el-table-column :label="t('project.deptBilling.billingEnabledCount')" width="110" align="center" prop="billing_enabled_count" />
          <el-table-column :label="t('project.deptBilling.totalCost')" width="160" align="right">
            <template #default="{ row }">
              <span class="dept-cost">{{ formatCost(row.total_cost) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dept-kpis {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}
.dept-kpi-card {
  background: white;
  border: 1px solid var(--neutral-200);
  border-radius: 10px;
  padding: 20px 24px;
}
.dept-kpi-label {
  font-size: 13px;
  color: var(--neutral-500);
  margin-bottom: 6px;
}
.dept-kpi-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--neutral-900);
  font-family: var(--font-mono);
}

.dept-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
@media (max-width: 1024px) {
  .dept-content { grid-template-columns: 1fr; }
  .dept-kpis { grid-template-columns: 1fr; }
}

.dept-chart-card {
  padding: 20px;
}
.dept-chart-head {
  font-size: 15px;
  font-weight: 600;
  color: var(--neutral-900);
  margin-bottom: 12px;
}
.dept-chart {
  width: 100%;
  height: 320px;
}
.dept-empty {
  height: 320px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--neutral-400);
  font-size: 14px;
}

.dept-table-card {
  overflow: hidden;
}
.dept-cost {
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 600;
  color: var(--color-primary-700);
}
</style>
