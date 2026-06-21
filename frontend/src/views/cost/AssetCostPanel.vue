<script setup lang="ts">
/**
 * 资产详情 — 成本构成面板
 * 设计来源：design/Asset Detail Cost Panel.html
 */
import { ref, onMounted, watch, shallowRef, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchAssetCost, type AssetCostDetail } from '@/api/cost'
import { useCostCurrency } from '@/composables/useCostCurrency'
import * as echarts from 'echarts/core'
import { PieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useEventListener } from '@vueuse/core'

echarts.use([PieChart, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps<{ assetId: number }>()
const { t, locale } = useI18n()
const { symbol, formatMoney, loadCurrency } = useCostCurrency()

const loading = ref(false)
const cost = ref<AssetCostDetail | null>(null)
const donutRef = shallowRef<echarts.ECharts | null>(null)

const COLORS = ['#8B5CF6', '#D97706', '#0891B2', '#94A3B8', '#EA580C', '#2563EB', '#16A34A']

async function loadCost() {
  loading.value = true
  try {
    cost.value = await fetchAssetCost(props.assetId)
  } finally {
    loading.value = false
  }
}

const breakdownItems = computed(() => {
  if (!cost.value) return []
  const total = Object.values(cost.value.cost_breakdown).reduce((s, v) => s + v, 0)
  return Object.entries(cost.value.cost_breakdown).map(([key, val], i) => ({
    key,
    label: key,
    value: val,
    pct: total > 0 ? (val / total * 100) : 0,
    color: COLORS[i % COLORS.length],
  }))
})

const deprInfo = computed(() => cost.value?.depreciation_info)
const deprProgressPct = computed(() => {
  const d = deprInfo.value
  if (!d || !d.depreciation_months) return 0
  return Math.min(100, (d.months_elapsed / d.depreciation_months) * 100)
})

const typeLabel = computed(() => {
  const typeMap: Record<string, string> = {
    physical: t('cost.assetCost.typePhysical'),
    virtual: t('cost.assetCost.typeVirtual'),
    cloud_server: t('cost.assetCost.typeCloudServer'),
    network_device: t('cost.assetCost.typeNetworkDevice'),
    other: t('cost.assetCost.typeOther'),
  }
  return typeMap[deprInfo.value?.depreciation_method || ''] || ''
})

const strategyLabel = computed(() => {
  const s = deprInfo.value?.end_of_life_strategy
  return s === 'revalue' ? t('cost.assetCost.strategyRevalue') : t('cost.assetCost.strategyZero')
})

function initDonut() {
  const el = document.getElementById(`cost-donut-${props.assetId}`)
  if (!el) return
  donutRef.value = echarts.init(el)
  renderDonut()
}

function renderDonut() {
  if (!donutRef.value || !cost.value) return
  const data = breakdownItems.value.map(item => ({
    name: item.label,
    value: item.value,
    itemStyle: { color: item.color },
  }))
  donutRef.value.setOption({
    tooltip: {
      trigger: 'item',
      formatter: (p: any) => `<b>${p.name}</b><br/>${symbol.value}${p.value.toLocaleString()} (${p.percent}%)`,
      textStyle: { fontSize: 13 },
    },
    legend: {
      orient: 'vertical', right: 0, top: 'center',
      textStyle: { fontSize: 12, color: '#334155' },
      itemWidth: 9, itemHeight: 9,
    },
    series: [{
      type: 'pie',
      radius: ['46%', '72%'],
      center: ['35%', '50%'],
      data,
      itemStyle: { borderWidth: 2, borderColor: '#ffffff' },
      label: { show: false },
      emphasis: { scale: true, scaleSize: 5 },
    }],
  })
}

useEventListener(window, 'resize', () => donutRef.value?.resize())
watch(locale, renderDonut)
onMounted(async () => {
  await loadCurrency()
  loadCost().then(initDonut)
})
</script>

<template>
  <div v-loading="loading" class="cost-panel">
    <template v-if="cost">
      <!-- KPI Row -->
      <div class="kpi-row">
        <div class="kpi-card accent">
          <div class="k-label"><span class="k-dot" style="background:#8B5CF6;" />{{ t('cost.assetCost.fullLoadMonthly') }}</div>
          <div class="k-val">{{ symbol }}{{ cost.full_loaded_monthly.toLocaleString() }}</div>
          <div class="k-sub">{{ t('cost.assetCost.dailyRateLabel', { rate: cost.daily_rate.toFixed(2) }) }}</div>
        </div>
        <div class="kpi-card">
          <div class="k-label"><span class="k-dot" style="background:#0891B2;" />{{ t('cost.assetCost.netValue') }}</div>
          <div class="k-val">{{ symbol }}{{ (deprInfo?.net_value ?? 0).toLocaleString() }}</div>
          <div class="k-sub" v-if="deprInfo?.purchase_price">
            {{ t('cost.assetCost.purchaseAndResidual', { price: deprInfo.purchase_price.toLocaleString(), rate: ((deprInfo.residual_rate ?? 0) * 100).toFixed(0) }) }}
          </div>
        </div>
        <div class="kpi-card">
          <div class="k-label"><span class="k-dot" style="background:#16A34A;" />{{ t('cost.assetCost.remainingMonths') }}</div>
          <div class="k-val">{{ deprInfo?.remaining_months ?? 0 }} <span class="k-unit">{{ t('cost.assetCost.months') }}</span></div>
          <div class="k-sub" v-if="deprInfo?.is_expired">
            {{ strategyLabel }}
          </div>
        </div>
      </div>

      <!-- Cost Breakdown Row -->
      <div class="cost-row">
        <!-- Donut Chart -->
        <div class="chart-card">
          <div class="cc-head">
            <span class="cc-title">{{ t('cost.assetCost.costDistribution') }}</span>
          </div>
          <div :id="`cost-donut-${assetId}`" style="height: 240px;" />
        </div>

        <!-- Detail Card -->
        <div class="detail-card">
          <div class="dc-head">{{ t('cost.assetCost.costDetail') }}</div>
          <div class="dc-items">
            <div v-for="item in breakdownItems" :key="item.key" class="dc-item">
              <span class="dc-dot" :style="{ background: item.color }" />
              <span class="dc-label">{{ item.label }}</span>
              <div class="dc-bar-wrap">
                <div class="dc-bar" :style="{ width: item.pct + '%', background: item.color }" />
              </div>
              <span class="dc-pct">{{ item.pct.toFixed(1) }}%</span>
              <span class="dc-val">{{ symbol }}{{ item.value.toLocaleString() }}</span>
            </div>
          </div>
          <div class="dc-total">
            {{ t('cost.assetCost.monthlyTotal') }} <span>{{ symbol }}{{ cost.full_loaded_monthly.toLocaleString() }}</span>
          </div>
        </div>
      </div>

      <!-- Depreciation Section -->
      <div v-if="deprInfo" class="depr-section">
        <div class="depr-head">
          <el-icon size="16" color="var(--color-success)"><CircleCheckFilled /></el-icon>
          <span class="depr-title">{{ t('cost.assetCost.deprProgress') }}</span>
          <span class="depr-sub">{{ t('cost.assetCost.basedOnType', { type: typeLabel || deprInfo.depreciation_method }) }}</span>
        </div>
        <div class="depr-body">
          <div class="depr-field">
            <span class="df-lbl">{{ t('cost.assetCost.purchasePrice') }}</span>
            <span class="df-val">{{ symbol }}{{ (deprInfo.purchase_price ?? 0).toLocaleString() }}</span>
          </div>
          <div class="depr-field">
            <span class="df-lbl">{{ t('cost.assetCost.purchaseDate') }}</span>
            <span class="df-val">{{ deprInfo.purchase_date || '-' }}</span>
          </div>
          <div class="depr-field">
            <span class="df-lbl">{{ t('cost.assetCost.deprMethod') }}</span>
            <span class="df-val">{{ deprInfo.depreciation_method === 'straight_line' ? t('cost.assetCost.straightLine') : deprInfo.depreciation_method }}</span>
          </div>
          <div class="depr-field">
            <span class="df-lbl">{{ t('cost.assetCost.monthlyDepr') }}</span>
            <span class="df-val mono">{{ symbol }}{{ deprInfo.monthly_depr.toLocaleString() }}</span>
          </div>
          <div class="depr-field">
            <span class="df-lbl">{{ t('cost.assetCost.eolStrategy') }}</span>
            <span class="df-val">{{ strategyLabel }}</span>
          </div>
        </div>
        <div class="depr-progress">
          <div class="dp-label">
            {{ t('cost.assetCost.deprProgress') }}
            <span class="dp-detail">{{ t('cost.assetCost.deprProgressDetail', { acc: deprInfo.accumulated_depr.toLocaleString(), elapsed: deprInfo.months_elapsed, remain: (deprInfo.net_value - (deprInfo.purchase_price ?? 0) * (deprInfo.residual_rate ?? 0)).toLocaleString(), remaining: deprInfo.remaining_months }) }}</span>
          </div>
          <div class="dp-track">
            <div class="dp-fill" :style="{ width: deprProgressPct + '%' }" />
          </div>
        </div>
      </div>

      <!-- Depreciation Warning -->
      <div v-if="deprInfo?.remaining_months && deprInfo.remaining_months <= 3" class="warn-banner">
        <el-icon size="20" color="var(--color-warning)"><WarningFilled /></el-icon>
        <div class="warn-body">
          <div class="warn-title">{{ t('cost.assetCost.deprWarning') }}</div>
          <div class="warn-desc">{{ t('cost.assetCost.deprWarningDesc', { date: 'N/A' }) }}</div>
          <div class="warn-actions">
            <el-button size="small">{{ t('cost.assetCost.currentStrategy') }}: {{ strategyLabel }}</el-button>
            <el-button size="small" type="primary" plain>{{ t('cost.assetCost.switchToRevalue') }}</el-button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.cost-panel { padding: var(--space-4) 0; }

/* KPI Row */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}
.kpi-card {
  background: var(--surface-base);
  border: var(--border-base);
  border-radius: var(--radius-lg);
  padding: var(--space-4) var(--space-4);
}
.kpi-card.accent {
  border-color: var(--color-primary-200);
  background: linear-gradient(135deg, var(--color-primary-50) 0%, #fff 100%);
}
.kpi-card.accent .k-val { color: var(--color-primary-700); }
.k-label {
  font-size: var(--fs-caption);
  color: var(--neutral-500);
  margin-bottom: 5px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.k-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.k-val {
  font-size: 24px;
  line-height: 32px;
  font-weight: 700;
  color: var(--neutral-900);
  font-family: var(--font-mono);
  letter-spacing: -0.02em;
}
.k-unit { font-size: 14px; font-weight: 400; color: var(--neutral-500); margin-left: 2px; }
.k-sub { font-size: 12px; color: var(--neutral-500); margin-top: 4px; }

/* Cost Row */
.cost-row {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}
.chart-card {
  background: var(--surface-base);
  border: var(--border-base);
  border-radius: var(--radius-lg);
  padding: var(--space-4) var(--space-6);
}
.cc-head { display: flex; justify-content: space-between; margin-bottom: var(--space-4); }
.cc-title { font-size: var(--fs-body); font-weight: 600; color: var(--neutral-900); }

/* Detail Card */
.detail-card {
  background: var(--surface-base);
  border: var(--border-base);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
}
.dc-head {
  font-size: var(--fs-body);
  font-weight: 600;
  color: var(--neutral-900);
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-3);
  border-bottom: var(--border-base);
}
.dc-items { display: flex; flex-direction: column; gap: var(--space-3); }
.dc-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 13px;
}
.dc-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.dc-label { flex: 1; color: var(--neutral-700); min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.dc-bar-wrap { width: 60px; height: 4px; background: var(--neutral-100); border-radius: 2px; }
.dc-bar { height: 100%; border-radius: 2px; }
.dc-pct { width: 40px; text-align: right; font-family: var(--font-mono); font-size: 12px; color: var(--neutral-500); }
.dc-val { width: 72px; text-align: right; font-family: var(--font-mono); font-size: 13px; color: var(--neutral-900); font-weight: 500; }
.dc-total {
  margin-top: var(--space-4);
  padding-top: var(--space-3);
  border-top: var(--border-base);
  font-size: 13px;
  color: var(--neutral-700);
  display: flex;
  justify-content: space-between;
}
.dc-total span { font-family: var(--font-mono); font-weight: 700; color: var(--neutral-900); }

/* Depreciation */
.depr-section {
  background: var(--surface-base);
  border: var(--border-base);
  border-radius: var(--radius-lg);
  padding: var(--space-4) var(--space-6);
}
.depr-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}
.depr-title { font-size: var(--fs-body); font-weight: 600; color: var(--neutral-900); }
.depr-sub { font-size: 12px; color: var(--neutral-500); margin-left: auto; }
.depr-body {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}
.depr-field { display: flex; flex-direction: column; gap: 4px; }
.df-lbl { font-size: 11px; color: var(--neutral-400); font-family: var(--font-mono); text-transform: uppercase; letter-spacing: 0.05em; }
.df-val { font-size: var(--fs-body); color: var(--neutral-900); font-weight: 500; }
.df-val.mono { font-family: var(--font-mono); }
.depr-progress { margin-top: var(--space-2); }
.dp-label { font-size: 12px; color: var(--neutral-500); margin-bottom: var(--space-2); display: flex; justify-content: space-between; }
.dp-detail { font-family: var(--font-mono); font-size: 11px; color: var(--neutral-400); }
.dp-track { height: 6px; background: var(--neutral-100); border-radius: 3px; }
.dp-fill { height: 100%; background: var(--color-primary-500); border-radius: 3px; transition: width 0.6s var(--ease-out); }

/* Warning */
.warn-banner {
  margin-top: var(--space-4);
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--color-warning-soft);
  border: 1px solid rgba(217, 119, 6, 0.2);
  border-radius: var(--radius-lg);
}
.warn-body { flex: 1; }
.warn-title { font-size: var(--fs-body); font-weight: 600; color: #92400E; margin-bottom: 4px; }
.warn-desc { font-size: 13px; color: #78350F; margin-bottom: var(--space-3); }
.warn-actions { display: flex; gap: var(--space-2); }
</style>
