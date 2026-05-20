<script setup lang="ts">
/**
 * 资产列表页
 * 2026 UI Redesign：升级筛选区与表格视觉，业务逻辑保持不变
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

async function loadData() {
  loading.value = true
  try {
    const params: AssetQueryParams = { ...query }
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

function handleSearch() {
  query.page = 1
  loadData()
}

function handleReset() {
  query.search = ''
  query.asset_type = undefined
  query.network_zone = undefined
  query.importance = undefined
  query.status = undefined
  query.page = 1
  loadData()
}

function handlePageChange(page: number) {
  query.page = page
  loadData()
}

function handleSizeChange(size: number) {
  query.page_size = size
  query.page = 1
  loadData()
}

function goDetail(id: number) {
  router.push(`/assets/${id}`)
}

function goCreate() {
  router.push('/assets/create')
}

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

async function handleExport() {
  const blob = await exportAssetsCsv(query)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'assets.csv'
  a.click()
  URL.revokeObjectURL(url)
}

function zoneClass(zone: string): string {
  const map: Record<string, string> = {
    intranet: 'zone-intranet',
    dmz: 'zone-dmz',
    office: 'zone-office',
    management: 'zone-mgmt',
    other: 'zone-other',
  }
  return map[zone] || 'zone-other'
}

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

function importanceLabel(imp: string): string {
  const map: Record<string, string> = { core: '核心', important: '重要', normal: '普通' }
  return map[imp] || imp
}

function statusLabel(s: string): string {
  const map: Record<string, string> = { online: '在线', offline: '离线', decommissioned: '已下线' }
  return map[s] || s
}

function typeLabel(t: string): string {
  const map: Record<string, string> = {
    physical: '物理服务器',
    virtual: '虚拟机',
    network_device: '网络设备',
    other: '其他',
  }
  return map[t] || t
}

// 派生统计：在线/离线计数（用于页头）
const onlineCount = computed(() =>
  tableData.value.filter((a) => a.status === 'online').length
)

onMounted(loadData)
</script>

<template>
  <div class="ui-page">
    <!-- 页头 -->
    <div class="ui-page-head">
      <div>
        <h1 class="ui-page-title">
          资产列表
          <span class="ui-page-count">共 <b>{{ total }}</b> 项</span>
        </h1>
        <p class="ui-page-subtitle">本页 {{ tableData.length }} 项 · 在线 {{ onlineCount }} 项</p>
      </div>
      <div class="ui-page-actions">
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
    <div class="ui-filter-bar">
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

      <el-button @click="handleReset">
        <el-icon><Refresh /></el-icon>
        重置
      </el-button>
    </div>

    <!-- 表格 -->
    <div class="ui-table-card">
      <el-table
        v-loading="loading"
        :data="tableData"
        stripe
        highlight-current-row
        style="width: 100%"
        :row-style="{ cursor: 'pointer' }"
        @row-click="(row: AssetListItem) => goDetail(row.id)"
      >
        <el-table-column prop="asset_no" label="资产编号" width="160">
          <template #default="{ row }">
            <span class="ui-id-link">{{ row.asset_no }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="ip_address" label="IP 地址" width="140">
          <template #default="{ row }">
            <span class="ui-mono">{{ row.ip_address }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="hostname" label="主机名" width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span style="color: var(--neutral-700)">{{ row.hostname || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="asset_type" label="类型" width="110">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ typeLabel(row.asset_type) }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="network_zone" label="区域" width="110">
          <template #default="{ row }">
            <span class="ui-zone" :class="zoneClass(row.network_zone)">
              {{ zoneLabel(row.network_zone) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="business_system" label="业务系统" width="140" show-overflow-tooltip />

        <el-table-column prop="importance" label="重要性" width="100">
          <template #default="{ row }">
            <span class="ui-imp" :class="'is-' + row.importance">{{ importanceLabel(row.importance) }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="110">
          <template #default="{ row }">
            <span class="ui-status" :class="'is-' + row.status">
              {{ statusLabel(row.status) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="owner" label="负责人" width="100" />

        <el-table-column label="操作" width="160" fixed="right">
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

      <div class="ui-pagination-bar">
        <span class="ui-pagination-info">共 {{ total }} 条 · 第 {{ query.page }} / {{ totalPages }} 页</span>
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
/* 表格行 hover 时让 ID 链接更亮 */
:deep(.el-table__row:hover) .ui-id-link {
  color: var(--color-primary-700);
}
</style>
