<script setup lang="ts">
/**
 * App service create/edit dialog
 */
import { ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { createAssetApp, updateAssetApp, fetchAppNames } from '@/api/asset-app'
import { APP_CATEGORIES } from '@/constants/app-categories'
import type { AssetApp, AssetAppCreateRequest, AssetAppUpdateRequest } from '@/types/asset-app'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps<{
  visible: boolean
  assetId: number
  editing: AssetApp | null
}>()

const emit = defineEmits<{
  (e: 'update:visible', val: boolean): void
  (e: 'success'): void
}>()

const isEdit = computed(() => !!props.editing)
const title = computed(() => (isEdit.value ? t('components.appService.dialog.editTitle') : t('components.appService.dialog.title')))

// Form data
const form = ref({
  name: '',
  version: '',
  category: '',
  port: null as number | null,
  protocol: 'tcp',
  install_path: '',
  config_path: '',
  notes: '',
})

// Autocomplete data
const appNames = ref<string[]>([])
const appNameSuggestions = computed(() => {
  const q = form.value.name.toLowerCase()
  if (!q) return appNames.value.map((n) => ({ value: n }))
  return appNames.value
    .filter((n) => n.toLowerCase().includes(q))
    .map((n) => ({ value: n }))
})

const submitting = ref(false)

// Watch visible changes to initialize form
watch(
  () => props.visible,
  async (val) => {
    if (val) {
      if (props.editing) {
        form.value = {
          name: props.editing.name,
          version: props.editing.version || '',
          category: props.editing.category || '',
          port: props.editing.port,
          protocol: props.editing.protocol || 'tcp',
          install_path: props.editing.install_path || '',
          config_path: props.editing.config_path || '',
          notes: props.editing.notes || '',
        }
      } else {
        form.value = {
          name: '',
          version: '',
          category: '',
          port: null,
          protocol: 'tcp',
          install_path: '',
          config_path: '',
          notes: '',
        }
      }
      // Load autocomplete data
      try {
        appNames.value = await fetchAppNames()
      } catch {
        // Silently fail
      }
    }
  }
)

function handleClose() {
  emit('update:visible', false)
}

async function handleSubmit() {
  if (!form.value.name.trim()) {
    ElMessage.warning(t('components.appService.dialog.nameRequired'))
    return
  }

  submitting.value = true
  try {
    if (isEdit.value && props.editing) {
      const data: AssetAppUpdateRequest = {
        name: form.value.name.trim(),
        version: form.value.version.trim() || null,
        category: form.value.category || null,
        port: form.value.port || null,
        protocol: form.value.port ? form.value.protocol : null,
        install_path: form.value.install_path.trim() || null,
        config_path: form.value.config_path.trim() || null,
        notes: form.value.notes.trim() || null,
      }
      await updateAssetApp(props.assetId, props.editing.id, data)
      ElMessage.success(t('components.appService.dialog.success.updated'))
    } else {
      const data: AssetAppCreateRequest = {
        name: form.value.name.trim(),
        version: form.value.version.trim() || null,
        category: form.value.category || null,
        port: form.value.port || null,
        protocol: form.value.port ? form.value.protocol : null,
        install_path: form.value.install_path.trim() || null,
        config_path: form.value.config_path.trim() || null,
        notes: form.value.notes.trim() || null,
      }
      await createAssetApp(props.assetId, data)
      ElMessage.success(t('components.appService.dialog.success.created'))
    }
    emit('success')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="visible"
    :title="title"
    width="560px"
    @close="handleClose"
    destroy-on-close
  >
    <el-form :model="form" label-width="100px" label-position="right">
      <el-form-item :label="t('components.appService.dialog.name')" required>
        <el-autocomplete
          v-model="form.name"
          :fetch-suggestions="(_q: string, cb: Function) => cb(appNameSuggestions)"
          :placeholder="t('components.appService.dialog.namePlaceholder')"
          style="width: 100%"
          clearable
        />
      </el-form-item>

      <el-form-item :label="t('components.appService.dialog.version')">
        <el-input v-model="form.version" :placeholder="t('components.appService.dialog.versionPlaceholder')" clearable />
      </el-form-item>

      <el-form-item :label="t('components.appService.dialog.category')">
        <el-select
          v-model="form.category"
          :placeholder="t('components.appService.dialog.categoryPlaceholder')"
          filterable
          allow-create
          clearable
          style="width: 100%"
        >
          <el-option
            v-for="cat in APP_CATEGORIES"
            :key="cat.value"
            :label="cat.label"
            :value="cat.value"
          />
        </el-select>
      </el-form-item>

      <el-form-item :label="t('components.appService.dialog.port')">
        <div style="display: flex; gap: 8px; width: 100%">
          <el-input-number
            v-model="form.port"
            :min="1"
            :max="65535"
            :placeholder="t('components.appService.dialog.portPlaceholder')"
            controls-position="right"
            style="flex: 1"
          />
          <el-select
            v-if="form.port"
            v-model="form.protocol"
            style="width: 100px"
          >
            <el-option label="TCP" value="tcp" />
            <el-option label="UDP" value="udp" />
          </el-select>
        </div>
      </el-form-item>

      <el-form-item :label="t('components.appService.dialog.installPath')">
        <el-input v-model="form.install_path" :placeholder="t('components.appService.dialog.installPathPlaceholder')" clearable />
      </el-form-item>

      <el-form-item :label="t('components.appService.dialog.configPath')">
        <el-input v-model="form.config_path" :placeholder="t('components.appService.dialog.configPathPlaceholder')" clearable />
      </el-form-item>

      <el-form-item :label="t('components.appService.dialog.notes')">
        <el-input
          v-model="form.notes"
          type="textarea"
          :rows="3"
          :placeholder="t('components.appService.dialog.notesPlaceholder')"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="handleClose">{{ t('components.appService.dialog.cancel') }}</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">
        {{ isEdit ? t('components.appService.dialog.save') : t('components.appService.dialog.add') }}
      </el-button>
    </template>
  </el-dialog>
</template>
