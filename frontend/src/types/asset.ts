/**
 * 资产相关 TypeScript 类型定义
 */

export type AssetType = 'physical' | 'virtual' | 'network_device' | 'other' | 'cloud_server'
export type Importance = 'core' | 'important' | 'normal'
export type NetworkZone =
  | 'dmz' | 'intranet' | 'office' | 'management' | 'other'
  | 'aliyun' | 'tencent' | 'huawei' | 'aws' | 'azure' | 'gcp' | 'other_cloud'
export type AssetStatus = 'online' | 'offline' | 'decommissioned'
export type AssetSource = 'scan' | 'manual'

export interface AssetPort {
  id: number
  port_number: number
  protocol: string
  service_name: string | null
  service_version: string | null
  state: string | null
  last_seen_at: string | null
}

export interface Asset {
  id: number
  asset_no: string
  ip_address: string
  mac_address: string | null
  hostname: string | null
  asset_type: AssetType
  os_info: string | null
  location: string
  owner: string
  business_system: string
  importance: Importance
  network_zone: NetworkZone
  cpu: string | null
  memory_gb: number | null
  disk_gb: number | null
  purchase_date: string | null
  warranty_expiry: string | null
  remark: string | null
  status: AssetStatus
  source: AssetSource
  last_seen_at: string | null
  missing_count: number
  last_scan_batch_id: number | null
  created_at: string
  updated_at: string
  ports: AssetPort[]
}

export interface AssetListItem {
  id: number
  asset_no: string
  ip_address: string
  mac_address: string | null
  hostname: string | null
  asset_type: AssetType
  os_info: string | null
  location: string
  owner: string
  business_system: string
  importance: Importance
  network_zone: NetworkZone
  status: AssetStatus
  source: AssetSource
  last_seen_at: string | null
  missing_count: number
  created_at: string
  updated_at: string
}

export interface AssetListResponse {
  items: AssetListItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface AssetCreateRequest {
  asset_no?: string | null
  ip_address: string
  mac_address?: string | null
  hostname?: string | null
  asset_type: AssetType
  os_info?: string | null
  location: string
  owner: string
  business_system: string
  importance: Importance
  network_zone: NetworkZone
  cpu?: string | null
  memory_gb?: number | null
  disk_gb?: number | null
  purchase_date?: string | null
  warranty_expiry?: string | null
  remark?: string | null
  source?: AssetSource
}

export interface AssetUpdateRequest {
  ip_address?: string
  mac_address?: string | null
  hostname?: string | null
  asset_type?: AssetType
  os_info?: string | null
  location?: string
  owner?: string
  business_system?: string
  importance?: Importance
  network_zone?: NetworkZone
  cpu?: string | null
  memory_gb?: number | null
  disk_gb?: number | null
  purchase_date?: string | null
  warranty_expiry?: string | null
  remark?: string | null
  status?: AssetStatus
}

export interface AssetQueryParams {
  page?: number
  page_size?: number
  search?: string
  asset_type?: AssetType
  network_zone?: NetworkZone
  importance?: Importance
  status?: AssetStatus
  business_system?: string
  owner?: string
  source?: AssetSource
}
