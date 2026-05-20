/**
 * 扫描批次相关 TypeScript 类型定义
 */

export interface ScanBatch {
  id: number
  batch_name: string | null
  uploaded_by: number | null
  uploaded_at: string
  scan_started_at: string | null
  scan_finished_at: string | null
  file_size_bytes: number | null
  total_hosts: number | null
  new_count: number
  changed_count: number
  missing_count: number
  status: 'pending' | 'confirmed' | 'rejected'
}

export interface ScanBatchListResponse {
  items: ScanBatch[]
  total: number
}

export interface ScanConfirmRequest {
  new_assets: Array<{
    ip_address: string
    asset_type: string
    location: string
    owner: string
    business_system: string
    importance: string
    network_zone: string
    asset_no?: string
    mac_address?: string
    hostname?: string
    os_info?: string
  }>
}

// ── 差异详情类型 ──────────────────────────────────────────

export interface DiffPort {
  port_number: number
  protocol: string
  service_name: string | null
  service_version: string | null
  state: string | null
}

export interface DiffPortChange {
  port_number: number
  protocol: string
  old_service: string | null
  new_service: string | null
  old_version: string | null
  new_version: string | null
  old_state: string | null
  new_state: string | null
  change_type: 'added' | 'removed' | 'modified'
}

export interface DiffNewHost {
  ip_address: string
  mac_address: string | null
  hostname: string | null
  os_info: string | null
  ports: DiffPort[]
}

export interface DiffChangedHost {
  ip_address: string
  mac_address: string | null
  hostname: string | null
  os_info: string | null
  matched_asset_id: number | null
  matched_asset_no: string | null
  port_changes: DiffPortChange[]
  current_ports: DiffPort[]
  scan_ports: DiffPort[]
}

export interface DiffMissingHost {
  ip_address: string
  mac_address: string | null
  hostname: string | null
  matched_asset_id: number | null
  matched_asset_no: string | null
  missing_count: number
}

export interface ScanDiffResponse {
  batch_id: number
  batch_name: string | null
  status: string
  total_hosts: number
  new_count: number
  changed_count: number
  missing_count: number
  new_hosts: DiffNewHost[]
  changed_hosts: DiffChangedHost[]
  missing_hosts: DiffMissingHost[]
}
