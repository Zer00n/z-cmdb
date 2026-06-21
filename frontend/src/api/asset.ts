/**
 * Asset management API wrappers
 */
import request from './request'
import type {
  Asset,
  AssetCreateRequest,
  AssetListResponse,
  AssetQueryParams,
  AssetUpdateRequest,
} from '@/types/asset'

/** Asset list (supports filtering/search/pagination) */
export function fetchAssetList(params?: AssetQueryParams): Promise<AssetListResponse> {
  return request.get('/api/assets', { params })
}

/** Asset detail (includes port list) */
export function fetchAsset(id: number): Promise<Asset> {
  return request.get(`/api/assets/${id}`)
}

/** Manually create asset */
export function createAsset(data: AssetCreateRequest): Promise<Asset> {
  return request.post('/api/assets', data)
}

/** Update asset */
export function updateAsset(id: number, data: AssetUpdateRequest): Promise<Asset> {
  return request.patch(`/api/assets/${id}`, data)
}

/** Decommission asset (soft delete) */
export function decommissionAsset(id: number): Promise<void> {
  return request.delete(`/api/assets/${id}`)
}

/** Export asset CSV */
export function exportAssetsCsv(params?: AssetQueryParams): Promise<Blob> {
  return request.get('/api/assets/export', {
    params,
    responseType: 'blob',
  })
}

/** Export assets+apps as threat hunting compatible CSV */
export function exportAssetsForThreatHunting(params?: AssetQueryParams & {
  skip_empty_apps?: boolean
  include_decommissioned?: boolean
  default_environment?: string
}): Promise<Blob> {
  return request.get('/api/assets/export-threat-hunting', {
    params,
    responseType: 'blob',
  })
}
