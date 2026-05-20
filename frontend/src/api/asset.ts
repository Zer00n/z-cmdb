/**
 * 资产管理 API 封装
 */
import request from './request'
import type {
  Asset,
  AssetCreateRequest,
  AssetListResponse,
  AssetQueryParams,
  AssetUpdateRequest,
} from '@/types/asset'

/** 资产列表（支持筛选/搜索/分页） */
export function fetchAssetList(params?: AssetQueryParams): Promise<AssetListResponse> {
  return request.get('/api/assets', { params })
}

/** 资产详情（含端口列表） */
export function fetchAsset(id: number): Promise<Asset> {
  return request.get(`/api/assets/${id}`)
}

/** 手动新增资产 */
export function createAsset(data: AssetCreateRequest): Promise<Asset> {
  return request.post('/api/assets', data)
}

/** 更新资产 */
export function updateAsset(id: number, data: AssetUpdateRequest): Promise<Asset> {
  return request.patch(`/api/assets/${id}`, data)
}

/** 下线资产（软删除） */
export function decommissionAsset(id: number): Promise<void> {
  return request.delete(`/api/assets/${id}`)
}

/** 导出资产 CSV */
export function exportAssetsCsv(params?: AssetQueryParams): Promise<Blob> {
  return request.get('/api/assets/export', {
    params,
    responseType: 'blob',
  })
}
