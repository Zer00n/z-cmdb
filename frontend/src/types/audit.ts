/**
 * 审计日志 TypeScript 类型
 */

export interface AuditLog {
  id: number
  timestamp: string
  user_id: number | null
  username: string | null
  user_role: string | null
  action_type: string
  target_type: string | null
  target_id: string | null
  ip_address: string | null
  user_agent: string | null
  details: string | null
  result: string
}

export interface AuditLogListResponse {
  items: AuditLog[]
  total: number
  page: number
  page_size: number
}

export interface AuditQueryParams {
  page?: number
  page_size?: number
  action_type?: string
  user_id?: number
  target_type?: string
}
