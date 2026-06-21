<script setup lang="ts">
/**
 * Audit log page
 * 2026 UI Redesign: upgraded notice, action badges, visuals, business logic unchanged
 */
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { fetchAuditLogs, exportAuditReport } from '@/api/audit'
import type { AuditLog, AuditQueryParams } from '@/types/audit'
import { useTimeFormat } from '@/composables/useTimeFormat'

const { t } = useI18n()
const loading = ref(false)
const tableData = ref<AuditLog[]>([])
const total = ref(0)

const query = reactive<AuditQueryParams>({
  page: 1,
  page_size: 50,
  action_type: undefined,
  target_type: undefined,
})

async function loadData() {
  loading.value = true
  try {
    const params = { ...query }
    Object.keys(params).forEach((k) => {
      if (params[k as keyof AuditQueryParams] === '' || params[k as keyof AuditQueryParams] === undefined) {
        delete params[k as keyof AuditQueryParams]
      }
    })
    const res = await fetchAuditLogs(params)
    tableData.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  query.page = 1
  loadData()
}

function handlePageChange(page: number) {
  query.page = page
  loadData()
}

async function handleExport() {
  const blob = await exportAuditReport()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'audit_report.csv'
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success(t('audit.exportSuccess'))
}

function formatTime(t: string): string {
  return useTimeFormat().formatTime(t, 'YYYY-MM-DD HH:mm:ss')
}

function actionLabel(action: string): string {
  if (!action) return action || ''
  const key = `audit.actions.${action}`
  return t(key) !== key ? t(key) : action
}

function actionClass(action: string): string {
  const map: Record<string, string> = {
    LOGIN: 'is-info',
    CREATE: 'is-success',
    UPDATE: 'is-warning',
    DELETE: 'is-danger',
    EXPORT: 'is-info',
    LLM_CALL: 'is-info',
    CONFIG: 'is-warning',
  }
  return map[action] || 'is-neutral'
}

function roleLabel(r: string): string {
  if (!r) return r || ''
  const key = `audit.roles.${r}`
  return t(key) !== key ? t(key) : r
}

onMounted(loadData)
</script>

<template>
  <div class="ui-page">
    <!-- Immutable notice -->
    <div class="ui-notice">
      <el-icon size="14" color="var(--color-primary-600)"><Lock /></el-icon>
      <span v-html="t('audit.notice')"></span>
    </div>

    <!-- Page header -->
    <div class="ui-page-head">
      <div>
        <h1 class="ui-page-title">
          {{ t('audit.title') }}
          <span class="ui-page-count">{{ t('audit.total', { count: total }) }}</span>
        </h1>
        <p class="ui-page-subtitle">{{ t('audit.subtitle') }}</p>
      </div>
      <div class="ui-page-actions">
        <el-button type="primary" @click="handleExport">
          <el-icon><Download /></el-icon>
          {{ t('audit.exportBtn') }}
        </el-button>
      </div>
    </div>

    <!-- Filters -->
    <div class="ui-filter-bar">
      <el-select v-model="query.action_type" :placeholder="t('audit.filters.action')" clearable @change="handleSearch" style="width: 150px">
        <el-option :label="t('audit.actions.LOGIN')" value="LOGIN" />
        <el-option :label="t('audit.actions.CREATE')" value="CREATE" />
        <el-option :label="t('audit.actions.UPDATE')" value="UPDATE" />
        <el-option :label="t('audit.actions.DELETE')" value="DELETE" />
        <el-option :label="t('audit.actions.EXPORT')" value="EXPORT" />
        <el-option :label="t('audit.actions.LLM_CALL')" value="LLM_CALL" />
        <el-option :label="t('audit.actions.CONFIG')" value="CONFIG" />
      </el-select>

      <el-select v-model="query.target_type" :placeholder="t('audit.filters.targetType')" clearable @change="handleSearch" style="width: 150px">
        <el-option :label="t('audit.targetTypes.asset')" value="asset" />
        <el-option :label="t('audit.targetTypes.user')" value="user" />
        <el-option :label="t('audit.targetTypes.scan_batch')" value="scan_batch" />
        <el-option :label="t('audit.targetTypes.topology')" value="topology" />
        <el-option :label="t('audit.targetTypes.system_config')" value="system_config" />
        <el-option :label="t('audit.targetTypes.audit_report')" value="audit_report" />
      </el-select>

      <el-button @click="query.action_type = undefined; query.target_type = undefined; handleSearch()">
        <el-icon><Refresh /></el-icon>
        {{ t('audit.reset') }}
      </el-button>
    </div>

    <!-- Table -->
    <div class="ui-table-card">
      <el-table v-loading="loading" :data="tableData" stripe style="width: 100%">
        <el-table-column prop="timestamp" :label="t('audit.columns.time')" width="180">
          <template #default="{ row }">
            <span class="ui-mono ui-mono-muted" style="font-size: 12px">{{ formatTime(row.timestamp) }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="username" :label="t('audit.columns.user')" width="110">
          <template #default="{ row }">
            <span style="font-weight: 500">{{ row.username || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="user_role" :label="t('audit.columns.role')" width="120">
          <template #default="{ row }">
            <span v-if="row.user_role" class="ui-badge is-neutral">{{ roleLabel(row.user_role) }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="action_type" :label="t('audit.columns.action')" width="120">
          <template #default="{ row }">
            <span class="ui-badge" :class="actionClass(row.action_type)">
              <span class="ui-badge-dot" />
              {{ actionLabel(row.action_type) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="target_type" :label="t('audit.columns.targetType')" width="110">
          <template #default="{ row }">
            <span class="ui-mono">{{ row.target_type || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="target_id" :label="t('audit.columns.targetId')" width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="ui-mono ui-mono-muted">{{ row.target_id || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="ip_address" :label="t('audit.columns.ip')" width="140">
          <template #default="{ row }">
            <span class="ui-mono">{{ row.ip_address || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="result" :label="t('audit.columns.result')" width="90">
          <template #default="{ row }">
            <span class="ui-badge" :class="row.result === 'success' ? 'is-success' : 'is-danger'">
              <span class="ui-badge-dot" />
              {{ row.result === 'success' ? t('audit.resultSuccess') : t('audit.resultFail') }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="details" :label="t('audit.columns.detail')" show-overflow-tooltip>
          <template #default="{ row }">
            <span style="color: var(--neutral-500); font-size: 12.5px">{{ row.details || '-' }}</span>
          </template>
        </el-table-column>
      </el-table>

      <div class="ui-pagination-bar">
        <span class="ui-pagination-info">{{ t('audit.pagination', { total }) }}</span>
        <el-pagination
          v-model:current-page="query.page"
          :total="total"
          :page-size="query.page_size || 50"
          layout="prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Only uses ui-* utility classes, no component-specific styles */
</style>
