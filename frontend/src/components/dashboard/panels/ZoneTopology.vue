<script setup lang="ts">
/**
 * 网络区域拓扑 — ECharts graph 按 network_zone 聚合
 */
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { GraphChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { ZoneTopologyData, DrillTarget } from '@/types/dashboard'

echarts.use([GraphChart, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps<{ data: ZoneTopologyData }>()
const emit = defineEmits<{ drill: [target: DrillTarget] }>()
const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

const ZONE_COLORS: Record<string, string> = {
  dmz: '#EF4444', intranet: '#3B82F6', office: '#F59E0B',
  management: '#8B5CF6', aliyun: '#FF6A00', tencent: '#00B4D8',
  huawei: '#CF0A2C', aws: '#FF9900', azure: '#0078D4',
  gcp: '#4285F4', other_cloud: '#6B7280', other: '#9CA3AF',
}

function buildOption(data: ZoneTopologyData) {
  const nodes = data.zones.map(z => ({
    id: z.zone,
    name: z.zone,
    symbolSize: Math.max(30, Math.min(80, z.asset_count * 8)),
    value: z.asset_count,
    category: z.core_count > 0 ? 'core' : 'normal',
    itemStyle: {
      color: ZONE_COLORS[z.zone] || '#6B7280',
      borderColor: z.core_count > 0 ? '#EF4444' : '#E5E7EB',
      borderWidth: z.core_count > 0 ? 3 : 1,
    },
    label: {
      show: true,
      formatter: `{b}\n{c}`,
      color: '#374151',
      fontSize: 11,
    },
  }))

  return {
    tooltip: {
      trigger: 'item',
      backgroundColor: '#fff',
      borderColor: '#E5E7EB',
      textStyle: { color: '#374151' },
      formatter: (p: any) => `${p.name}<br/>资产数: ${p.value}`,
    },
    series: [{
      type: 'graph',
      layout: 'force',
      roam: true,
      force: { repulsion: 300, edgeLength: 120, gravity: 0.1 },
      data: nodes,
      categories: [
        { name: 'core' },
        { name: 'normal' },
      ],
      lineStyle: { color: 'rgba(255,255,255,0.08)', curveness: 0.1 },
      emphasis: { lineStyle: { width: 2 } },
    }],
  }
}

function renderChart() {
  if (!chartRef.value || !props.data?.zones?.length) return
  if (!chart) {
    chart = echarts.init(chartRef.value, undefined, { renderer: 'canvas' })
    chart.on('click', (params: any) => {
      emit('drill', { route: '/assets', query: { network_zone: params.id } })
    })
  }
  chart.setOption(buildOption(props.data), { notMerge: true })
}

watch(() => props.data, () => nextTick(renderChart), { deep: true })
onMounted(renderChart)
onUnmounted(() => { chart?.dispose(); chart = null })

function handleResize() { chart?.resize() }
defineExpose({ handleResize })
</script>

<template>
  <div class="panel-inner">
    <div class="panel-title">网络区域拓扑</div>
    <div ref="chartRef" class="chart-container"></div>
    <div v-if="!data?.zones?.length" class="empty-hint">暂无区域数据</div>
  </div>
</template>

<style scoped>
.panel-inner { height: 100%; display: flex; flex-direction: column; }
.panel-title { font-size: 13px; color: var(--neutral-500); padding: 6px 10px 0; flex-shrink: 0; }
.chart-container { flex: 1; min-height: 0; }
.empty-hint { display: flex; align-items: center; justify-content: center; flex: 1; color: var(--neutral-300); font-size: 13px; }
</style>
