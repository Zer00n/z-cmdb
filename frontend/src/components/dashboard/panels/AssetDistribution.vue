<script setup lang="ts">
/**
 * 资产分布 — 四维度饼图（可切换）
 */
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { PieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { AssetDistribution, DrillTarget } from '@/types/dashboard'

echarts.use([PieChart, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps<{ data: AssetDistribution }>()
const emit = defineEmits<{ drill: [target: DrillTarget] }>()
const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

const dimensions = [
  { key: 'by_zone' as const, label: '网络区域', routeField: 'network_zone' },
  { key: 'by_type' as const, label: '资产类型', routeField: 'asset_type' },
  { key: 'by_importance' as const, label: '重要性', routeField: 'importance' },
  { key: 'by_os' as const, label: '操作系统', routeField: 'os_info' },
]
const activeDim = ref(0)

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4', '#F97316', '#EC4899']

function buildOption() {
  if (!props.data) return {}
  const dim = dimensions[activeDim.value]
  const items = props.data[dim.key] || []
  return {
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(11,18,32,0.95)',
      borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: '#374151' },
    },
    legend: {
      orient: 'vertical',
      right: 10,
      top: 'center',
      textStyle: { color: 'rgba(255,255,255,0.6)', fontSize: 11 },
      itemWidth: 10,
      itemHeight: 10,
    },
    color: COLORS,
    series: [{
      type: 'pie',
      radius: ['40%', '65%'],
      center: ['35%', '50%'],
      roseType: 'radius',
      label: { show: false },
      emphasis: {
        label: { show: true, color: '#374151', fontSize: 12, fontWeight: 'bold' },
      },
      data: items.map(item => ({ name: item.label, value: item.count })),
      animationDuration: 500,
      animationEasing: 'cubicOut',
    }],
  }
}

function renderChart() {
  if (!chartRef.value) return
  if (!chart) {
    chart = echarts.init(chartRef.value)
    chart.on('click', (params: any) => {
      const dim = dimensions[activeDim.value]
      emit('drill', { route: '/assets', query: { [dim.routeField]: params.name } })
    })
  }
  chart.setOption(buildOption(), { notMerge: true })
}

watch(() => props.data, () => nextTick(renderChart), { deep: true })
watch(activeDim, () => nextTick(renderChart))
onMounted(renderChart)
onUnmounted(() => { chart?.dispose(); chart = null })
function handleResize() { chart?.resize() }
defineExpose({ handleResize })
</script>

<template>
  <div class="panel-inner">
    <div class="panel-header">
      <span class="panel-title">资产分布</span>
      <div class="dim-tabs">
        <button
          v-for="(dim, i) in dimensions"
          :key="dim.key"
          :class="['dim-tab', { active: activeDim === i }]"
          @click="activeDim = i"
        >{{ dim.label }}</button>
      </div>
    </div>
    <div ref="chartRef" class="chart-container"></div>
  </div>
</template>

<style scoped>
.panel-inner { height: 100%; display: flex; flex-direction: column; }
.panel-header { display: flex; align-items: center; justify-content: space-between; padding: 6px 10px 0; flex-shrink: 0; }
.panel-title { font-size: 13px; color: var(--neutral-500); }
.dim-tabs { display: flex; gap: 4px; }
.dim-tab {
  padding: 2px 8px;
  font-size: 11px;
  color: var(--neutral-400);
  background: var(--surface-base);
  border: 1px solid var(--neutral-200);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}
.dim-tab.active { color: #3B82F6; background: rgba(59,130,246,0.08); border-color: rgba(59,130,246,0.4); }
.dim-tab:hover { color: var(--neutral-700); }
.chart-container { flex: 1; min-height: 0; }
</style>
