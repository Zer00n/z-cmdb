/**
 * 资产总览状态管理（静态，无轮询）
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getSummary, getLayout, saveLayout, saveDefaultLayout } from '@/api/dashboard'
import type { DashboardSummary, DashboardConfig, DrillTarget } from '@/types/dashboard'
import { PANELS } from '@/components/dashboard/registry'
import router from '@/router'

const DEFAULT_CONFIG: DashboardConfig = {
  panels: PANELS.map(p => ({ id: p.id, visible: true })),
  refreshIntervalSec: 0,
  filters: {},
  theme: 'light',
}

export const useDashboardStore = defineStore('dashboard', () => {
  const summary = ref<DashboardSummary | null>(null)
  const config = ref<DashboardConfig>({ ...DEFAULT_CONFIG })
  const loading = ref(false)

  async function fetchSummary() {
    loading.value = true
    try {
      summary.value = await getSummary(true)
    } catch (e) {
      console.error('[dashboard] fetchSummary failed', e)
    } finally {
      loading.value = false
    }
  }

  async function loadConfig() {
    try {
      const cfg = await getLayout()
      if (cfg && cfg.panels?.length) {
        config.value = cfg
      }
    } catch {
      // 接口不存在或出错时使用默认配置
    }
  }

  async function saveConfig() {
    try {
      await saveLayout(config.value)
    } catch (e) {
      console.error('[dashboard] saveConfig failed', e)
    }
  }

  async function saveConfigAsDefault() {
    try {
      await saveDefaultLayout(config.value)
    } catch (e) {
      console.error('[dashboard] saveConfigAsDefault failed', e)
    }
  }

  function drillTo(target: DrillTarget) {
    router.push({ path: target.route, query: target.query })
  }

  function resetConfig() {
    config.value = { ...DEFAULT_CONFIG, panels: DEFAULT_CONFIG.panels.map(p => ({ ...p })) }
  }

  return {
    summary, config, loading,
    fetchSummary, loadConfig, saveConfig, saveConfigAsDefault,
    drillTo, resetConfig,
  }
})
