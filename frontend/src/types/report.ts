/**
 * 安全报表 TypeScript 类型
 */

export interface PortExposureData {
  top_ports: Array<{ port: number; count: number }>
  zone_stats: Array<{ zone: string; port_count: number }>
}

export interface DangerousPortAlert {
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

export interface DangerousPortsData {
  total: number
  high_count: number
  medium_count: number
  alerts: DangerousPortAlert[]
}

export interface ShadowAssetsData {
  incomplete_assets: Array<{
    id: number
    asset_no: string
    ip_address: string
    hostname: string | null
    reason: string
  }>
  long_offline_assets: Array<{
    id: number
    asset_no: string
    ip_address: string
    hostname: string | null
    missing_count: number
  }>
  total: number
}

export interface AssetChangesData {
  total: number
  changes: Array<{
    id: number
    batch_id: number
    ip_address: string
    hostname: string | null
    port_number: number | null
    protocol: string | null
    service_name: string | null
    diff_type: string
  }>
}
