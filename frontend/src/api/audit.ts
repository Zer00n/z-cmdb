/**
 * Audit log API wrappers
 */
import request from './request'
import type { AuditLogListResponse, AuditQueryParams } from '@/types/audit'

/** Query audit logs */
export function fetchAuditLogs(params?: AuditQueryParams): Promise<AuditLogListResponse> {
  return request.get('/api/audit/logs', { params })
}

/** Export audit report */
export function exportAuditReport(): Promise<Blob> {
  return request.post('/api/audit/export', null, { responseType: 'blob' })
}
