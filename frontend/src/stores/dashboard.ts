/**
 * Asset overview state management
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getSummary } from '@/api/dashboard'
import type { DashboardSummary } from '@/types/dashboard'

export const useDashboardStore = defineStore('dashboard', () => {
  const summary = ref<DashboardSummary | null>(null)
  const loading = ref(false)

  /**
   * Fetch aggregated data
   * @param force bypass backend cache when true (only used by "refresh" button)
   */
  async function fetchSummary(force = false) {
    loading.value = true
    try {
      summary.value = await getSummary(force)
    } catch (e) {
      // HTTP errors handled by request interceptor, only log here
      console.error('[dashboard] fetchSummary failed', e)
    } finally {
      loading.value = false
    }
  }

  return { summary, loading, fetchSummary }
})
