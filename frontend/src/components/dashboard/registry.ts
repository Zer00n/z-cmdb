/**
 * 大屏面板注册表
 * 新增面板只需：① 在此注册元数据 ② 实现组件 ③ 后端补 summary 字段
 */
import { defineAsyncComponent } from 'vue'
import type { PanelDef } from '@/types/dashboard'

export const PANELS: PanelDef[] = [
  {
    id: 'kpi',
    title: 'KPI 翻牌带',
    dataKey: 'kpi',
    defaultLayout: { x: 0, y: 0, w: 24, h: 3 },
    minW: 12,
    minH: 2,
  },
  {
    id: 'zone_topology',
    title: '网络区域拓扑',
    dataKey: 'zone_topology',
    defaultLayout: { x: 0, y: 3, w: 12, h: 9 },
    minW: 8,
    minH: 6,
  },
  {
    id: 'asset_dist',
    title: '资产分布',
    dataKey: 'asset_distribution',
    defaultLayout: { x: 12, y: 3, w: 12, h: 9 },
    minW: 8,
    minH: 6,
  },
  {
    id: 'port_exposure',
    title: '端口暴露面',
    dataKey: 'port_exposure',
    defaultLayout: { x: 0, y: 12, w: 12, h: 9 },
    minW: 8,
    minH: 6,
  },
  {
    id: 'dangerous_ports',
    title: '危险端口告警',
    dataKey: 'dangerous_ports',
    defaultLayout: { x: 12, y: 12, w: 12, h: 9 },
    minW: 8,
    minH: 6,
  },
  {
    id: 'shadow_assets',
    title: '影子资产',
    dataKey: 'shadow_assets',
    defaultLayout: { x: 0, y: 21, w: 8, h: 9 },
    minW: 6,
    minH: 6,
  },
  {
    id: 'asset_changes',
    title: '资产变化时间线',
    dataKey: 'asset_changes',
    defaultLayout: { x: 8, y: 21, w: 8, h: 9 },
    minW: 6,
    minH: 6,
  },
  {
    id: 'activity',
    title: '审计与 LLM 活动流',
    dataKey: 'activity',
    defaultLayout: { x: 16, y: 21, w: 8, h: 9 },
    minW: 6,
    minH: 6,
    roles: ['super_admin', 'auditor'],
  },
]

/** 面板组件懒加载映射 */
export const PANEL_COMPONENTS: Record<string, ReturnType<typeof defineAsyncComponent>> = {
  kpi: defineAsyncComponent(() => import('./panels/KpiBand.vue')),
  zone_topology: defineAsyncComponent(() => import('./panels/ZoneTopology.vue')),
  asset_dist: defineAsyncComponent(() => import('./panels/AssetDistribution.vue')),
  port_exposure: defineAsyncComponent(() => import('./panels/PortExposure.vue')),
  dangerous_ports: defineAsyncComponent(() => import('./panels/DangerousPorts.vue')),
  shadow_assets: defineAsyncComponent(() => import('./panels/ShadowAssets.vue')),
  asset_changes: defineAsyncComponent(() => import('./panels/AssetChangeTimeline.vue')),
  activity: defineAsyncComponent(() => import('./panels/ActivityFeed.vue')),
}
