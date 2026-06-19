/**
 * 资产安全态势大屏 — TypeScript 类型定义
 * 对齐后端 /api/reports/dashboard-summary 返回结构
 */

/** KPI 翻牌带数据 */
export interface KpiData {
  total_assets: number
  online: number
  offline: number
  decommissioned: number
  dangerous_ports: number
  shadow_assets: number
  changes_this_month: number
  scan_coverage: {
    last_scan_at: string | null
    covered: number
    total: number
  }
}

/** 分布项 */
export interface DistributionItem {
  label: string
  count: number
}

/** 资产分布 */
export interface AssetDistribution {
  by_zone: DistributionItem[]
  by_type: DistributionItem[]
  by_importance: DistributionItem[]
  by_os: DistributionItem[]
}

/** 端口暴露面 */
export interface PortExposureData {
  top_ports: { port: number; count: number }[]
  by_zone: { zone: string; port_count: number }[]
}

/** 危险端口告警项 */
export interface DangerousPortItem {
  asset_id: number
  asset_no: string
  ip_address: string
  hostname: string | null
  network_zone: string
  port_number: number
  protocol: string
  service_name: string | null
  severity: 'high' | 'medium'
}

/** 影子资产 */
export interface ShadowAssetsData {
  missing_fields: {
    id: number
    asset_no: string
    ip_address: string
    hostname: string | null
    reason: string
  }[]
  missing_fields_count: number
  long_offline: {
    id: number
    asset_no: string
    ip_address: string
    hostname: string | null
    missing_count: number
  }[]
  long_offline_count: number
}

/** 资产变化项 */
export interface AssetChangeItem {
  batch_id: number
  ip_address: string
  hostname: string | null
  port_number: number | null
  protocol: string | null
  service_name: string | null
  diff_type: string
}

/** 区域拓扑 */
export interface ZoneTopologyData {
  zones: {
    zone: string
    asset_count: number
    core_count: number
  }[]
}

/** 活动流项 */
export interface ActivityItem {
  timestamp: string
  action_type: string
  username: string | null
  target: string
  result: string
  source: 'audit' | 'llm'
}

/** 大屏聚合数据（完整响应） */
export interface DashboardSummary {
  generated_at: string
  cache_age_seconds: number
  kpi: KpiData
  asset_distribution: AssetDistribution
  port_exposure: PortExposureData
  dangerous_ports: DangerousPortItem[]
  shadow_assets: ShadowAssetsData
  asset_changes: AssetChangeItem[]
  zone_topology: ZoneTopologyData
  activity: ActivityItem[]
}

/** 面板定义（注册表用） */
export interface PanelDef {
  id: string
  title: string
  dataKey: keyof DashboardSummary
  defaultLayout: { x: number; y: number; w: number; h: number }
  minW: number
  minH: number
  roles?: string[]
}

/** 大屏配置 */
export interface DashboardConfig {
  panels: { id: string; visible: boolean }[]
  refreshIntervalSec: number
  filters: { zone?: string[]; timeRange?: string }
  theme: 'dark' | 'light'
}

/** 钻取目标 */
export interface DrillTarget {
  route: string
  query: Record<string, string>
}
