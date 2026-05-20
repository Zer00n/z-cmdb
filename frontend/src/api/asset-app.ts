/**
 * 应用服务清单 API 封装
 */
import request from './request'
import type {
  AssetApp,
  AssetAppCreateRequest,
  AssetAppUpdateRequest,
  AssetAppListResponse,
  AppSearchResponse,
} from '@/types/asset-app'

/** 列出某资产的所有应用 */
export function fetchAssetApps(assetId: number): Promise<AssetAppListResponse> {
  return request.get(`/api/assets/${assetId}/apps`)
}

/** 新增应用 */
export function createAssetApp(assetId: number, data: AssetAppCreateRequest): Promise<AssetApp> {
  return request.post(`/api/assets/${assetId}/apps`, data)
}

/** 修改应用 */
export function updateAssetApp(assetId: number, appId: number, data: AssetAppUpdateRequest): Promise<AssetApp> {
  return request.patch(`/api/assets/${assetId}/apps/${appId}`, data)
}

/** 删除应用（软删除） */
export function deleteAssetApp(assetId: number, appId: number): Promise<void> {
  return request.delete(`/api/assets/${assetId}/apps/${appId}`)
}

/** 导出某资产应用清单 CSV */
export function exportAssetAppsCsv(assetId: number): Promise<Blob> {
  return request.get(`/api/assets/${assetId}/apps/export`, {
    responseType: 'blob',
  })
}

/** 全局应用搜索 */
export function searchApps(q: string): Promise<AppSearchResponse> {
  return request.get('/api/apps/search', { params: { q } })
}

/** 获取所有应用名（去重，用于 autocomplete） */
export function fetchAppNames(): Promise<string[]> {
  return request.get('/api/apps/names')
}
