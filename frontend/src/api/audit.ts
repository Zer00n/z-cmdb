/**
 * 审计日志 API 封装
 */
import request from './request'
import type { AuditLogListResponse, AuditQueryParams } from '@/types/audit'

/** 查询审计日志 */
export function fetchAuditLogs(params?: AuditQueryParams): Promise<AuditLogListResponse> {
  return request.get('/api/audit/logs', { params })
}

/** 导出审计报告 */
export function exportAuditReport(): Promise<Blob> {
  return request.post('/api/audit/export', null, { responseType: 'blob' })
}
