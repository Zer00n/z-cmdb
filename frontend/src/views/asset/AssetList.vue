<script setup lang="ts">
/**
 * 资产列表页
 * 基于 Claude Design 04-asset-list.html 实现
 */
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchAssetList, decommissionAsset, exportAssetsCsv, updateAsset } from '@/api/asset'
import type { AssetListItem, AssetListResponse, AssetQueryParams } from '@/types/asset'

const router = useRouter()

// 数据
const loading = ref(false)
const tableData = ref<AssetListItem[]>([])
const total = ref(0)
const totalPages = ref(0)

// 查询参数
const query = reactive<AssetQueryParams>({
  page: 1,
  page_size: 20,
  search: '',
  asset_type: undefined,
  network_zone: undefined,
  importance: undefined,
  status: undefined,
  business_system: undefined,
  owner: undefined,
})

// 加载数据
async function loadData() {
  loading.value = true
  try {
    const params: AssetQueryParams = { ...query }
    // 清除空字符串
    Object.keys(params).forEach((key) => {
      const k = key as keyof AssetQueryParams
      if (params[k] === '' || params[k] === undefined) {
        delete params[k]
      }
    })
    const res: AssetListResponse = await fetchAssetList(params)
    tableData.value = res.items
    total.value = res.total
    totalPages.value = res.total_pages
  } finally {
    loading.value = false
  }
}

// 搜索
function handleSearch() {
  query.page = 1
  loadData()
}

// 重置筛选
function handleReset() {
  query.search = ''
  query.asset_type = undefined
  query.network_zone = undefined
  query.importance = undefined
  query.status = undefined
  query.page = 1
  loadData()
}

// 分页
function handlePageChange(page: number) {
  query.page = page
  loadData()
}

function handleSizeChange(size: number) {
  query.page_size = size
  query.page = 1
  loadData()
}

// 跳转详情
function goDetail(id: number) {
  router.push(`/assets/${id}`)
}

// 跳转新增
function goCreate() {
  router.push('/assets/create')
}

// 下线资产
async function handleDecommission(row: AssetListItem) {
  await ElMessageBox.confirm(
    `确认将资产 ${row.asset_no}（${row.ip_address}）标记为下线？`,
    '下线确认',
    { confirmButtonText: '确认下线', cancelButtonText: '取消', type: 'warning' }
  )
  await decommissionAsset(row.id)
  ElMessage.success('资产已下线')
  loadData()
}

// 恢复上线
async function handleRestore(row: AssetListItem) {
  await ElMessageBox.confirm(
    `确认将资产 ${row.asset_no}（${row.ip_address}）恢复为在线？`,
    '恢复上线',
    { confirmButtonText: '确认恢复', cancelButtonText: '取消', type: 'info' }
  )
  await updateAsset(row.id, { status: 'online' })
  ElMessage.success('资产已恢复上线')
  loadData()
}

// 导出 CSV
async function handleExport() {
  const blob = await exportAssetsCsv(query)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'assets.csv'
  a.click()
  URL.revokeObjectURL(url)
}

// 网络区域标签样式
function zoneClass(zone: string): string {
  const map: Record<string, string> = {
    intranet: 'zone-intranet',
    dmz: 'zone-dmz',
    office: 'zone-office',
    management: 'zone-mgmt',
    other: '',
  }
  return map[zone] || ''
}

// 网络区域中文
function zoneLabel(zone: string): string {
  const map: Record<string, string> = {
    intranet: '内网',
    dmz: 'DMZ',
    office: '办公网',
    management: '管理网',
    other: '其他',
  }
  return map[zone] || zone
}

// 重要性中文
function importanceLabel(imp: string): string {
  const map: Record<string, string> = { core: '核心', important: '重要', normal: '普通' }
  return map[imp] || imp
}

// 状态中文
function statusLabel(s: string): string {
  const map: Record<string, string> = { online: '在线', offline: '离线', decommissioned: '已下线' }
  return map[s] || s
}

// 资产类型中文
function typeLabel(t: string): string {
  const map: Record<string, string> = {
    physical: '物理服务器',
    virtual: '虚拟机',
    network_device: '网络设备',
    other: '其他',
  }
  return map[t] || t
}

onMounted(loadData)
</script>

<template>
  <div class="asset-list-page">
    <!-- 页头 -->
    <div class="page-head">
      <div>
        <h1>
          资产列表
          <span class="count">共 <b>{{ total }}</b> 项</span>
        </h1>
      </div>
      <div class="actions">
        <el-button @click="handleExport">
          <el-icon><Download /></el-icon>
          导出 CSV
        </el-button>
        <el-button type="primary" @click="goCreate">
          <el-icon><Plus /></el-icon>
          新增资产
        </el-button>
      </div>
    </div>

    <!-- 筛选区 -->
    <div class="filter-card">
      <div class="filter-row">
        <el-input
          v-model="query.search"
          placeholder="搜索 IP / 主机名 / 资产编号 / 备注"
          clearable
          style="width: 320px"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <el-select v-model="query.network_zone" placeholder="网络区域" clearable @change="handleSearch" style="width: 140px">
          <el-option label="内网" value="intranet" />
          <el-option label="DMZ" value="dmz" />
          <el-option label="办公网" value="office" />
          <el-option label="管理网" value="management" />
          <el-option label="其他" value="other" />
        </el-select>

        <el-select v-model="query.asset_type" placeholder="资产类型" clearable @change="handleSearch" style="width: 140px">
          <el-option label="物理服务器" value="physical" />
          <el-option label="虚拟机" value="virtual" />
          <el-option label="网络设备" value="network_device" />
          <el-option label="其他" value="other" />
        </el-select>

        <el-select v-model="query.importance" placeholder="重要性" clearable @change="handleSearch" style="width: 120px">
          <el-option label="核心" value="core" />
          <el-option label="重要" value="important" />
          <el-option label="普通" value="normal" />
        </el-select>

        <el-select v-model="query.status" placeholder="状态" clearable @change="handleSearch" style="width: 120px">
          <el-option label="在线" value="online" />
          <el-option label="离线" value="offline" />
          <el-option label="已下线" value="decommissioned" />
        </el-select>

        <el-button @click="handleReset">重置</el-button>
      </div>
    </div>

    <!-- 表格 -->
    <div class="table-card">
      <el-table
        v-loading="loading"
        :data="tableData"
        stripe
        highlight-current-row
        style="width: 100%"
        :header-cell-style="{ background: '#F4F7FB', color: 'var(--neutral-700)', fontWeight: 600, fontSize: '13px' }"
        :row-style="{ cursor: 'pointer' }"
        @row-click="(row: AssetListItem) => goDetail(row.id)"
      >
        <el-table-column prop="asset_no" label="资产编号" width="150">
          <template #default="{ row }">
            <span class="id-link">{{ row.asset_no }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="ip_address" label="IP 地址" width="140">
          <template #default="{ row }">
            <span class="mono">{{ row.ip_address }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="hostname" label="主机名" width="160" show-overflow-tooltip />

        <el-table-column prop="asset_type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ typeLabel(row.asset_type) }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="network_zone" label="区域" width="100">
          <template #default="{ row }">
            <span class="zone-tag" :class="zoneClass(row.network_zone)">
              <span class="zone-dot" />
              {{ zoneLabel(row.network_zone) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="business_system" label="业务系统" width="130" show-overflow-tooltip />

        <el-table-column prop="importance" label="重要性" width="90">
          <template #default="{ row }">
            <span class="imp" :class="row.importance">{{ importanceLabel(row.importance) }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <span class="status-cell" :class="row.status">
              <span class="status-dot" />
              {{ statusLabel(row.status) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="owner" label="负责人" width="90" />

        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click.stop="router.push(`/assets/${row.id}/edit`)">
              编辑
            </el-button>
            <el-button
              v-if="row.status !== 'decommissioned' && row.status !== 'offline'"
              link
              type="danger"
              size="small"
              @click.stop="handleDecommission(row)"
            >
              下线
            </el-button>
            <el-button
              v-if="row.status === 'decommissioned' || row.status === 'offline'"
              link
              type="success"
              size="small"
              @click.stop="handleRestore(row)"
            >
              恢复上线
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-bar">
        <span class="total-info">共 {{ total }} 条</span>
        <el-pagination
          v-model:current-page="query.page"
          v-model:page-size="query.page_size"
          :total="total"
          :page-sizes="[20, 50, 100]"
          layout="sizes, prev, pager, next, jumper"
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.asset-list-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

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
.page-head .count {
  font-size: 13px;
  font-weight: 400;
  color: var(--neutral-500);
  font-family: var(--font-mono);
}
.page-head .count b {
  color: var(--neutral-900);
  font-weight: 600;
}
.actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

/* 筛选区 */
.filter-card {
  background: var(--neutral-0);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
}
.filter-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}

/* 表格卡片 */
.table-card {
  background: var(--neutral-0);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

/* 单元格样式 */
.id-link {
  color: var(--color-primary-500);
  font-family: var(--font-mono);
  font-size: 13px;
  cursor: pointer;
}
.id-link:hover {
  color: var(--color-primary-700);
  text-decoration: underline;
}

.mono {
  font-family: var(--font-mono);
  color: var(--neutral-900);
  font-size: 13px;
}

/* 区域标签 */
.zone-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  line-height: 18px;
  padding: 1px 8px;
  border-radius: var(--radius-sm);
  white-space: nowrap;
}
.zone-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
.zone-intranet { background: #DBE5FE; color: #1E40AF; }
.zone-dmz      { background: #FEF3C7; color: #92400E; }
.zone-office   { background: #CFFAFE; color: #0E7490; }
.zone-mgmt     { background: #EDE9FE; color: #5B21B6; }

/* 重要性 */
.imp { font-size: 13px; }
.imp.core { color: var(--color-danger); font-weight: 500; }
.imp.important { color: var(--color-warning); }
.imp.normal { color: var(--neutral-500); }

/* 状态 */
.status-cell {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--neutral-700);
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.status-cell.online .status-dot {
  background: var(--status-online);
  box-shadow: 0 0 0 3px rgba(22, 163, 74, 0.16);
}
.status-cell.offline .status-dot { background: var(--status-offline); }
.status-cell.decommissioned .status-dot { background: var(--status-decommissioned); }

/* 分页 */
.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  border-top: 1px solid var(--neutral-200);
}
.total-info {
  font-size: 13px;
  color: var(--neutral-500);
}
</style>
