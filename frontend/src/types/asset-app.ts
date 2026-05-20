/**
 * 应用服务清单 TypeScript 类型定义
 */

export type AppSource = 'manual' | 'scan'
export type AppStatus = 'active' | 'decommissioned'

export interface AssetApp {
  id: number
  asset_id: number
  name: string
  version: string | null
  category: string | null
  port: number | null
  protocol: string | null
  install_path: string | null
  config_path: string | null
  notes: string | null
  source: AppSource
  status: AppStatus
  created_at: string
  updated_at: string
  created_by: number | null
}

export interface AssetAppListResponse {
  items: AssetApp[]
  total: number
}

export interface AssetAppCreateRequest {
  name: string
  version?: string | null
  category?: string | null
  port?: number | null
  protocol?: string | null
  install_path?: string | null
  config_path?: string | null
  notes?: string | null
}

export interface AssetAppUpdateRequest {
  name?: string | null
  version?: string | null
  category?: string | null
  port?: number | null
  protocol?: string | null
  install_path?: string | null
  config_path?: string | null
  notes?: string | null
  status?: AppStatus | null
}

export interface AppSearchItem {
  id: number
  asset_id: number
  name: string
  version: string | null
  category: string | null
  port: number | null
  asset_no: string
  ip_address: string
  hostname: string | null
}

export interface AppSearchResponse {
  items: AppSearchItem[]
  total: number
}
