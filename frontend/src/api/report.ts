/**
 * Security report API wrappers
 */
import request from './request'
import type {
  AssetChangesData,
  DangerousPortsData,
  PortExposureData,
  ShadowAssetsData,
} from '@/types/report'

/** Port exposure analysis */
export function fetchPortExposure(): Promise<PortExposureData> {
  return request.get('/api/reports/port-exposure')
}

/** Dangerous port list */
export function fetchDangerousPorts(): Promise<DangerousPortsData> {
  return request.get('/api/reports/dangerous-ports')
}

/** Shadow assets */
export function fetchShadowAssets(): Promise<ShadowAssetsData> {
  return request.get('/api/reports/shadow-assets')
}

/** Asset change timeline */
export function fetchAssetChanges(): Promise<AssetChangesData> {
  return request.get('/api/reports/asset-changes')
}
