/**
 * Import Preset Pinia store
 * Centralized cache for preset options, shared across all pages
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { presetApi, type Preset } from '@/api/importPreset'

export const PRESET_CATEGORIES = ['location', 'owner', 'business_system'] as const

export const useImportPresetStore = defineStore('importPreset', () => {
  const byCategory = ref<Record<string, Preset[]>>({})
  const loaded = ref(false)

  const options = computed(() => (cat: string): Preset[] => byCategory.value[cat] ?? [])

  const defaultValue = computed(() => (cat: string): string => {
    const presets = byCategory.value[cat] ?? []
    return presets.find(p => p.is_default)?.value ?? ''
  })

  async function ensureLoaded() {
    if (loaded.value) return
    await Promise.all(PRESET_CATEGORIES.map(c => reload(c)))
    loaded.value = true
  }

  async function reload(cat: string) {
    byCategory.value[cat] = await presetApi.list(cat)
  }

  async function reloadAll() {
    await Promise.all(PRESET_CATEGORIES.map(c => reload(c)))
  }

  async function addInline(cat: string, value: string): Promise<Preset> {
    const p = await presetApi.create({ category: cat, value })
    await reload(cat)
    return p
  }

  return {
    byCategory,
    loaded,
    options,
    defaultValue,
    ensureLoaded,
    reload,
    reloadAll,
    addInline,
  }
})
