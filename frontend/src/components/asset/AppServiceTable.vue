<script setup lang="ts">
/**
 * 应用服务清单表格组件
 * 用于资产详情页"应用"Tab
 */
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchAssetApps, deleteAssetApp, exportAssetAppsCsv } from '@/api/asset-app'
import { getCategoryLabel } from '@/constants/app-categories'
import type { AssetApp } from '@/types/asset-app'
import AppServiceDialog from './AppServiceDialog.vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps<{
  assetId: number
}>()

const emit = defineEmits<{
  (e: 'countChange', count: number): void
  (e: 'portsChanged'): void
}>()

const loading = ref(false)
const apps = ref<AssetApp[]>([])
const dialogVisible = ref(false)
const editingApp = ref<AssetApp | null>(null)

async function loadApps() {
  loading.value = true
  try {
    const res = await fetchAssetApps(props.assetId)
    apps.value = res.items
    emit('countChange', res.total)
  } finally {
    loading.value = false
  }
}

function handleCreate() {
  editingApp.value = null
  dialogVisible.value = true
}

function handleEdit(app: AssetApp) {
  editingApp.value = app
  dialogVisible.value = true
}

async function handleDelete(app: AssetApp) {
  const appName = `${app.name}${app.version ? ' ' + app.version : ''}`
  await ElMessageBox.confirm(
    t('components.appService.table.deleteConfirm', { name: appName }),
    t('components.appService.table.deleteTitle'),
    { confirmButtonText: t('components.appService.table.deleteBtn'), cancelButtonText: t('common.cancel'), type: 'warning' }
  )
  await deleteAssetApp(props.assetId, app.id)
  ElMessage.success(t('components.appService.table.deleteSuccess'))
  loadApps()
}

async function handleExport() {
  const blob = await exportAssetAppsCsv(props.assetId)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `asset_${props.assetId}_apps.csv`
  a.click()
  URL.revokeObjectURL(url)
}

function handleDialogSuccess() {
  dialogVisible.value = false
  loadApps()
  emit('portsChanged')
}

function sourceLabel(source: string): string {
  return source === 'scan' ? t('components.appService.table.sourceLabels.scan') : t('components.appService.table.sourceLabels.manual')
}

onMounted(loadApps)
</script>

<template>
  <div class="app-service-table">
    <div class="app-toolbar">
      <el-button type="primary" size="small" @click="handleCreate">
        <el-icon><Plus /></el-icon>
        {{ t('components.appService.table.addApp') }}
      </el-button>
      <el-button size="small" @click="handleExport" :disabled="apps.length === 0">
        <el-icon><Download /></el-icon>
        {{ t('common.export') }}
      </el-button>
    </div>

    <el-table v-loading="loading" :data="apps" stripe style="width: 100%">
      <el-table-column prop="name" :label="t('components.appService.table.name')" width="140">
        <template #default="{ row }">
          <span style="font-weight: 600; color: var(--neutral-900)">{{ row.name }}</span>
        </template>
      </el-table-column>

      <el-table-column prop="version" :label="t('components.appService.table.version')" width="110">
        <template #default="{ row }">
          <span class="ui-mono">{{ row.version || '-' }}</span>
        </template>
      </el-table-column>

      <el-table-column prop="category" :label="t('components.appService.table.category')" width="160" show-overflow-tooltip>
        <template #default="{ row }">
          <span>{{ getCategoryLabel(row.category) }}</span>
        </template>
      </el-table-column>

      <el-table-column prop="port" :label="t('components.appService.table.port')" width="90">
        <template #default="{ row }">
          <span v-if="row.port" class="ui-mono">{{ row.port }}/{{ row.protocol || 'tcp' }}</span>
          <span v-else class="ui-mono-muted">-</span>
        </template>
      </el-table-column>

      <el-table-column prop="source" :label="t('components.appService.table.source')" width="80">
        <template #default="{ row }">
          <el-tag size="small" :type="row.source === 'scan' ? 'success' : 'info'" effect="plain">
            {{ sourceLabel(row.source) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="notes" :label="t('components.appService.dialog.notes')" show-overflow-tooltip />

      <el-table-column :label="t('components.appService.table.actions')" width="120" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="handleEdit(row)">{{ t('components.appService.table.edit') }}</el-button>
          <el-button link type="danger" size="small" @click="handleDelete(row)">{{ t('components.appService.table.delete') }}</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div v-if="apps.length === 0 && !loading" class="app-empty">
      <p>{{ t('components.appService.table.empty') }}</p>
      <el-button type="primary" size="small" @click="handleCreate">{{ t('components.appService.table.addApp') }}</el-button>
    </div>

    <AppServiceDialog
      v-model:visible="dialogVisible"
      :asset-id="props.assetId"
      :editing="editingApp"
      @success="handleDialogSuccess"
    />
  </div>
</template>

<style scoped>
.app-toolbar {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}
.app-empty {
  text-align: center;
  padding: var(--space-8) 0;
  color: var(--neutral-400);
}
.app-empty p {
  margin-bottom: var(--space-3);
}
</style>
