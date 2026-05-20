<script setup lang="ts">
/**
 * 审计日志页
 * 基于 Claude Design 10-audit-log.html 实现
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
    LLM_CALL: 'LLM调用',
    CONFIG: '配置变更',
  }
  return map[action] || action
}

function resultTag(result: string): string {
  return result === 'success' ? 'success' : 'danger'
}

onMounted(loadData)
</script>

<template>
  <div class="audit-page">
    <!-- 不可变提示 -->
    <div class="notice-bar">
      <el-icon size="14"><Lock /></el-icon>
      <span>审计日志<b>不可修改、不可删除</b>，所有操作均已永久记录</span>
    </div>

    <!-- 页头 -->
    <div class="page-head">
      <div>
        <h1>
          操作审计日志
          <span class="count">共 <b>{{ total }}</b> 条</span>
        </h1>
      </div>
      <div class="actions">
        <el-button type="primary" @click="handleExport">
          <el-icon><Download /></el-icon>
          导出审计报告
        </el-button>
      </div>
    </div>

    <!-- 筛选 -->
    <div class="filter-card">
      <div class="filter-row">
        <el-select v-model="query.action_type" placeholder="操作类型" clearable @change="handleSearch" style="width: 140px">
          <el-option label="登录" value="LOGIN" />
          <el-option label="创建" value="CREATE" />
          <el-option label="更新" value="UPDATE" />
          <el-option label="删除" value="DELETE" />
          <el-option label="导出" value="EXPORT" />
          <el-option label="LLM调用" value="LLM_CALL" />
          <el-option label="配置变更" value="CONFIG" />
        </el-select>

        <el-select v-model="query.target_type" placeholder="目标类型" clearable @change="handleSearch" style="width: 140px">
          <el-option label="资产" value="asset" />
          <el-option label="用户" value="user" />
          <el-option label="扫描批次" value="scan_batch" />
          <el-option label="拓扑图" value="topology" />
          <el-option label="系统配置" value="system_config" />
          <el-option label="审计报告" value="audit_report" />
        </el-select>

        <el-button @click="query.action_type = undefined; query.target_type = undefined; handleSearch()">重置</el-button>
      </div>
    </div>

    <!-- 表格 -->
    <div class="table-card">
      <el-table v-loading="loading" :data="tableData" stripe style="width: 100%">
        <el-table-column prop="timestamp" label="时间" width="170">
          <template #default="{ row }">
            <span class="mono" style="font-size: 12px">{{ formatTime(row.timestamp) }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="username" label="操作人" width="100" />

        <el-table-column prop="user_role" label="角色" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.user_role" size="small" effect="plain">{{ row.user_role }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="action_type" label="操作" width="100">
          <template #default="{ row }">
            <span>{{ actionLabel(row.action_type) }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="target_type" label="目标类型" width="100" />
        <el-table-column prop="target_id" label="目标ID" width="120" show-overflow-tooltip />

        <el-table-column prop="ip_address" label="来源IP" width="130">
          <template #default="{ row }">
            <span class="mono">{{ row.ip_address || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="result" label="结果" width="80">
          <template #default="{ row }">
            <el-tag :type="resultTag(row.result)" size="small">{{ row.result }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="details" label="详情" show-overflow-tooltip />
      </el-table>

      <div class="pagination-bar">
        <span class="total-info">共 {{ total }} 条</span>
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
.audit-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.notice-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: var(--space-2) var(--space-4);
  background: var(--neutral-100);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  font-size: var(--fs-caption);
  color: var(--neutral-700);
}
.notice-bar b { font-weight: 600; color: var(--neutral-900); }

.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
}
.page-head h1 {
  margin: 0;
  font-size: var(--fs-h2);
  line-height: var(--lh-h2);
  color: var(--neutral-900);
  font-weight: 600;
  display: inline-flex;
  align-items: baseline;
  gap: var(--space-3);
}
.count { font-size: 13px; font-weight: 400; color: var(--neutral-500); font-family: var(--font-mono); }
.count b { color: var(--neutral-900); font-weight: 600; }
.actions { display: flex; gap: var(--space-2); }

.filter-card {
  background: var(--neutral-0);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
}
.filter-row { display: flex; align-items: center; gap: var(--space-3); }

.table-card {
  background: var(--neutral-0);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.mono { font-family: var(--font-mono); font-size: 13px; }

.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  border-top: 1px solid var(--neutral-200);
}
.total-info { font-size: 13px; color: var(--neutral-500); }
</style>
