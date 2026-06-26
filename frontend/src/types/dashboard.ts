/**
 * Asset security dashboard -- TypeScript type definitions
 * Aligned with backend /api/reports/dashboard-summary response structure
 */

/** KPI flip data */
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
  project_count: number
  consuming_unit_count: number
  attribution_coverage: number
}

/** Distribution item */
export interface DistributionItem {
  label: string
  count: number
}

/** Asset distribution */
export interface AssetDistribution {
  by_zone: DistributionItem[]
  by_type: DistributionItem[]
  by_importance: DistributionItem[]
  by_os: DistributionItem[]
}

/** Port exposure */
export interface PortExposureData {
  top_ports: { port: number; count: number }[]
  by_zone: { zone: string; port_count: number }[]
}

/** Dangerous port alert item */
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

/** Shadow assets */
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

/** Asset change item */
export interface AssetChangeItem {
  batch_id: number
  ip_address: string
  hostname: string | null
  port_number: number | null
  protocol: string | null
  service_name: string | null
  diff_type: string
}

/** Zone topology */
export interface ZoneTopologyData {
  zones: {
    zone: string
    asset_count: number
    core_count: number
  }[]
}

/** Activity stream item */
export interface ActivityItem {
  timestamp: string
  action_type: string
  username: string | null
  target: string
  result: string
  source: 'audit' | 'llm'
}

/** Project summary for dashboard */
export interface ProjectSummaryData {
  total_project_cost: number
  global_idle_bucket: number
  by_project: { name: string; unit_count: number; cost: number | null }[]
}

/** Dashboard aggregated data (full response) */
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
  project_summary: ProjectSummaryData
}
