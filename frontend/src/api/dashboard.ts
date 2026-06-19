/**
 * 大屏 API 封装
 */
import request from './request'
import type { DashboardSummary, DashboardConfig } from '@/types/dashboard'

/** 获取大屏聚合数据 */
export function getSummary(force = false): Promise<DashboardSummary> {
  return request.get('/api/reports/dashboard-summary', { params: { force } })
}

/** 获取当前用户生效布局 */
export function getLayout(): Promise<DashboardConfig> {
  return request.get('/api/dashboard/layout')
}

/** 保存当前用户个人布局 */
export function saveLayout(cfg: DashboardConfig): Promise<void> {
  return request.put('/api/dashboard/layout', cfg)
}

/** 保存全局默认布局（super_admin） */
export function saveDefaultLayout(cfg: DashboardConfig): Promise<void> {
  return request.put('/api/dashboard/layout/default', cfg)
}
