/**
 * 资产总览 API
 */
import request from './request'
import type { DashboardSummary } from '@/types/dashboard'

/** 获取资产总览聚合数据（force=true 绕过后端缓存） */
export function getSummary(force = false): Promise<DashboardSummary> {
  return request.get('/api/reports/dashboard-summary', { params: { force } })
}
