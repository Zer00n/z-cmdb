/**
 * Feature flags API
 */
import request from './request'

export async function fetchFeatures(): Promise<{ cost_accounting: boolean }> {
  return request.get('/api/features')
}
