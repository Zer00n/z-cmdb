/**
 * 系统配置 API 封装
 */
import request from './request'

/** 读取所有配置 */
export function fetchConfig(): Promise<Record<string, { value: string; description: string; updated_at: string | null }>> {
  return request.get('/api/config')
}

/** 修改配置 */
export function updateConfig(data: Record<string, string>): Promise<{ message: string; updated: string[] }> {
  return request.patch('/api/config', data)
}
