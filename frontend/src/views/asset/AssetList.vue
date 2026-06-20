<script setup lang="ts">
/**
 * 资产列表页
 * 2026 UI Redesign：升级筛选区与表格视觉，业务逻辑保持不变
 */
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchAssetList, decommissionAsset, exportAssetsCsv, exportAssetsForThreatHunting, updateAsset } from '@/api/asset'
import type { AssetListItem, AssetListResponse, AssetQueryParams } from '@/types/asset'
import { useTranslatedLabels } from '@/composables/useTranslatedLabels'

const router = useRouter()
const { t } = useI18n()
const { zoneLabel, importanceLabel, statusLabel, typeLabel } = useTranslatedLabels()

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
    t('asset.list.decommissionConfirm', { no: row.asset_no, ip: row.ip_address }),
    t('asset.list.decommissionTitle'),
    { confirmButtonText: t('asset.list.decommissionBtn'), cancelButtonText: t('common.cancel'), type: 'warning' }
  )
  await decommissionAsset(row.id)
  ElMessage.success(t('asset.list.decommissionSuccess'))
  loadData()
}

async function handleRestore(row: AssetListItem) {
  await ElMessageBox.confirm(
    t('asset.list.restoreConfirm', { no: row.asset_no, ip: row.ip_address }),
    t('asset.list.restoreTitle'),
    { confirmButtonText: t('asset.list.restoreBtn'), cancelButtonText: t('common.cancel'), type: 'info' }
  )
  await updateAsset(row.id, { status: 'online' })
  ElMessage.success(t('asset.list.restoreSuccess'))
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

async function handleExportThreatHunting() {
  const blob = await exportAssetsForThreatHunting(query)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  const today = new Date().toISOString().slice(0, 10).replace(/-/g, '')
  a.download = `cmdb_threat_hunting_${today}.csv`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success(t('asset.list.exportThreatHuntingSuccess'))
}

function handleExportCommand(command: string) {
  if (command === 'standard') {
    handleExport()
  } else if (command === 'threat-hunting') {
    handleExportThreatHunting()
  }
}

function zoneClass(zone: string): string {
  const map: Record<string, string> = {
    intranet: 'zone-intranet',
    dmz: 'zone-dmz',
    office: 'zone-office',
    management: 'zone-mgmt',
    other: 'zone-other',
    aliyun: 'zone-cloud',
    tencent: 'zone-cloud',
    huawei: 'zone-cloud',
    aws: 'zone-cloud',
    azure: 'zone-cloud',
    gcp: 'zone-cloud',
    other_cloud: 'zone-cloud',
  }
  return map[zone] || 'zone-other'
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
          {{ t('asset.list.title') }}
          <span class="ui-page-count">{{ t('asset.list.total', { count: total }) }}</span>
        </h1>
        <p class="ui-page-subtitle">{{ t('asset.list.pageSummary', { pageItems: tableData.length, onlineCount: onlineCount }) }}</p>
      </div>
      <div class="ui-page-actions">
        <el-dropdown trigger="click" @command="handleExportCommand">
          <el-button>
            <el-icon><Download /></el-icon>
            {{ t('asset.list.exportCsv') }}
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="standard">{{ t('asset.list.standardFormat') }}</el-dropdown-item>
              <el-dropdown-item command="threat-hunting">{{ t('asset.list.threatHuntingFormat') }}</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button type="primary" @click="goCreate">
          <el-icon><Plus /></el-icon>
          {{ t('asset.list.newAsset') }}
        </el-button>
      </div>
    </div>

    <!-- 筛选区 -->
    <div class="ui-filter-bar">
      <el-input
        v-model="query.search"
        :placeholder="t('asset.list.searchPlaceholder')"
        clearable
        style="width: 380px"
        @keyup.enter="handleSearch"
        @clear="handleSearch"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>

      <el-select v-model="query.network_zone" :placeholder="t('asset.list.filterZone')" clearable @change="handleSearch" style="width: 140px">
        <el-option-group :label="t('asset.list.traditionalZones')">
          <el-option :label="t('constants.zones.intranet')" value="intranet" />
          <el-option label="DMZ" value="dmz" />
          <el-option :label="t('constants.zones.office')" value="office" />
          <el-option :label="t('constants.zones.management')" value="management" />
          <el-option :label="t('constants.zones.other')" value="other" />
        </el-option-group>
        <el-option-group :label="t('asset.list.cloudProviders')">
          <el-option :label="t('constants.zones.aliyun')" value="aliyun" />
          <el-option :label="t('constants.zones.tencent')" value="tencent" />
          <el-option :label="t('constants.zones.huawei')" value="huawei" />
          <el-option label="AWS" value="aws" />
          <el-option label="Azure" value="azure" />
          <el-option label="Google Cloud" value="gcp" />
          <el-option :label="t('constants.zones.other_cloud')" value="other_cloud" />
        </el-option-group>
      </el-select>

      <el-select v-model="query.asset_type" :placeholder="t('asset.list.filterType')" clearable @change="handleSearch" style="width: 140px">
        <el-option :label="t('constants.assetTypes.physical')" value="physical" />
        <el-option :label="t('constants.assetTypes.virtual')" value="virtual" />
        <el-option :label="t('constants.assetTypes.cloud_server')" value="cloud_server" />
        <el-option :label="t('constants.assetTypes.network_device')" value="network_device" />
        <el-option :label="t('constants.assetTypes.other')" value="other" />
      </el-select>

      <el-select v-model="query.importance" :placeholder="t('asset.list.filterImportance')" clearable @change="handleSearch" style="width: 120px">
        <el-option :label="t('constants.importance.core')" value="core" />
        <el-option :label="t('constants.importance.important')" value="important" />
        <el-option :label="t('constants.importance.normal')" value="normal" />
      </el-select>

      <el-select v-model="query.status" :placeholder="t('asset.list.filterStatus')" clearable @change="handleSearch" style="width: 120px">
        <el-option :label="t('common.status.online')" value="online" />
        <el-option :label="t('common.status.offline')" value="offline" />
        <el-option :label="t('common.status.decommissioned')" value="decommissioned" />
      </el-select>

      <el-button @click="handleReset">
        <el-icon><Refresh /></el-icon>
        {{ t('asset.list.reset') }}
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
        <el-table-column prop="asset_no" :label="t('asset.list.columns.assetNo')" width="160">
          <template #default="{ row }">
            <span class="ui-id-link">{{ row.asset_no }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="ip_address" :label="t('asset.list.columns.ip')" width="140">
          <template #default="{ row }">
            <span class="ui-mono">{{ row.ip_address }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="hostname" :label="t('asset.list.columns.hostname')" width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span style="color: var(--neutral-700)">{{ row.hostname || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="asset_type" :label="t('asset.list.columns.type')" width="110">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ typeLabel(row.asset_type) }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="network_zone" :label="t('asset.list.columns.zone')" width="110">
          <template #default="{ row }">
            <span class="ui-zone" :class="zoneClass(row.network_zone)">
              {{ zoneLabel(row.network_zone) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="business_system" :label="t('asset.list.columns.businessSystem')" width="140" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.business_system" class="ui-mono" style="color: var(--neutral-700)">{{ row.business_system }}</span>
            <span v-else class="ui-mono-muted" style="font-size: 12px">-</span>
          </template>
        </el-table-column>

        <el-table-column prop="os_info" :label="t('asset.list.columns.os')" width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.os_info" style="color: var(--neutral-700)">{{ row.os_info }}</span>
            <span v-else class="ui-mono-muted" style="font-size: 12px">{{ t('asset.list.osUnidentified') }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="importance" :label="t('asset.list.columns.importance')" width="100">
          <template #default="{ row }">
            <span class="ui-imp" :class="'is-' + row.importance">{{ importanceLabel(row.importance) }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="status" :label="t('asset.list.columns.status')" width="110">
          <template #default="{ row }">
            <span class="ui-status" :class="'is-' + row.status">
              {{ statusLabel(row.status) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="owner" :label="t('asset.list.columns.owner')" width="100" />

        <el-table-column :label="t('asset.list.columns.actions')" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click.stop="router.push(`/assets/${row.id}/edit`)">
              {{ t('asset.list.edit') }}
            </el-button>
            <el-button
              v-if="row.status !== 'decommissioned' && row.status !== 'offline'"
              link
              type="danger"
              size="small"
              @click.stop="handleDecommission(row)"
            >
              {{ t('asset.list.decommission') }}
            </el-button>
            <el-button
              v-if="row.status === 'decommissioned' || row.status === 'offline'"
              link
              type="success"
              size="small"
              @click.stop="handleRestore(row)"
            >
              {{ t('asset.list.restore') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="ui-pagination-bar">
        <span class="ui-pagination-info">{{ t('asset.list.pagination', { total, page: query.page, totalPages }) }}</span>
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
