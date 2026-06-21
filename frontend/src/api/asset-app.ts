/**
 * App service inventory API wrappers
 */
import request from './request'
import type {
  AssetApp,
  AssetAppCreateRequest,
  AssetAppUpdateRequest,
  AssetAppListResponse,
  AppSearchResponse,
} from '@/types/asset-app'

/** List all apps for an asset */
export function fetchAssetApps(assetId: number): Promise<AssetAppListResponse> {
  return request.get(`/api/assets/${assetId}/apps`)
}

/** Create app */
export function createAssetApp(assetId: number, data: AssetAppCreateRequest): Promise<AssetApp> {
  return request.post(`/api/assets/${assetId}/apps`, data)
}

/** Update app */
export function updateAssetApp(assetId: number, appId: number, data: AssetAppUpdateRequest): Promise<AssetApp> {
  return request.patch(`/api/assets/${assetId}/apps/${appId}`, data)
}

/** Delete app (soft delete) */
export function deleteAssetApp(assetId: number, appId: number): Promise<void> {
  return request.delete(`/api/assets/${assetId}/apps/${appId}`)
}

/** Export asset app inventory CSV */
export function exportAssetAppsCsv(assetId: number): Promise<Blob> {
  return request.get(`/api/assets/${assetId}/apps/export`, {
    responseType: 'blob',
  })
}

/** Global app search */
export function searchApps(q: string): Promise<AppSearchResponse> {
  return request.get('/api/apps/search', { params: { q } })
}

/** Get all app names (deduplicated, for autocomplete) */
export function fetchAppNames(): Promise<string[]> {
  return request.get('/api/apps/names')
}
