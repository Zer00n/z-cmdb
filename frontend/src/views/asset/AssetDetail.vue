<script setup lang="ts">
/**
 * 资产详情页
 * 2026 UI Redesign：升级头部 hero 区与信息卡片，业务逻辑保持不变
 */
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchAsset, decommissionAsset, updateAsset } from '@/api/asset'
import type { Asset } from '@/types/asset'
import AppServiceTable from '@/components/asset/AppServiceTable.vue'
import { useTranslatedLabels } from '@/composables/useTranslatedLabels'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const { zoneLabel, typeLabel, importanceLabel, statusLabel } = useTranslatedLabels()

const loading = ref(true)
const asset = ref<Asset | null>(null)
const activeTab = ref('basic')
const appCount = ref(0)

const assetId = computed(() => Number(route.params.id))

async function loadAsset() {
  loading.value = true
  try {
    asset.value = await fetchAsset(assetId.value)
  } finally {
    loading.value = false
  }
}

async function handleDecommission() {
  if (!asset.value) return
  await ElMessageBox.confirm(
    t('asset.detail.decommissionConfirm', { no: asset.value.asset_no }),
    t('asset.detail.decommissionTitle'),
    { confirmButtonText: t('asset.detail.decommissionBtn'), cancelButtonText: t('common.cancel'), type: 'warning' }
  )
  await decommissionAsset(assetId.value)
  ElMessage.success(t('asset.detail.decommissionSuccess'))
  loadAsset()
}

async function handleRestore() {
  if (!asset.value) return
  await ElMessageBox.confirm(
    t('asset.detail.restoreConfirm', { no: asset.value.asset_no }),
    t('asset.detail.restoreTitle'),
    { confirmButtonText: t('asset.detail.restoreBtn'), cancelButtonText: t('common.cancel'), type: 'info' }
  )
  await updateAsset(assetId.value, { status: 'online' })
  ElMessage.success(t('asset.detail.restoreSuccess'))
  loadAsset()
}

function formatTime(time: string | null): string {
  if (!time) return '-'
  return dayjs(time).format('YYYY-MM-DD HH:mm')
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

onMounted(loadAsset)
</script>

<template>
  <div v-loading="loading" class="ui-page">
    <template v-if="asset">
      <!-- Hero 头部 -->
      <div class="hero-card">
        <div class="hero-grad" aria-hidden="true" />
        <div class="hero-main">
          <div class="hero-meta">
            <span class="hero-id">{{ asset.asset_no }}</span>
            <span class="ui-status" :class="'is-' + asset.status">{{ statusLabel(asset.status) }}</span>
          </div>
          <h1 class="hero-title">{{ asset.hostname || asset.ip_address }}</h1>
          <div class="hero-sub">
            <span class="ui-mono">{{ asset.ip_address }}</span>
            <span class="hero-sep" />
            <span>{{ typeLabel(asset.asset_type) }}</span>
            <span class="hero-sep" />
            <span>{{ asset.business_system }}</span>
            <span class="hero-sep" />
            <span>{{ t('asset.detail.lastScan') }} {{ formatTime(asset.last_seen_at) }}</span>
          </div>
        </div>
        <div class="hero-actions">
          <el-button @click="router.push('/assets')">
            <el-icon><ArrowLeft /></el-icon>
            {{ t('asset.detail.backToList') }}
          </el-button>
          <el-button @click="router.push(`/assets/${asset.id}/edit`)">
            <el-icon><Edit /></el-icon>
            {{ t('asset.detail.edit') }}
          </el-button>
          <el-button
            v-if="asset.status !== 'decommissioned'"
            type="danger"
            plain
            @click="handleDecommission"
          >
            {{ t('asset.detail.decommission') }}
          </el-button>
          <el-button
            v-if="asset.status === 'decommissioned' || asset.status === 'offline'"
            type="success"
            plain
            @click="handleRestore"
          >
            {{ t('asset.detail.restore') }}
          </el-button>
        </div>
      </div>

      <!-- 信息卡片 -->
      <div class="info-cards">
        <div class="info-card">
          <div class="ic-label">{{ t('asset.detail.infoCards.zone') }}</div>
          <div class="ic-value">
            <span class="ui-zone" :class="zoneClass(asset.network_zone)">
              {{ zoneLabel(asset.network_zone) }}
            </span>
          </div>
        </div>
        <div class="info-card">
          <div class="ic-label">{{ t('asset.detail.infoCards.importance') }}</div>
          <div class="ic-value">
            <span class="ui-imp" :class="'is-' + asset.importance">{{ importanceLabel(asset.importance) }}</span>
          </div>
        </div>
        <div class="info-card">
          <div class="ic-label">{{ t('asset.detail.infoCards.owner') }}</div>
          <div class="ic-value">{{ asset.owner }}</div>
        </div>
        <div class="info-card">
          <div class="ic-label">{{ t('asset.detail.infoCards.source') }}</div>
          <div class="ic-value">{{ asset.source === 'scan' ? t('asset.detail.sourceLabels.scan') : t('asset.detail.sourceLabels.manual') }}</div>
        </div>
      </div>

      <!-- Tab 区域 -->
      <div class="ui-card">
        <el-tabs v-model="activeTab" style="padding: 0 var(--space-6)">
          <el-tab-pane :label="t('asset.detail.tabs.basic')" name="basic">
            <div class="field-grid">
              <div class="field"><span class="lbl">{{ t('asset.detail.fields.assetNo') }}</span><span class="val ui-mono">{{ asset.asset_no }}</span></div>
              <div class="field"><span class="lbl">{{ t('asset.detail.fields.ip') }}</span><span class="val ui-mono">{{ asset.ip_address }}</span></div>
              <div class="field"><span class="lbl">{{ t('asset.detail.fields.mac') }}</span><span class="val ui-mono">{{ asset.mac_address || '-' }}</span></div>
              <div class="field"><span class="lbl">{{ t('asset.detail.fields.hostname') }}</span><span class="val">{{ asset.hostname || '-' }}</span></div>
              <div class="field"><span class="lbl">{{ t('asset.detail.fields.os') }}</span><span class="val">{{ asset.os_info || '-' }}</span></div>
              <div class="field"><span class="lbl">{{ t('asset.detail.fields.assetType') }}</span><span class="val">{{ typeLabel(asset.asset_type) }}</span></div>
              <div class="field"><span class="lbl">{{ t('asset.detail.fields.location') }}</span><span class="val">{{ asset.location }}</span></div>
              <div class="field"><span class="lbl">{{ t('asset.detail.fields.businessSystem') }}</span><span class="val">{{ asset.business_system }}</span></div>
              <div class="field"><span class="lbl">{{ t('asset.detail.fields.source') }}</span><span class="val">{{ asset.source === 'scan' ? t('asset.detail.sourceLabels.scan') : t('asset.detail.sourceLabels.manual') }}</span></div>
              <div class="field"><span class="lbl">{{ t('asset.detail.fields.cpu') }}</span><span class="val">{{ asset.cpu || '-' }}</span></div>
              <div class="field"><span class="lbl">{{ t('asset.detail.fields.memory') }}</span><span class="val">{{ asset.memory_gb ? asset.memory_gb + ' GB' : '-' }}</span></div>
              <div class="field"><span class="lbl">{{ t('asset.detail.fields.disk') }}</span><span class="val">{{ asset.disk_gb ? asset.disk_gb + ' GB' : '-' }}</span></div>
              <div class="field"><span class="lbl">{{ t('asset.detail.fields.purchaseDate') }}</span><span class="val">{{ asset.purchase_date || '-' }}</span></div>
              <div class="field"><span class="lbl">{{ t('asset.detail.fields.warrantyExpiry') }}</span><span class="val">{{ asset.warranty_expiry || '-' }}</span></div>
              <div class="field"><span class="lbl">{{ t('asset.detail.fields.createdAt') }}</span><span class="val ui-mono">{{ formatTime(asset.created_at) }}</span></div>
            </div>
            <div v-if="asset.remark" class="remark-block">
              <div class="remark-label">{{ t('asset.detail.fields.remark') }}</div>
              <div class="remark-content">{{ asset.remark }}</div>
            </div>
          </el-tab-pane>

          <el-tab-pane :label="`${t('asset.detail.tabs.ports')} (${asset.ports.length})`" name="ports">
            <el-table :data="asset.ports" stripe style="width: 100%">
              <el-table-column prop="port_number" :label="t('asset.detail.portColumns.port')" width="100">
                <template #default="{ row }">
                  <span class="port-chip">{{ row.port_number }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="protocol" :label="t('asset.detail.portColumns.protocol')" width="80">
                <template #default="{ row }">
                  <el-tag size="small" effect="plain">{{ row.protocol }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="service_name" :label="t('asset.detail.portColumns.service')" width="140" />
              <el-table-column prop="service_version" :label="t('asset.detail.portColumns.version')" show-overflow-tooltip />
              <el-table-column prop="state" :label="t('asset.detail.portColumns.status')" width="110">
                <template #default="{ row }">
                  <span class="port-state" :class="row.state">
                    <span class="port-dot" />
                    {{ row.state }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column prop="last_seen_at" :label="t('asset.detail.portColumns.lastFound')" width="170">
                <template #default="{ row }">
                  <span class="ui-mono ui-mono-muted">{{ formatTime(row.last_seen_at) }}</span>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <el-tab-pane :label="`${t('asset.detail.tabs.apps')} (${appCount})`" name="apps">
            <div class="apps-pane">
              <AppServiceTable
                :asset-id="assetId"
                @count-change="(n: number) => appCount = n"
                @ports-changed="loadAsset"
              />
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </template>
  </div>
</template>

<style scoped>
/* Hero */
.hero-card {
  position: relative;
  background: var(--surface-base);
  border: var(--border-base);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-4);
  overflow: hidden;
  box-shadow: var(--shadow-subtle);
}
.hero-grad {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(420px 280px at 0% 0%, rgba(37, 99, 235, 0.08) 0%, transparent 60%),
    radial-gradient(360px 220px at 100% 0%, rgba(99, 102, 241, 0.06) 0%, transparent 55%);
}
.hero-main {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
}
.hero-meta {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.hero-id {
  font-family: var(--font-mono);
  font-size: 12.5px;
  font-weight: 600;
  color: var(--color-primary-700);
  background: var(--color-primary-50);
  border: 1px solid rgba(37, 99, 235, 0.16);
  padding: 3px 10px;
  border-radius: 999px;
}
.hero-title {
  margin: 0;
  font-size: 28px;
  line-height: 36px;
  font-weight: 700;
  color: var(--neutral-900);
  letter-spacing: -0.02em;
}
.hero-sub {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: var(--neutral-500);
  flex-wrap: wrap;
}
.hero-sep {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--neutral-300);
}
.hero-actions {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}

/* 信息卡片 */
.info-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-4);
}
.info-card {
  background: var(--surface-base);
  border: var(--border-base);
  border-radius: var(--radius-lg);
  padding: var(--space-4) var(--space-6);
  box-shadow: var(--shadow-subtle);
  transition: box-shadow var(--dur-base) var(--ease-out);
}
.info-card:hover {
  box-shadow: var(--shadow-medium);
  border-color: var(--neutral-300);
}
.ic-label {
  font-size: 11px;
  font-family: var(--font-mono);
  color: var(--neutral-400);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 8px;
}
.ic-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--neutral-900);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 24px;
}

/* 应用 Tab 顶部留白：与基本信息/端口的视觉间距对齐 */
.apps-pane {
  padding-top: var(--space-4);
}

/* 字段网格 */
.field-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4) var(--space-8);
  padding: var(--space-2) 0 var(--space-4);
}
.field { display: flex; flex-direction: column; gap: 4px; }
.field .lbl {
  font-size: 11px;
  color: var(--neutral-400);
  font-family: var(--font-mono);
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.field .val {
  font-size: var(--fs-body);
  color: var(--neutral-900);
}

/* 备注 */
.remark-block {
  margin-top: var(--space-4);
  background: var(--surface-sunken);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  padding: var(--space-4);
}
.remark-label {
  font-size: 11px;
  color: var(--neutral-400);
  font-family: var(--font-mono);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: var(--space-2);
}
.remark-content {
  font-size: var(--fs-body);
  color: var(--neutral-700);
  line-height: 22px;
}

/* 端口 chip */
.port-chip {
  display: inline-block;
  padding: 2px 10px;
  background: var(--surface-sunken);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 600;
  color: var(--neutral-900);
}

.port-state { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; }
.port-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--status-online); flex-shrink: 0; }
.port-state.closed .port-dot { background: var(--neutral-400); }
.port-state.filtered .port-dot { background: var(--color-warning); }
</style>
