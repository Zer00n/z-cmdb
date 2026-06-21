/**
 * Asset-related TypeScript type definitions
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
  // V0.4 cost fields
  purchase_price?: number | null
  depreciation_months?: number | null
  residual_rate?: number | null
  depreciation_method?: string | null
  end_of_life_strategy?: string | null
  revalue_amount?: number | null
  revalue_months?: number | null
  revalue_effective_date?: string | null
  billing_mode?: string | null
  responsible_dept_id?: number | null
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
  // V0.4 cost fields
  purchase_price?: number | null
  depreciation_months?: number | null
  residual_rate?: number | null
  depreciation_method?: string | null
  end_of_life_strategy?: string | null
  revalue_amount?: number | null
  revalue_months?: number | null
  billing_mode?: string | null
  responsible_dept_id?: number | null
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
  // V0.4 cost fields
  purchase_price?: number | null
  depreciation_months?: number | null
  residual_rate?: number | null
  depreciation_method?: string | null
  end_of_life_strategy?: string | null
  revalue_amount?: number | null
  revalue_months?: number | null
  billing_mode?: string | null
  responsible_dept_id?: number | null
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
