<script setup lang="ts">
/**
 * PresetSelect — reusable dropdown for preset fields
 * Supports: filterable select, clearable, inline add via footer slot
 */
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useImportPresetStore } from '@/stores/importPreset'

const props = defineProps<{
  category: string
  modelValue: string
  readonly?: boolean
  placeholder?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const { t } = useI18n()
const store = useImportPresetStore()

const adding = ref(false)
const draft = ref('')

const model = computed({
  get: () => props.modelValue,
  set: (v: string) => emit('update:modelValue', v),
})

const options = computed(() => store.options(props.category))

const fieldLabel = computed(() => t(`preset.category.${props.category}`))

onMounted(() => {
  store.ensureLoaded()
})

async function confirmAdd() {
  const v = draft.value.trim()
  if (!v) return
  try {
    const p = await store.addInline(props.category, v)
    model.value = p.value
    draft.value = ''
    adding.value = false
  } catch {
    // Error handled by request interceptor
  }
}

function cancelAdd() {
  adding.value = false
  draft.value = ''
}
</script>

<template>
  <el-select
    v-model="model"
    :placeholder="placeholder || fieldLabel"
    filterable
    clearable
    :disabled="readonly"
    style="width: 100%"
  >
    <el-option
      v-for="o in options"
      :key="o.id"
      :label="o.value"
      :value="o.value"
    />
    <template #footer v-if="!readonly">
      <div v-if="!adding" class="preset-add-btn">
        <el-button text size="small" @click="adding = true">
          {{ t('preset.inlineAdd', { field: fieldLabel }) }}
        </el-button>
      </div>
      <div v-else class="preset-add-form">
        <el-input
          v-model="draft"
          size="small"
          :placeholder="fieldLabel"
          @keyup.enter="confirmAdd"
          style="flex: 1"
        />
        <el-button size="small" type="primary" @click="confirmAdd">
          {{ t('common.confirm') }}
        </el-button>
        <el-button size="small" @click="cancelAdd">
          {{ t('common.cancel') }}
        </el-button>
      </div>
    </template>
  </el-select>
</template>

<style scoped>
.preset-add-btn {
  padding: 4px 0;
  border-top: 1px solid var(--el-border-color-lighter);
}
.preset-add-form {
  display: flex;
  gap: 6px;
  padding: 4px 0;
  border-top: 1px solid var(--el-border-color-lighter);
}
</style>
