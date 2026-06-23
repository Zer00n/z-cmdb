/**
 * Import Preset API client
 */
import request from './request'

export interface Preset {
  id: number
  category: string
  value: string
  is_default: boolean
  sort_order: number
  remark: string | null
}

export interface PresetCreate {
  category: string
  value: string
  is_default?: boolean
  sort_order?: number
  remark?: string
}

export interface PresetUpdate {
  value?: string
  sort_order?: number
  remark?: string
}

export interface SyncResult {
  location: number
  owner: number
  business_system: number
}

export const presetApi = {
  list: (category?: string, q?: string) =>
    request.get<any, Preset[]>('/api/import-presets', { params: { category, q } }),

  categories: () =>
    request.get<any, { key: string; label_key: string }[]>('/api/import-presets/categories'),

  create: (data: PresetCreate) =>
    request.post<any, Preset>('/api/import-presets', data),

  update: (id: number, data: PresetUpdate) =>
    request.put<any, Preset>(`/api/import-presets/${id}`, data),

  setDefault: (id: number) =>
    request.patch<any, Preset>(`/api/import-presets/${id}/default`),

  remove: (id: number) =>
    request.delete(`/api/import-presets/${id}`),

  syncFromAssets: () =>
    request.post<any, SyncResult>('/api/import-presets/sync-from-assets'),
}
