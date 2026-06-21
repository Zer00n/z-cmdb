/**
 * Asset overview API
 */
import request from './request'
import type { DashboardSummary } from '@/types/dashboard'

/** Get asset overview aggregated data (force=true bypasses backend cache) */
export function getSummary(force = false): Promise<DashboardSummary> {
  return request.get('/api/reports/dashboard-summary', { params: { force } })
}
