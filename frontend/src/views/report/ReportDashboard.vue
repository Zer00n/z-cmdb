<script setup lang="ts">
/**
 * 安全报表 Dashboard
 * 2026 UI Redesign：升级 KPI hero、按区域分布的可视化、配色升级，逻辑保持不变
 * v2.1：危险端口告警支持多字段筛选 + 分页
 */
import { ref, onMounted, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchPortExposure, fetchDangerousPorts, fetchShadowAssets } from '@/api/report'
import type { PortExposureData, DangerousPortsData, ShadowAssetsData } from '@/types/report'

const { t } = useI18n()
const loading = ref(true)
const portExposure = ref<PortExposureData | null>(null)
const dangerousPorts = ref<DangerousPortsData | null>(null)
const shadowAssets = ref<ShadowAssetsData | null>(null)

// ── 危险端口筛选 & 分页 ──────────────────────────────────────
const dpFilter = ref({
  asset_no: '',
  ip_address: '',
  port_number: '',
  service_name: '',
  network_zone: '',
  severity: '',
  hostname: '',
})
const dpPage = ref(1)
const dpPageSize = ref(20)

// 重置分页到第一页（筛选条件变化时触发）
watch(dpFilter, () => { dpPage.value = 1 }, { deep: true })

const ZONE_OPTIONS = computed(() => [
  { label: t('report.filters.allZones'), value: '' },
  { label: t('constants.zones.intranet'), value: 'intranet' },
  { label: 'DMZ', value: 'dmz' },
  { label: t('constants.zones.office'), value: 'office' },
  { label: t('constants.zones.management'), value: 'management' },
  { label: t('constants.zones.other'), value: 'other' },
])

const SEVERITY_OPTIONS = computed(() => [
  { label: t('report.filters.allSeverity'), value: '' },
  { label: t('report.severity.high'), value: 'high' },
  { label: t('report.severity.medium'), value: 'medium' },
])

/** 经过筛选后的全量告警 */
const dpFiltered = computed(() => {
  const all = dangerousPorts.value?.alerts ?? []
  const f = dpFilter.value
  return all.filter(a => {
    if (f.asset_no && !a.asset_no.toLowerCase().includes(f.asset_no.toLowerCase())) return false
    if (f.ip_address && a.ip_address !== f.ip_address.trim()) return false
    if (f.port_number && String(a.port_number) !== f.port_number.trim()) return false
    if (f.service_name && !(a.service_name ?? '').toLowerCase().includes(f.service_name.toLowerCase())) return false
    if (f.network_zone && a.network_zone !== f.network_zone) return false
    if (f.severity && a.severity !== f.severity) return false
    if (f.hostname && !(a.hostname ?? '').toLowerCase().includes(f.hostname.toLowerCase())) return false
    return true
  })
})

/** 当前页数据 */
const dpPageData = computed(() => {
  const start = (dpPage.value - 1) * dpPageSize.value
  return dpFiltered.value.slice(start, start + dpPageSize.value)
})

function resetDpFilter() {
  dpFilter.value = { asset_no: '', ip_address: '', port_number: '', service_name: '', network_zone: '', severity: '', hostname: '' }
  dpPage.value = 1
}
// ────────────────────────────────────────────────────────────

async function loadData() {
  loading.value = true
  try {
    const [pe, dp, sa] = await Promise.all([
      fetchPortExposure(),
      fetchDangerousPorts(),
      fetchShadowAssets(),
    ])
    portExposure.value = pe
    dangerousPorts.value = dp
    shadowAssets.value = sa
  } finally {
    loading.value = false
  }
}

function zoneLabel(zone: string): string {
  if (!zone) return zone || ''
  const key = `constants.zones.${zone}`
  return t(key) !== key ? t(key) : zone
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

const topPortMax = computed(() => {
  return portExposure.value?.top_ports?.[0]?.count || 1
})

const totalZonePorts = computed(() => {
  return portExposure.value?.zone_stats?.reduce((sum, s) => sum + s.port_count, 0) || 1
})

onMounted(loadData)
</script>

<template>
  <div v-loading="loading" class="ui-page">
    <!-- 页头 -->
    <div class="ui-page-head">
      <div>
        <h1 class="ui-page-title">{{ t('report.title') }}</h1>
        <p class="ui-page-subtitle">{{ t('report.subtitle') }}</p>
      </div>
    </div>

    <!-- KPI hero 网格 -->
    <div class="ui-kpi-grid">
      <div class="ui-kpi is-danger">
        <div class="ui-kpi-head">
          <span class="ui-kpi-label">{{ t('report.kpi.highDangerPorts') }}</span>
          <span class="ui-kpi-icon">
            <el-icon size="16"><Warning /></el-icon>
          </span>
        </div>
        <div class="ui-kpi-num">{{ dangerousPorts?.high_count || 0 }}</div>
        <div class="ui-kpi-foot">
          <el-icon size="12"><CaretTop /></el-icon>
          {{ t('report.kpi.highDangerPortsFoot') }}
        </div>
      </div>

      <div class="ui-kpi is-warning">
        <div class="ui-kpi-head">
          <span class="ui-kpi-label">{{ t('report.kpi.mediumDangerPorts') }}</span>
          <span class="ui-kpi-icon">
            <el-icon size="16"><InfoFilled /></el-icon>
          </span>
        </div>
        <div class="ui-kpi-num">{{ dangerousPorts?.medium_count || 0 }}</div>
        <div class="ui-kpi-foot">
          {{ t('report.kpi.mediumDangerPortsFoot') }}
        </div>
      </div>

      <div class="ui-kpi is-info">
        <div class="ui-kpi-head">
          <span class="ui-kpi-label">{{ t('report.kpi.shadowAssets') }}</span>
          <span class="ui-kpi-icon">
            <el-icon size="16"><View /></el-icon>
          </span>
        </div>
        <div class="ui-kpi-num">{{ shadowAssets?.total || 0 }}</div>
        <div class="ui-kpi-foot">
          {{ t('report.kpi.shadowAssetsFoot') }}
        </div>
      </div>

      <div class="ui-kpi is-accent">
        <div class="ui-kpi-head">
          <span class="ui-kpi-label">{{ t('report.kpi.exposedPortTypes') }}</span>
          <span class="ui-kpi-icon">
            <el-icon size="16"><Connection /></el-icon>
          </span>
        </div>
        <div class="ui-kpi-num">{{ portExposure?.top_ports?.length || 0 }}</div>
        <div class="ui-kpi-foot">
          {{ t('report.kpi.exposedPortTypesFoot') }}
        </div>
      </div>
    </div>

    <!-- 端口暴露面 + 按区域统计 横向布局 -->
    <div class="row-2">
      <!-- 左：Top 10 端口 -->
      <div class="ui-card">
        <div class="ui-card-head">
          <h3 class="ui-card-title">
            <span class="title-dot dot-blue" />
            {{ t('report.portExposure.title') }}
          </h3>
          <span class="card-meta">{{ t('report.portExposure.meta') }}</span>
        </div>
        <div class="port-list">
          <div
            v-for="(item, idx) in portExposure?.top_ports || []"
            :key="item.port"
            class="port-row"
          >
            <span class="port-rank">{{ String(idx + 1).padStart(2, '0') }}</span>
            <span class="port-num">{{ item.port }}</span>
            <div class="port-bar-wrap">
              <div
                class="port-bar"
                :style="{ width: `${(item.count / topPortMax) * 100}%` }"
              />
            </div>
            <span class="port-count">{{ item.count }}</span>
          </div>
          <div v-if="!portExposure?.top_ports?.length" class="ui-empty">
            <div class="ui-empty-title">{{ t('report.portExposure.emptyTitle') }}</div>
            <div class="ui-empty-desc">{{ t('report.portExposure.emptyDesc') }}</div>
          </div>
        </div>
      </div>

      <!-- 右：按区域统计 -->
      <div class="ui-card">
        <div class="ui-card-head">
          <h3 class="ui-card-title">
            <span class="title-dot dot-purple" />
            {{ t('report.zoneDistribution.title') }}
          </h3>
          <span class="card-meta">{{ t('report.zoneDistribution.meta') }}</span>
        </div>
        <div class="zone-list">
          <div
            v-for="stat in portExposure?.zone_stats || []"
            :key="stat.zone"
            class="zone-row"
          >
            <span class="ui-zone" :class="zoneClass(stat.zone)">
              {{ zoneLabel(stat.zone) }}
            </span>
            <div class="zone-bar-wrap">
              <div
                class="zone-bar"
                :class="zoneClass(stat.zone)"
                :style="{ width: `${(stat.port_count / totalZonePorts) * 100}%` }"
              />
            </div>
            <span class="zone-count">{{ stat.port_count }}</span>
          </div>
          <div v-if="!portExposure?.zone_stats?.length" class="ui-empty">
            <div class="ui-empty-title">{{ t('report.zoneDistribution.emptyTitle') }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 危险端口告警 -->
    <div v-if="dangerousPorts && dangerousPorts.alerts.length > 0" class="ui-card">
      <div class="ui-card-head">
        <h3 class="ui-card-title">
          <span class="title-dot dot-red" />
          {{ t('report.dangerousPorts.title') }}
          <span class="ui-page-count">
            {{ t('report.dangerousPorts.totalItems', { count: dpFiltered.length }) }}
            <template v-if="dpFiltered.length !== dangerousPorts.total">
              （{{ t('report.dangerousPorts.allItems', { count: dangerousPorts.total }) }}）
            </template>
          </span>
        </h3>
        <el-button
          v-if="Object.values(dpFilter).some(v => v !== '')"
          size="small"
          text
          @click="resetDpFilter"
        >
          {{ t('report.dangerousPorts.clearFilter') }}
        </el-button>
      </div>

      <!-- 筛选栏 -->
      <div class="dp-filter-bar">
        <el-input
          v-model="dpFilter.asset_no"
          :placeholder="t('report.dangerousPorts.filterAssetNo')"
          clearable
          size="small"
          class="dp-filter-input"
        />
        <el-input
          v-model="dpFilter.ip_address"
          :placeholder="t('report.dangerousPorts.filterIp')"
          clearable
          size="small"
          class="dp-filter-input"
        />
        <el-input
          v-model="dpFilter.hostname"
          :placeholder="t('report.dangerousPorts.filterHostname')"
          clearable
          size="small"
          class="dp-filter-input"
        />
        <el-input
          v-model="dpFilter.port_number"
          :placeholder="t('report.dangerousPorts.filterPort')"
          clearable
          size="small"
          class="dp-filter-input dp-filter-input--sm"
        />
        <el-input
          v-model="dpFilter.service_name"
          :placeholder="t('report.dangerousPorts.filterService')"
          clearable
          size="small"
          class="dp-filter-input dp-filter-input--sm"
        />
        <el-select
          v-model="dpFilter.network_zone"
          size="small"
          class="dp-filter-input dp-filter-input--sm"
        >
          <el-option
            v-for="opt in ZONE_OPTIONS"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
        <el-select
          v-model="dpFilter.severity"
          size="small"
          class="dp-filter-input dp-filter-input--sm"
        >
          <el-option
            v-for="opt in SEVERITY_OPTIONS"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
      </div>

      <!-- 表格 -->
      <el-table :data="dpPageData" stripe style="width: 100%">
        <el-table-column prop="asset_no" :label="t('report.dangerousPorts.columnAssetNo')" width="160">
          <template #default="{ row }">
            <span class="ui-mono">{{ row.asset_no }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="ip_address" :label="t('report.dangerousPorts.columnIp')" width="150">
          <template #default="{ row }">
            <span class="ui-mono">{{ row.ip_address }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="port_number" :label="t('report.dangerousPorts.columnPort')" width="90">
          <template #default="{ row }">
            <span class="port-chip">{{ row.port_number }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="service_name" :label="t('report.dangerousPorts.columnService')" width="130" />
        <el-table-column prop="network_zone" :label="t('report.dangerousPorts.columnZone')" width="120">
          <template #default="{ row }">
            <span class="ui-zone" :class="zoneClass(row.network_zone)">
              {{ zoneLabel(row.network_zone) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="severity" :label="t('report.dangerousPorts.columnSeverity')" width="110">
          <template #default="{ row }">
            <span class="ui-badge" :class="row.severity === 'high' ? 'is-danger' : 'is-warning'">
              <span class="ui-badge-dot" />
              {{ row.severity === 'high' ? t('report.severity.high') : t('report.severity.medium') }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="hostname" :label="t('report.dangerousPorts.columnHostname')" show-overflow-tooltip />
      </el-table>

      <!-- 分页 -->
      <div class="dp-pagination">
        <el-pagination
          v-model:current-page="dpPage"
          v-model:page-size="dpPageSize"
          :total="dpFiltered.length"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          size="small"
        />
      </div>
    </div>

    <!-- 影子资产 -->
    <div v-if="shadowAssets && shadowAssets.total > 0" class="ui-card">
      <div class="ui-card-head">
        <h3 class="ui-card-title">
          <span class="title-dot dot-cyan" />
          {{ t('report.shadowAssets.title') }}
          <span class="ui-page-count">{{ t('report.shadowAssets.totalItems', { count: shadowAssets.total }) }}</span>
        </h3>
      </div>
      <div style="padding: var(--space-2) var(--space-6) var(--space-4)">
        <div v-if="shadowAssets.incomplete_assets.length" style="margin-bottom: var(--space-4)">
          <h4 class="sub-title">{{ t('report.shadowAssets.incompleteTitle', { count: shadowAssets.incomplete_assets.length }) }}</h4>
          <el-table :data="shadowAssets.incomplete_assets" stripe style="width: 100%">
            <el-table-column prop="asset_no" :label="t('report.dangerousPorts.columnAssetNo')" width="160">
              <template #default="{ row }"><span class="ui-mono">{{ row.asset_no }}</span></template>
            </el-table-column>
            <el-table-column prop="ip_address" :label="t('report.shadowAssets.columnIp')" width="150">
              <template #default="{ row }"><span class="ui-mono">{{ row.ip_address }}</span></template>
            </el-table-column>
            <el-table-column prop="hostname" :label="t('report.shadowAssets.columnHostname')" width="180" />
            <el-table-column prop="reason" :label="t('report.shadowAssets.columnReason')" />
          </el-table>
        </div>
        <div v-if="shadowAssets.long_offline_assets.length">
          <h4 class="sub-title">{{ t('report.shadowAssets.offlineTitle', { count: shadowAssets.long_offline_assets.length }) }}</h4>
          <el-table :data="shadowAssets.long_offline_assets" stripe style="width: 100%">
            <el-table-column prop="asset_no" :label="t('report.dangerousPorts.columnAssetNo')" width="160">
              <template #default="{ row }"><span class="ui-mono">{{ row.asset_no }}</span></template>
            </el-table-column>
            <el-table-column prop="ip_address" :label="t('report.shadowAssets.columnIp')" width="150">
              <template #default="{ row }"><span class="ui-mono">{{ row.ip_address }}</span></template>
            </el-table-column>
            <el-table-column prop="hostname" :label="t('report.shadowAssets.columnHostname')" width="180" />
            <el-table-column prop="missing_count" :label="t('report.shadowAssets.columnMissingCount')" width="160">
              <template #default="{ row }">
                <span class="ui-badge is-warning"><span class="ui-badge-dot" />{{ row.missing_count }}</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.row-2 {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: var(--space-4);
}

/* 卡片细节 */
.title-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dot-blue   { background: linear-gradient(135deg, #2563EB, #6366F1); }
.dot-purple { background: linear-gradient(135deg, #6366F1, #8B5CF6); }
.dot-red    { background: linear-gradient(135deg, #DC2626, #EA580C); }
.dot-cyan   { background: linear-gradient(135deg, #0891B2, #06B6D4); }

.card-meta {
  font-size: 12px;
  color: var(--neutral-500);
  font-family: var(--font-mono);
}

/* 端口列表 */
.port-list {
  padding: var(--space-3) var(--space-6) var(--space-4);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.port-row {
  display: grid;
  grid-template-columns: 28px 64px 1fr 60px;
  align-items: center;
  gap: var(--space-3);
  padding: 6px 0;
}
.port-rank {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--neutral-400);
  letter-spacing: 0.05em;
}
.port-num {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 600;
  color: var(--neutral-900);
}
.port-bar-wrap {
  height: 6px;
  background: var(--surface-sunken);
  border-radius: 6px;
  overflow: hidden;
}
.port-bar {
  height: 100%;
  background: linear-gradient(90deg, #2563EB 0%, #6366F1 100%);
  border-radius: 6px;
  box-shadow: 0 0 8px -1px rgba(37, 99, 235, 0.5);
  transition: width 360ms var(--ease-out);
}
.port-count {
  text-align: right;
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 600;
  color: var(--neutral-900);
}

/* 区域列表 */
.zone-list {
  padding: var(--space-3) var(--space-6) var(--space-4);
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.zone-row {
  display: grid;
  grid-template-columns: 90px 1fr 60px;
  align-items: center;
  gap: var(--space-3);
}
.zone-bar-wrap {
  height: 8px;
  background: var(--surface-sunken);
  border-radius: 8px;
  overflow: hidden;
}
.zone-bar {
  height: 100%;
  border-radius: 8px;
  transition: width 360ms var(--ease-out);
}
.zone-bar.zone-intranet { background: linear-gradient(90deg, #2563EB, #5A82F4); }
.zone-bar.zone-dmz      { background: linear-gradient(90deg, #B45309, #F59E0B); }
.zone-bar.zone-office   { background: linear-gradient(90deg, #0E7490, #06B6D4); }
.zone-bar.zone-mgmt     { background: linear-gradient(90deg, #6D28D9, #8B5CF6); }
.zone-bar.zone-other    { background: linear-gradient(90deg, #94A3B8, #CBD5E1); }

.zone-count {
  text-align: right;
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 600;
  color: var(--neutral-900);
}

/* 端口数字 chip */
.port-chip {
  display: inline-block;
  padding: 1px 8px;
  background: var(--surface-sunken);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 12.5px;
  font-weight: 600;
  color: var(--neutral-900);
}

.sub-title {
  margin: 0 0 var(--space-2);
  font-size: 13px;
  font-weight: 600;
  color: var(--neutral-700);
  letter-spacing: 0.02em;
}

/* 危险端口筛选栏 */
.dp-filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: var(--space-3) var(--space-6);
  border-bottom: 1px solid var(--neutral-100);
  background: var(--surface-sunken);
}
.dp-filter-input {
  width: 160px;
}
.dp-filter-input--sm {
  width: 120px;
}

/* 分页区域 */
.dp-pagination {
  display: flex;
  justify-content: flex-end;
  padding: var(--space-3) var(--space-6);
  border-top: 1px solid var(--neutral-100);
}
</style>
