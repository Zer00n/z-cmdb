<script setup lang="ts">
/**
 * BatchPresetToolbar — batch-apply preset values to table rows
 * Pure frontend operation: emits apply event, parent handles row updates
 */
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useImportPresetStore, PRESET_CATEGORIES } from '@/stores/importPreset'
import PresetSelect from './PresetSelect.vue'

const props = defineProps<{
  diffTypes?: string[]  // available diff type options, e.g. ['new', 'changed']
}>()

const emit = defineEmits<{
  apply: [payload: { category: string; value: string; scope: string }]
}>()

const { t } = useI18n()

const selectedField = ref<string>('location')
const selectedValue = ref<string>('')
const selectedScope = ref<string>('selected')

const categoryOptions = computed(() =>
  PRESET_CATEGORIES.map(c => ({
    label: t(`preset.category.${c}`),
    value: c,
  }))
)

const scopeOptions = computed(() => {
  const opts = [
    { label: t('preset.batchToolbar.selectedRows'), value: 'selected' },
    { label: t('preset.batchToolbar.allRows'), value: 'all' },
  ]
  if (props.diffTypes) {
    for (const dt of props.diffTypes) {
      opts.push({ label: t(`preset.batchToolbar.${dt}`) || dt, value: dt })
    }
  }
  return opts
})

function handleApply() {
  if (!selectedValue.value) return
  emit('apply', {
    category: selectedField.value,
    value: selectedValue.value,
    scope: selectedScope.value,
  })
}
</script>

<template>
  <div class="batch-toolbar">
    <span class="toolbar-label">{{ t('preset.batchToolbar.field') }}</span>
    <el-select v-model="selectedField" style="width: 140px" size="small">
      <el-option
        v-for="opt in categoryOptions"
        :key="opt.value"
        :label="opt.label"
        :value="opt.value"
      />
    </el-select>

    <span class="toolbar-label">{{ t('preset.batchToolbar.value') }}</span>
    <PresetSelect
      :category="selectedField"
      v-model="selectedValue"
      style="width: 180px"
    />

    <span class="toolbar-label">{{ t('preset.batchToolbar.scope') }}</span>
    <el-select v-model="selectedScope" style="width: 130px" size="small">
      <el-option
        v-for="opt in scopeOptions"
        :key="opt.value"
        :label="opt.label"
        :value="opt.value"
      />
    </el-select>

    <el-button type="primary" size="small" :disabled="!selectedValue" @click="handleApply">
      {{ t('preset.batchToolbar.apply') }}
    </el-button>
  </div>
</template>

<style scoped>
.batch-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--el-fill-color-light);
  border-radius: var(--radius-md);
  flex-wrap: wrap;
}
.toolbar-label {
  font-size: 13px;
  color: var(--neutral-600);
  white-space: nowrap;
}
</style>
