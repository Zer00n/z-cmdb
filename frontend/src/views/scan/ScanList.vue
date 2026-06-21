<script setup lang="ts">
/**
 * 扫描批次列表页
 * 2026 UI Redesign：升级页头、状态徽标，逻辑保持不变
 */
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchScanBatches, uploadScan, rejectBatch } from '@/api/scan'
import type { ScanBatch } from '@/types/scan'
import { useTimeFormat } from '@/composables/useTimeFormat'
import { useI18n } from 'vue-i18n'
import { useTranslatedLabels } from '@/composables/useTranslatedLabels'

const { t } = useI18n()
const { scanStatusLabel } = useTranslatedLabels()

const router = useRouter()
const loading = ref(false)
const tableData = ref<ScanBatch[]>([])
const total = ref(0)
const page = ref(1)
const uploading = ref(false)

async function loadData() {
  loading.value = true
  try {
    const res = await fetchScanBatches({ page: page.value, page_size: 20 })
    tableData.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

async function handleUpload(file: File) {
  uploading.value = true
  try {
    await uploadScan(file)
    ElMessage.success(t('scan.list.uploadSuccess'))
    loadData()
  } finally {
    uploading.value = false
  }
  return false
}

function goConfirm(row: ScanBatch) {
  router.push(`/scans/${row.id}/confirm`)
}

async function handleReject(row: ScanBatch) {
  await ElMessageBox.confirm(
    t('scan.list.rejectConfirm', { name: row.batch_name }),
    t('scan.list.rejectTitle'),
    { confirmButtonText: t('scan.list.rejectBtn'), cancelButtonText: t('common.cancel'), type: 'warning' }
  )
  await rejectBatch(row.id)
  ElMessage.success(t('scan.list.rejectSuccess'))
  loadData()
}

function formatTime(t: string): string {
  return useTimeFormat().formatTime(t)
}

function statusBadgeClass(s: string): string {
  const map: Record<string, string> = {
    pending: 'is-warning',
    confirmed: 'is-success',
    rejected: 'is-neutral',
  }
  return map[s] || 'is-neutral'
}

const pendingCount = computed(() => tableData.value.filter((b) => b.status === 'pending').length)

onMounted(loadData)
</script>

<template>
  <div class="ui-page">
    <div class="ui-page-head">
      <div>
        <h1 class="ui-page-title">
          {{ t('scan.list.title') }}
          <span class="ui-page-count">{{ t('scan.list.total', { count: total }) }}</span>
        </h1>
        <p class="ui-page-subtitle">
          <span v-if="pendingCount > 0" style="color: var(--color-warning); font-weight: 500">
            {{ t('scan.list.pendingWarning', { count: pendingCount }) }}
          </span>
          <span v-else>{{ t('scan.list.allProcessed') }}</span>
        </p>
      </div>
      <div class="ui-page-actions">
        <router-link to="/help" class="help-link">
          <el-icon><Document /></el-icon>
          {{ t('scan.list.nmapGuide') }}
        </router-link>
        <el-upload
          :show-file-list="false"
          accept=".xml"
          :before-upload="handleUpload"
          :disabled="uploading"
        >
          <el-button type="primary" :loading="uploading">
            <el-icon><Upload /></el-icon>
            {{ t('scan.list.uploadNmap') }}
          </el-button>
        </el-upload>
      </div>
    </div>

    <div class="ui-table-card">
      <el-table v-loading="loading" :data="tableData" stripe style="width: 100%">
        <el-table-column prop="id" :label="t('scan.list.columns.id')" width="70">
          <template #default="{ row }">
            <span class="ui-mono ui-mono-muted">#{{ row.id }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="batch_name" :label="t('scan.list.columns.filename')" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">
            <span style="color: var(--neutral-900); font-weight: 500">{{ row.batch_name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="uploaded_at" :label="t('scan.list.columns.uploadTime')" width="160">
          <template #default="{ row }">
            <span class="ui-mono ui-mono-muted">{{ formatTime(row.uploaded_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="total_hosts" :label="t('scan.list.columns.hosts')" width="90" align="center">
          <template #default="{ row }">
            <span class="num-cell">{{ row.total_hosts }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="new_count" :label="t('scan.list.columns.new')" width="90" align="center">
          <template #default="{ row }">
            <span v-if="row.new_count > 0" class="num-cell num-blue">+{{ row.new_count }}</span>
            <span v-else class="num-cell ui-mono-muted">0</span>
          </template>
        </el-table-column>
        <el-table-column prop="changed_count" :label="t('scan.list.columns.changed')" width="90" align="center">
          <template #default="{ row }">
            <span v-if="row.changed_count > 0" class="num-cell num-warning">~{{ row.changed_count }}</span>
            <span v-else class="num-cell ui-mono-muted">0</span>
          </template>
        </el-table-column>
        <el-table-column prop="missing_count" :label="t('scan.list.columns.missing')" width="90" align="center">
          <template #default="{ row }">
            <span v-if="row.missing_count > 0" class="num-cell num-muted">−{{ row.missing_count }}</span>
            <span v-else class="num-cell ui-mono-muted">0</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" :label="t('scan.list.columns.status')" width="120">
          <template #default="{ row }">
            <span class="ui-badge" :class="statusBadgeClass(row.status)">
              <span class="ui-badge-dot" />
              {{ scanStatusLabel(row.status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="file_size_bytes" :label="t('scan.list.columns.size')" width="100">
          <template #default="{ row }">
            <span class="ui-mono ui-mono-muted">
              {{ row.file_size_bytes ? (row.file_size_bytes / 1024).toFixed(0) + ' KB' : '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column :label="t('scan.list.columns.actions')" width="200" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === 'pending'" link type="primary" size="small" @click="goConfirm(row)">
              {{ t('scan.list.confirmImport') }}
            </el-button>
            <el-button v-if="row.status === 'pending'" link type="danger" size="small" @click="handleReject(row)">
              {{ t('scan.list.reject') }}
            </el-button>
            <el-button v-if="row.status !== 'pending'" link size="small" @click="goConfirm(row)">
              {{ t('scan.list.viewDetail') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="ui-pagination-bar">
        <span class="ui-pagination-info">{{ t('scan.list.pagination', { total: total }) }}</span>
        <el-pagination
          v-model:current-page="page"
          :total="total"
          :page-size="20"
          layout="prev, pager, next"
          @current-change="loadData"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.help-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--color-primary-600);
  text-decoration: none;
  padding: 6px 12px;
  border-radius: var(--radius-md);
  transition: background-color var(--dur-fast) var(--ease-out),
              color var(--dur-fast) var(--ease-out);
}
.help-link:hover {
  color: var(--color-primary-700);
  background: var(--color-primary-50);
}

.num-cell {
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 600;
  color: var(--neutral-700);
}
.num-blue { color: var(--color-primary-500); }
.num-warning { color: var(--color-warning); }
.num-muted { color: var(--neutral-500); }
</style>
