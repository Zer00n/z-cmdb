/**
 * 功能特性开关 Store
 * 应用初始化时从 GET /api/features 拉取，缓存在内存中
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
