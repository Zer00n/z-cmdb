<script setup lang="ts">
/**
 * Import Preset Settings page
 * Two-column layout: category list (left) + preset table (right)
 */
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { presetApi, type Preset } from '@/api/importPreset'
import { useImportPresetStore, PRESET_CATEGORIES } from '@/stores/importPreset'

const { t } = useI18n()
const store = useImportPresetStore()

// ── State ────────────────────────────────────────────────
const activeCategory = ref<string>('location')
const searchQuery = ref('')
const loading = ref(false)
const presets = ref<Preset[]>([])

// Dialog state
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const editingId = ref<number | null>(null)
const form = ref({ value: '', remark: '', sort_order: 0, is_default: false })
const formError = ref('')

// ── Computed ─────────────────────────────────────────────
const categoryItems = computed(() =>
  PRESET_CATEGORIES.map(c => ({
    key: c,
    label: t(`preset.category.${c}`),
  }))
)

const filteredPresets = computed(() => {
  if (!searchQuery.value.trim()) return presets.value
  const q = searchQuery.value.trim().toLowerCase()
  return presets.value.filter(p => p.value.toLowerCase().includes(q))
})

// ── Data loading ─────────────────────────────────────────
async function loadPresets() {
  loading.value = true
  try {
    presets.value = await presetApi.list(activeCategory.value)
  } finally {
    loading.value = false
  }
}

function selectCategory(key: string) {
  activeCategory.value = key
  searchQuery.value = ''
  loadPresets()
}

// ── CRUD ─────────────────────────────────────────────────
function openCreate() {
  dialogMode.value = 'create'
  editingId.value = null
  form.value = { value: '', remark: '', sort_order: 0, is_default: false }
  formError.value = ''
  dialogVisible.value = true
}

function openEdit(preset: Preset) {
  dialogMode.value = 'edit'
  editingId.value = preset.id
  form.value = {
    value: preset.value,
    remark: preset.remark ?? '',
    sort_order: preset.sort_order,
    is_default: preset.is_default,
  }
  formError.value = ''
  dialogVisible.value = true
}

async function submitForm() {
  const trimmed = form.value.value.trim()
  if (!trimmed) return

  formError.value = ''
  try {
    if (dialogMode.value === 'create') {
      await presetApi.create({
        category: activeCategory.value,
        value: trimmed,
        remark: form.value.remark || undefined,
        sort_order: form.value.sort_order,
        is_default: form.value.is_default,
      })
    } else {
      await presetApi.update(editingId.value!, {
        value: trimmed,
        remark: form.value.remark || undefined,
        sort_order: form.value.sort_order,
      })
      if (form.value.is_default) {
        await presetApi.setDefault(editingId.value!)
      }
    }
    dialogVisible.value = false
    await loadPresets()
    await store.reload(activeCategory.value)
    ElMessage.success(t('common.success'))
  } catch (err: any) {
    if (err?.response?.status === 409) {
      formError.value = t('preset.duplicateError')
    }
  }
}

async function handleDelete(preset: Preset) {
  try {
    await ElMessageBox.confirm(
      t('preset.deleteConfirm'),
      t('common.delete'),
      { type: 'warning', confirmButtonText: t('common.confirm'), cancelButtonText: t('common.cancel') }
    )
    await presetApi.remove(preset.id)
    await loadPresets()
    await store.reload(activeCategory.value)
    ElMessage.success(t('common.success'))
  } catch {
    // cancelled
  }
}

async function handleSetDefault(preset: Preset) {
  await presetApi.setDefault(preset.id)
  await loadPresets()
  await store.reload(activeCategory.value)
  ElMessage.success(t('common.success'))
}

async function handleSync() {
  try {
    await ElMessageBox.confirm(
      t('preset.syncConfirm'),
      t('preset.syncFromAssets'),
      { type: 'info', confirmButtonText: t('common.confirm'), cancelButtonText: t('common.cancel') }
    )
    const result = await presetApi.syncFromAssets()
    await loadPresets()
    await store.reloadAll()
    ElMessage.success(t('preset.syncResult', { ...result }))
  } catch {
    // cancelled
  }
}

// ── Init ─────────────────────────────────────────────────
onMounted(() => {
  loadPresets()
})
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1>{{ t('preset.title') }}</h1>
      <p class="page-desc">{{ t('preset.description') }}</p>
    </div>

    <div class="preset-layout">
      <!-- Left panel: category list -->
      <div class="category-panel">
        <div
          v-for="cat in categoryItems"
          :key="cat.key"
          class="category-item"
          :class="{ active: activeCategory === cat.key }"
          @click="selectCategory(cat.key)"
        >
          {{ cat.label }}
        </div>
      </div>

      <!-- Right panel: preset table -->
      <div class="preset-content">
        <div class="toolbar">
          <el-input
            v-model="searchQuery"
            :placeholder="t('preset.search')"
            clearable
            style="width: 240px"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <div class="toolbar-actions">
            <el-button type="primary" @click="openCreate">
              <el-icon><Plus /></el-icon>
              {{ t('preset.addNewShort') }}
            </el-button>
            <el-button @click="handleSync">
              <el-icon><Download /></el-icon>
              {{ t('preset.syncFromAssets') }}
            </el-button>
          </div>
        </div>

        <el-table :data="filteredPresets" v-loading="loading" stripe style="width: 100%">
          <el-table-column :label="t('preset.value')" prop="value" min-width="200">
            <template #default="{ row }">
              <span>{{ row.value }}</span>
              <el-tag v-if="row.is_default" type="success" size="small" style="margin-left: 8px">
                {{ t('preset.isDefault') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="t('preset.sort')" prop="sort_order" width="100" align="center" />
          <el-table-column :label="t('preset.remark')" prop="remark" min-width="150">
            <template #default="{ row }">
              {{ row.remark || '-' }}
            </template>
          </el-table-column>
          <el-table-column :label="t('common.actions')" width="240" align="center">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="openEdit(row)">
                {{ t('common.edit') }}
              </el-button>
              <el-button
                link
                type="primary"
                size="small"
                :disabled="row.is_default"
                @click="handleSetDefault(row)"
              >
                {{ t('preset.setDefault') }}
              </el-button>
              <el-button link type="danger" size="small" @click="handleDelete(row)">
                {{ t('common.delete') }}
              </el-button>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty :description="t('preset.empty')" :image-size="80" />
          </template>
        </el-table>
      </div>
    </div>

    <!-- Add / Edit dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? t('preset.addNewShort') : t('common.edit')"
      width="420px"
      destroy-on-close
    >
      <el-form label-position="top">
        <el-form-item :label="t('preset.value')" required>
          <el-input v-model="form.value" :maxlength="255" />
          <div v-if="formError" class="form-error">{{ formError }}</div>
        </el-form-item>
        <el-form-item :label="t('preset.remark')">
          <el-input v-model="form.remark" :maxlength="255" />
        </el-form-item>
        <el-form-item :label="t('preset.sort')">
          <el-input-number v-model="form.sort_order" :min="0" :max="9999" />
        </el-form-item>
        <el-form-item :label="t('preset.isDefault')">
          <el-switch v-model="form.is_default" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :disabled="!form.value.trim()" @click="submitForm">
          {{ t('common.confirm') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-container {
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  height: 100%;
}

.page-header h1 {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
}
.page-desc {
  color: var(--neutral-500);
  font-size: 13px;
  margin-top: 4px;
}

.preset-layout {
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: var(--space-4);
  flex: 1;
  min-height: 0;
}

.category-panel {
  background: var(--surface-base);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(15, 23, 42, 0.06);
  padding: var(--space-3);
}

.category-item {
  padding: 10px 14px;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 14px;
  color: var(--neutral-700);
  transition: all 0.15s ease;
}
.category-item:hover {
  background: var(--color-primary-50);
  color: var(--neutral-900);
}
.category-item.active {
  background: linear-gradient(90deg, rgba(37, 99, 235, 0.10) 0%, rgba(99, 102, 241, 0.06) 100%);
  color: var(--color-primary-700);
  font-weight: 600;
}

.preset-content {
  background: var(--surface-base);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(15, 23, 42, 0.06);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  min-height: 0;
  overflow: auto;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.toolbar-actions {
  display: flex;
  gap: var(--space-2);
}

.form-error {
  color: var(--color-danger);
  font-size: 12px;
  margin-top: 4px;
}
</style>
