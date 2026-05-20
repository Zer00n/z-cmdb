/**
 * 安全报表 API 封装
 */
import request from './request'
import type {
  AssetChangesData,
  DangerousPortsData,
  PortExposureData,
  ShadowAssetsData,
} from '@/types/report'

/** 端口暴露面分析 */
export function fetchPortExposure(): Promise<PortExposureData> {
  return request.get('/api/reports/port-exposure')
}

/** 危险端口列表 */
export function fetchDangerousPorts(): Promise<DangerousPortsData> {
  return request.get('/api/reports/dangerous-ports')
}

/** 影子资产 */
export function fetchShadowAssets(): Promise<ShadowAssetsData> {
  return request.get('/api/reports/shadow-assets')
}

/** 资产变化时间线 */
export function fetchAssetChanges(): Promise<AssetChangesData> {
  return request.get('/api/reports/asset-changes')
}
