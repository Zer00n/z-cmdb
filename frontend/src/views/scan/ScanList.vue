<script setup lang="ts">
/**
 * 扫描批次列表页
 * 复用资产列表模板结构
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchScanBatches, uploadScan, rejectBatch } from '@/api/scan'
import type { ScanBatch } from '@/types/scan'
import dayjs from 'dayjs'

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
    ElMessage.success('扫描报告上传成功，请在列表中确认导入')
    loadData()
  } finally {
    uploading.value = false
  }
  return false // 阻止 el-upload 默认行为
}

function goConfirm(row: ScanBatch) {
  router.push(`/scans/${row.id}/confirm`)
}

async function handleReject(row: ScanBatch) {
  await ElMessageBox.confirm(
    `确认拒绝批次 "${row.batch_name}"？拒绝后数据不会入库。`,
    '拒绝批次',
    { confirmButtonText: '确认拒绝', cancelButtonText: '取消', type: 'warning' }
  )
  await rejectBatch(row.id)
  ElMessage.success('批次已拒绝')
  loadData()
}

function formatTime(t: string): string {
  return dayjs(t).format('YYYY-MM-DD HH:mm')
}

function statusLabel(s: string): string {
  const map: Record<string, string> = { pending: '待确认', confirmed: '已确认', rejected: '已拒绝' }
  return map[s] || s
}

function statusType(s: string): string {
  const map: Record<string, string> = { pending: 'warning', confirmed: 'success', rejected: 'info' }
  return map[s] || ''
}

onMounted(loadData)
</script>

<template>
  <div class="scan-list-page">
    <div class="page-head">
      <h1>扫描批次</h1>
      <div class="actions">
        <router-link to="/help" class="help-link">
          <el-icon><Document /></el-icon>
          nmap 扫描指南
        </router-link>
        <el-upload
          :show-file-list="false"
          accept=".xml"
          :before-upload="handleUpload"
          :disabled="uploading"
        >
          <el-button type="primary" :loading="uploading">
            <el-icon><Upload /></el-icon>
            上传 nmap XML
          </el-button>
        </el-upload>
      </div>
    </div>

    <div class="table-card">
      <el-table v-loading="loading" :data="tableData" stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="batch_name" label="文件名" width="250" show-overflow-tooltip />
        <el-table-column prop="uploaded_at" label="上传时间" width="160">
          <template #default="{ row }">
            <span class="mono">{{ formatTime(row.uploaded_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="total_hosts" label="主机数" width="80" />
        <el-table-column prop="new_count" label="新发现" width="80">
          <template #default="{ row }">
            <span v-if="row.new_count > 0" style="color: var(--color-primary-500); font-weight: 500">{{ row.new_count }}</span>
            <span v-else>0</span>
          </template>
        </el-table-column>
        <el-table-column prop="changed_count" label="变更" width="80">
          <template #default="{ row }">
            <span v-if="row.changed_count > 0" style="color: var(--color-warning); font-weight: 500">{{ row.changed_count }}</span>
            <span v-else>0</span>
          </template>
        </el-table-column>
        <el-table-column prop="missing_count" label="消失" width="80">
          <template #default="{ row }">
            <span v-if="row.missing_count > 0" style="color: var(--neutral-500)">{{ row.missing_count }}</span>
            <span v-else>0</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="file_size_bytes" label="文件大小" width="100">
          <template #default="{ row }">
            {{ row.file_size_bytes ? (row.file_size_bytes / 1024).toFixed(0) + ' KB' : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'pending'"
              link
              type="primary"
              size="small"
              @click="goConfirm(row)"
            >
              确认导入
            </el-button>
            <el-button
              v-if="row.status === 'pending'"
              link
              type="danger"
              size="small"
              @click="handleReject(row)"
            >
              拒绝
            </el-button>
            <el-button
              v-if="row.status !== 'pending'"
              link
              size="small"
              @click="goConfirm(row)"
            >
              查看详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-bar">
        <span class="total-info">共 {{ total }} 条</span>
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
.scan-list-page { display: flex; flex-direction: column; gap: var(--space-4); }
.page-head { display: flex; align-items: flex-end; justify-content: space-between; }
.page-head h1 { margin: 0; font-size: var(--fs-h2); color: var(--neutral-900); font-weight: 600; }
.actions { display: flex; gap: var(--space-2); align-items: center; }
.help-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--color-primary-500);
  text-decoration: none;
  padding: 0 var(--space-2);
}
.help-link:hover { color: var(--color-primary-700); text-decoration: underline; }
.table-card { background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: var(--radius-lg); overflow: hidden; }
.mono { font-family: var(--font-mono); font-size: 12px; }
.pagination-bar { display: flex; align-items: center; justify-content: space-between; padding: var(--space-3) var(--space-4); border-top: 1px solid var(--neutral-200); }
.total-info { font-size: 13px; color: var(--neutral-500); }
</style>
