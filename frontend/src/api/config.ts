/**
 * System configuration API wrappers
 */
import request from './request'

/** Read all config */
export function fetchConfig(): Promise<Record<string, { value: string; description: string; updated_at: string | null }>> {
  return request.get('/api/config')
}

/** Update config */
export function updateConfig(data: Record<string, string>): Promise<{ message: string; updated: string[] }> {
  return request.patch('/api/config', data)
}
