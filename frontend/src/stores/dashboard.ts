/**
 * 资产总览状态管理
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getSummary } from '@/api/dashboard'
import type { DashboardSummary } from '@/types/dashboard'

export const useDashboardStore = defineStore('dashboard', () => {
  const summary = ref<DashboardSummary | null>(null)
  const loading = ref(false)

  /**
   * 拉取聚合数据
   * @param force true 时绕过后端缓存（仅「刷新数据」按钮使用）
   */
  async function fetchSummary(force = false) {
    loading.value = true
    try {
      summary.value = await getSummary(force)
    } catch (e) {
      // HTTP 错误已由 request 拦截器统一提示，这里仅记录
      console.error('[dashboard] fetchSummary failed', e)
    } finally {
      loading.value = false
    }
  }

  return { summary, loading, fetchSummary }
})
