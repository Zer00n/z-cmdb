<script setup lang="ts">
/**
 * 审计日志页
 * 2026 UI Redesign：升级 notice、动作徽标、视觉，业务逻辑保持不变
 */
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchAuditLogs, exportAuditReport } from '@/api/audit'
import type { AuditLog, AuditQueryParams } from '@/types/audit'
import dayjs from 'dayjs'

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
  ElMessage.success('审计报告已导出')
}

function formatTime(t: string): string {
  return dayjs(t).format('YYYY-MM-DD HH:mm:ss')
}

function actionLabel(action: string): string {
  const map: Record<string, string> = {
    LOGIN: '登录',
    CREATE: '创建',
    UPDATE: '更新',
    DELETE: '删除',
    EXPORT: '导出',
    LLM_CALL: 'LLM 调用',
    CONFIG: '配置变更',
  }
  return map[action] || action
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
  const map: Record<string, string> = {
    super_admin: '超管',
    admin: '管理员',
    auditor: '审计员',
  }
  return map[r] || r
}

onMounted(loadData)
</script>

<template>
  <div class="ui-page">
    <!-- 不可变提示 -->
    <div class="ui-notice">
      <el-icon size="14" color="var(--color-primary-600)"><Lock /></el-icon>
      <span>审计日志<b>不可修改、不可删除</b>，所有操作均已永久记录 · 数据库层面已启用触发器保护</span>
    </div>

    <!-- 页头 -->
    <div class="ui-page-head">
      <div>
        <h1 class="ui-page-title">
          操作审计日志
          <span class="ui-page-count">共 <b>{{ total }}</b> 条</span>
        </h1>
        <p class="ui-page-subtitle">来源 IP、User-Agent、操作前后状态均完整记录</p>
      </div>
      <div class="ui-page-actions">
        <el-button type="primary" @click="handleExport">
          <el-icon><Download /></el-icon>
          导出审计报告
        </el-button>
      </div>
    </div>

    <!-- 筛选 -->
    <div class="ui-filter-bar">
      <el-select v-model="query.action_type" placeholder="操作类型" clearable @change="handleSearch" style="width: 150px">
        <el-option label="登录" value="LOGIN" />
        <el-option label="创建" value="CREATE" />
        <el-option label="更新" value="UPDATE" />
        <el-option label="删除" value="DELETE" />
        <el-option label="导出" value="EXPORT" />
        <el-option label="LLM 调用" value="LLM_CALL" />
        <el-option label="配置变更" value="CONFIG" />
      </el-select>

      <el-select v-model="query.target_type" placeholder="目标类型" clearable @change="handleSearch" style="width: 150px">
        <el-option label="资产" value="asset" />
        <el-option label="用户" value="user" />
        <el-option label="扫描批次" value="scan_batch" />
        <el-option label="拓扑图" value="topology" />
        <el-option label="系统配置" value="system_config" />
        <el-option label="审计报告" value="audit_report" />
      </el-select>

      <el-button @click="query.action_type = undefined; query.target_type = undefined; handleSearch()">
        <el-icon><Refresh /></el-icon>
        重置
      </el-button>
    </div>

    <!-- 表格 -->
    <div class="ui-table-card">
      <el-table v-loading="loading" :data="tableData" stripe style="width: 100%">
        <el-table-column prop="timestamp" label="时间" width="180">
          <template #default="{ row }">
            <span class="ui-mono ui-mono-muted" style="font-size: 12px">{{ formatTime(row.timestamp) }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="username" label="操作人" width="110">
          <template #default="{ row }">
            <span style="font-weight: 500">{{ row.username || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="user_role" label="角色" width="120">
          <template #default="{ row }">
            <span v-if="row.user_role" class="ui-badge is-neutral">{{ roleLabel(row.user_role) }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="action_type" label="操作" width="120">
          <template #default="{ row }">
            <span class="ui-badge" :class="actionClass(row.action_type)">
              <span class="ui-badge-dot" />
              {{ actionLabel(row.action_type) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="target_type" label="目标" width="110">
          <template #default="{ row }">
            <span class="ui-mono">{{ row.target_type || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="target_id" label="目标 ID" width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="ui-mono ui-mono-muted">{{ row.target_id || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="ip_address" label="来源 IP" width="140">
          <template #default="{ row }">
            <span class="ui-mono">{{ row.ip_address || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="result" label="结果" width="90">
          <template #default="{ row }">
            <span class="ui-badge" :class="row.result === 'success' ? 'is-success' : 'is-danger'">
              <span class="ui-badge-dot" />
              {{ row.result === 'success' ? '成功' : '失败' }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="details" label="详情" show-overflow-tooltip>
          <template #default="{ row }">
            <span style="color: var(--neutral-500); font-size: 12.5px">{{ row.details || '-' }}</span>
          </template>
        </el-table-column>
      </el-table>

      <div class="ui-pagination-bar">
        <span class="ui-pagination-info">共 {{ total }} 条</span>
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
/* 仅依赖 ui-* 工具类，无组件特定样式 */
</style>
