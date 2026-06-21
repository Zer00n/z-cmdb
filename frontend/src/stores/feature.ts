/**
 * Feature flags store
 * Fetched from GET /api/features on app init, cached in memory
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchFeatures } from '@/api/features'

export const useFeatureStore = defineStore('feature', () => {
  const costAccounting = ref(false)

  async function fetchFeatureFlags() {
    try {
      const data = await fetchFeatures()
      costAccounting.value = !!data.cost_accounting
    } catch {
      costAccounting.value = false
    }
  }

  return {
    costAccounting,
    fetchFeatureFlags,
  }
})
