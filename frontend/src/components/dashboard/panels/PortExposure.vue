<script setup lang="ts">
/**
 * 端口暴露面 — Top10 柱状图 + 区域分布
 */
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart, PieChart } from 'echarts/charts'
import { TooltipComponent, GridComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { PortExposureData, DrillTarget } from '@/types/dashboard'

echarts.use([BarChart, PieChart, TooltipComponent, GridComponent, LegendComponent, CanvasRenderer])

const props = defineProps<{ data: PortExposureData }>()
const emit = defineEmits<{ drill: [target: DrillTarget] }>()
const barRef = ref<HTMLElement>()
const pieRef = ref<HTMLElement>()
let barChart: echarts.ECharts | null = null
let pieChart: echarts.ECharts | null = null

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4', '#F97316', '#EC4899', '#14B8A6', '#6366F1']
const ZONE_COLORS: Record<string, string> = {
  dmz: '#EF4444', intranet: '#3B82F6', office: '#F59E0B',
  management: '#8B5CF6', aliyun: '#FF6A00', tencent: '#00B4D8',
  huawei: '#CF0A2C', aws: '#FF9900', azure: '#0078D4',
  gcp: '#4285F4', other_cloud: '#6B7280', other: '#9CA3AF',
}

const tooltipStyle = {
  backgroundColor: '#fff',
  borderColor: '#E5E7EB',
  textStyle: { color: '#374151' as const },
}

function renderBar() {
  if (!barRef.value || !props.data) return
  if (!barChart) {
    barChart = echarts.init(barRef.value)
    barChart.on('click', (params: any) => {
      emit('drill', { route: '/assets', query: { port: String(params.name) } })
    })
  }
  const ports = props.data.top_ports || []
  barChart.setOption({
    tooltip: { ...tooltipStyle, trigger: 'axis' },
    grid: { left: 40, right: 10, top: 10, bottom: 24 },
    xAxis: {
      type: 'category',
      data: ports.map(p => String(p.port)),
      axisLabel: { color: '#6B7280', fontSize: 10 },
      axisLine: { lineStyle: { color: '#E5E7EB' } },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#9CA3AF', fontSize: 10 },
      splitLine: { lineStyle: { color: '#F3F4F6' } },
    },
    series: [{
      type: 'bar',
      data: ports.map((p, i) => ({ value: p.count, itemStyle: { color: COLORS[i % COLORS.length] } })),
      barMaxWidth: 24,
      animationDuration: 500,
      animationEasing: 'cubicOut',
    }],
  }, { notMerge: true })
}

function renderPie() {
  if (!pieRef.value || !props.data) return
  if (!pieChart) pieChart = echarts.init(pieRef.value)
  const zones = props.data.by_zone || []
  pieChart.setOption({
    tooltip: { ...tooltipStyle, trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['35%', '60%'],
      label: { show: false },
      data: zones.map(z => ({
        name: z.zone,
        value: z.port_count,
        itemStyle: { color: ZONE_COLORS[z.zone] || '#6B7280' },
      })),
      animationDuration: 500,
    }],
  }, { notMerge: true })
}

watch(() => props.data, () => { nextTick(renderBar); nextTick(renderPie) }, { deep: true })
onMounted(() => { renderBar(); renderPie() })
onUnmounted(() => { barChart?.dispose(); barChart = null; pieChart?.dispose(); pieChart = null })
function handleResize() { barChart?.resize(); pieChart?.resize() }
defineExpose({ handleResize })
</script>

<template>
  <div class="panel-inner">
    <div class="panel-title">端口暴露面</div>
    <div class="chart-row">
      <div class="chart-col">
        <div class="sub-title">开放端口 Top 10</div>
        <div ref="barRef" class="chart-box"></div>
      </div>
      <div class="chart-col">
        <div class="sub-title">按区域分布</div>
        <div ref="pieRef" class="chart-box"></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.panel-inner { height: 100%; display: flex; flex-direction: column; }
.panel-title { font-size: 13px; color: var(--neutral-500); padding: 6px 10px 0; flex-shrink: 0; }
.chart-row { flex: 1; display: flex; gap: 8px; padding: 4px 10px 8px; min-height: 0; }
.chart-col { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.sub-title { font-size: 11px; color: var(--neutral-400); margin-bottom: 4px; flex-shrink: 0; }
.chart-box { flex: 1; min-height: 0; }
</style>
