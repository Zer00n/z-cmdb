<script setup lang="ts">
/**
 * Scan batch diff confirmation page
 * Based on Claude Design 07-scan-confirm.htm.html
 * Three sections: newly discovered / changed / missing
 */
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchScanDiff, confirmBatch, rejectBatch } from '@/api/scan'
import type { ScanDiffResponse, DiffNewHost, DiffChangedHost, DiffMissingHost, ScanConfirmRequest } from '@/types/scan'
import { useI18n } from 'vue-i18n'
import { useImportPresetStore } from '@/stores/importPreset'
import PresetSelect from '@/components/PresetSelect.vue'
import BatchPresetToolbar from '@/components/BatchPresetToolbar.vue'

const { t } = useI18n()

const route = useRoute()
const router = useRouter()
const presetStore = useImportPresetStore()

const batchId = computed(() => Number(route.params.id))
const loading = ref(true)
const loadingStep = ref<'presets' | 'diff'>('presets')
const submitting = ref(false)
const activeTab = ref('new')

const diffData = ref<ScanDiffResponse | null>(null)

// Supplementary fields for newly discovered assets
interface NewAssetForm {
  ip_address: string
  hostname: string | null
  os_info: string | null
  asset_type: string
  location: string
  owner: string
  business_system: string
  importance: string
  network_zone: string
  selected: boolean
}

const newAssetForms = ref<NewAssetForm[]>([])

async function loadDiff() {
  loading.value = true
  loadingStep.value = 'presets'
  try {
    await presetStore.ensureLoaded()
    loadingStep.value = 'diff'
    diffData.value = await fetchScanDiff(batchId.value)
    // Initialize new asset forms with preset defaults
    const defaultLocation = presetStore.defaultValue('location')
    const defaultOwner = presetStore.defaultValue('owner')
    const defaultBusinessSystem = presetStore.defaultValue('business_system')
    newAssetForms.value = (diffData.value.new_hosts || []).map((h: DiffNewHost) => ({
      ip_address: h.ip_address,
      hostname: h.hostname,
      os_info: h.os_info,
      asset_type: 'virtual',
      location: defaultLocation,
      owner: defaultOwner,
      business_system: defaultBusinessSystem,
      importance: 'normal',
      network_zone: 'intranet',
      selected: true,
    }))
  } finally {
    loading.value = false
  }
}

// Confirm import
async function handleConfirm() {
  if (!diffData.value) return

  // Validate required fields for selected new assets
  const selectedNew = newAssetForms.value.filter(f => f.selected)
  for (const item of selectedNew) {
    if (!item.location || !item.owner || !item.business_system) {
      ElMessage.warning(t('scan.confirm.validation.missingFields', { ip: item.ip_address }))
      activeTab.value = 'new'
      return
    }
  }

  await ElMessageBox.confirm(
    t('scan.confirm.confirmDialog.message', { newCount: selectedNew.length, changedCount: diffData.value.changed_count }),
    t('scan.confirm.confirmDialog.title'),
    { confirmButtonText: t('scan.confirm.confirmDialog.btn'), cancelButtonText: t('common.cancel'), type: 'info' }
  )

  submitting.value = true
  try {
    const req: ScanConfirmRequest = {
      new_assets: selectedNew.map(f => ({
        ip_address: f.ip_address,
        asset_type: f.asset_type,
        location: f.location,
        owner: f.owner,
        business_system: f.business_system,
        importance: f.importance,
        network_zone: f.network_zone,
        hostname: f.hostname || undefined,
        os_info: f.os_info || undefined,
      })),
    }
    await confirmBatch(batchId.value, req)
    ElMessage.success(t('scan.confirm.success.confirmed'))
    router.push('/scans')
  } finally {
    submitting.value = false
  }
}

// Reject batch
async function handleReject() {
  await ElMessageBox.confirm(
    t('scan.confirm.success.rejectConfirm'),
    t('scan.confirm.action.rejectBatch'),
    { confirmButtonText: t('scan.list.rejectBtn'), cancelButtonText: t('common.cancel'), type: 'warning' }
  )
  submitting.value = true
  try {
    await rejectBatch(batchId.value)
    ElMessage.success(t('scan.confirm.success.rejected'))
    router.push('/scans')
  } finally {
    submitting.value = false
  }
}

// Select/deselect all new assets
function toggleAllNew(checked: boolean) {
  newAssetForms.value.forEach(f => { f.selected = checked })
}

const allNewSelected = computed(() => newAssetForms.value.every(f => f.selected))

// Batch preset apply handler
function handleBatchApply(payload: { category: string; value: string; scope: string }) {
  const fieldMap: Record<string, keyof NewAssetForm> = {
    location: 'location',
    owner: 'owner',
    business_system: 'business_system',
  }
  const field = fieldMap[payload.category]
  if (!field) return

  let targets = newAssetForms.value
  if (payload.scope === 'selected') {
    targets = targets.filter(f => f.selected)
  }
  // 'all' uses all forms as-is
  for (const form of targets) {
    ;(form as any)[field] = payload.value
  }
}

onMounted(loadDiff)
</script>

<template>
  <div v-loading="loading" class="scan-confirm-page">
    <!-- Loading step hint -->
    <div v-if="loading" class="loading-steps">
      <div class="loading-step-item" :class="{ active: loadingStep === 'presets', done: loadingStep === 'diff' }">
        <span class="step-dot" /> {{ t('scan.confirm.loadingPresets') }}
      </div>
      <div class="loading-step-item" :class="{ active: loadingStep === 'diff' }">
        <span class="step-dot" /> {{ t('scan.confirm.loadingDiff') }}
      </div>
    </div>

    <!-- Import overlay -->
    <div v-if="submitting" class="import-overlay">
      <div class="import-overlay-content">
        <el-icon class="import-spinner" size="32"><Loading /></el-icon>
        <p>{{ t('scan.confirm.importing') }}</p>
      </div>
    </div>

    <template v-if="diffData">
      <!-- Page header -->
      <div class="ui-page-head">
        <div>
          <div class="title-row">
            <h1 class="ui-page-title">{{ t('scan.confirm.title') }}</h1>
            <span class="file-tag">{{ diffData.batch_name }}</span>
            <span class="ui-badge is-warning">
              <span class="ui-badge-dot" />
              {{ t('scan.confirm.pending') }}
            </span>
          </div>
          <p class="ui-page-subtitle">{{ t('scan.confirm.subtitle') }}</p>
        </div>
        <div class="ui-page-actions">
          <el-button @click="router.push('/scans')">
            <el-icon><ArrowLeft /></el-icon>
            {{ t('scan.confirm.backToList') }}
          </el-button>
        </div>
      </div>

      <!-- KPI cards -->
      <div class="ui-kpi-grid">
        <div class="ui-kpi">
          <div class="ui-kpi-head">
            <span class="ui-kpi-label">{{ t('scan.confirm.kpi.scannedHosts') }}</span>
            <span class="ui-kpi-icon"><el-icon size="16"><Connection /></el-icon></span>
          </div>
          <div class="ui-kpi-num">{{ diffData.total_hosts }}</div>
        </div>
        <div class="ui-kpi is-accent">
          <div class="ui-kpi-head">
            <span class="ui-kpi-label">{{ t('scan.confirm.kpi.newDiscovery') }}</span>
            <span class="ui-kpi-icon"><el-icon size="16"><Plus /></el-icon></span>
          </div>
          <div class="ui-kpi-num">{{ diffData.new_count }}</div>
        </div>
        <div class="ui-kpi is-warning">
          <div class="ui-kpi-head">
            <span class="ui-kpi-label">{{ t('scan.confirm.kpi.changed') }}</span>
            <span class="ui-kpi-icon"><el-icon size="16"><Refresh /></el-icon></span>
          </div>
          <div class="ui-kpi-num">{{ diffData.changed_count }}</div>
        </div>
        <div class="ui-kpi">
          <div class="ui-kpi-head">
            <span class="ui-kpi-label">{{ t('scan.confirm.kpi.missing') }}</span>
            <span class="ui-kpi-icon"><el-icon size="16"><Minus /></el-icon></span>
          </div>
          <div class="ui-kpi-num" style="color: var(--neutral-500)">{{ diffData.missing_count }}</div>
        </div>
      </div>

      <!-- Tab area -->
      <div class="ui-card" style="padding: var(--space-4) var(--space-6)">
        <el-tabs v-model="activeTab">
          <!-- New discovery tab -->
          <el-tab-pane :label="`${t('scan.confirm.tabs.new')} (${diffData.new_count})`" name="new">
            <div v-if="newAssetForms.length === 0" class="empty-hint">{{ t('scan.confirm.newTab.empty') }}</div>
            <template v-else>
              <BatchPresetToolbar
                :diff-types="['newDiscovery']"
                @apply="handleBatchApply"
              />
              <div class="tab-toolbar">
                <el-checkbox :model-value="allNewSelected" @change="toggleAllNew">{{ t('scan.confirm.newTab.selectAll') }}</el-checkbox>
                <span class="hint">{{ t('scan.confirm.newTab.hint') }}</span>
              </div>
              <div class="new-host-list">
                <div
                  v-for="(form, idx) in newAssetForms"
                  :key="form.ip_address"
                  class="new-host-card"
                  :class="{ disabled: !form.selected }"
                >
                  <div class="nh-head">
                    <el-checkbox v-model="form.selected" />
                    <span class="nh-ip mono">{{ form.ip_address }}</span>
                    <span v-if="form.hostname" class="nh-hostname">{{ form.hostname }}</span>
                    <span v-if="form.os_info" class="nh-os">{{ form.os_info }}</span>
                    <el-tag size="small" type="info" v-if="diffData.new_hosts[idx]?.ports?.length">
                      {{ t('scan.confirm.newTab.ports', { count: diffData.new_hosts[idx].ports.length }) }}
                    </el-tag>
                  </div>
                  <div v-if="form.selected" class="nh-form">
                    <div class="form-grid">
                      <div class="form-item">
                        <label>{{ t('scan.confirm.newTab.assetType') }}</label>
                        <el-select v-model="form.asset_type" size="small" style="width: 100%">
                          <el-option :label="t('scan.confirm.newTab.types.physical')" value="physical" />
                          <el-option :label="t('scan.confirm.newTab.types.virtual')" value="virtual" />
                          <el-option :label="t('scan.confirm.newTab.types.networkDevice')" value="network_device" />
                          <el-option :label="t('scan.confirm.newTab.types.other')" value="other" />
                        </el-select>
                      </div>
                      <div class="form-item">
                        <label>{{ t('scan.confirm.newTab.networkZone') }}</label>
                        <el-select v-model="form.network_zone" size="small" style="width: 100%">
                          <el-option :label="t('constants.zones.intranet')" value="intranet" />
                          <el-option :label="t('constants.zones.dmz')" value="dmz" />
                          <el-option :label="t('constants.zones.office')" value="office" />
                          <el-option :label="t('constants.zones.management')" value="management" />
                          <el-option :label="t('constants.zones.other')" value="other" />
                        </el-select>
                      </div>
                      <div class="form-item">
                        <label>{{ t('scan.confirm.newTab.importance') }}</label>
                        <el-select v-model="form.importance" size="small" style="width: 100%">
                          <el-option :label="t('constants.importance.core')" value="core" />
                          <el-option :label="t('constants.importance.important')" value="important" />
                          <el-option :label="t('constants.importance.normal')" value="normal" />
                        </el-select>
                      </div>
                      <div class="form-item">
                        <label>{{ t('scan.confirm.newTab.location') }}</label>
                        <PresetSelect category="location" v-model="form.location" size="small" />
                      </div>
                      <div class="form-item">
                        <label>{{ t('scan.confirm.newTab.owner') }}</label>
                        <PresetSelect category="owner" v-model="form.owner" size="small" />
                      </div>
                      <div class="form-item">
                        <label>{{ t('scan.confirm.newTab.businessSystem') }}</label>
                        <PresetSelect category="business_system" v-model="form.business_system" size="small" />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </el-tab-pane>

          <!-- Changes tab -->
          <el-tab-pane :label="`${t('scan.confirm.tabs.changed')} (${diffData.changed_count})`" name="changed">
            <div v-if="diffData.changed_hosts.length === 0" class="empty-hint">{{ t('scan.confirm.changedTab.empty') }}</div>
            <div v-else class="changed-list">
              <div
                v-for="host in diffData.changed_hosts"
                :key="host.ip_address"
                class="chg-card"
              >
                <div class="chg-head">
                  <span class="chg-id mono">{{ host.matched_asset_no || '-' }}</span>
                  <span class="chg-ip mono">{{ host.ip_address }}</span>
                  <span v-if="host.hostname" class="chg-hostname">{{ host.hostname }}</span>
                  <div class="chg-pills">
                    <span
                      v-for="pc in host.port_changes"
                      :key="`${pc.port_number}-${pc.protocol}`"
                      class="chg-pill"
                      :class="pc.change_type"
                    >
                      {{ pc.change_type === 'added' ? '+' : pc.change_type === 'removed' ? '−' : '~' }}
                      {{ pc.port_number }}/{{ pc.protocol }}
                      <template v-if="pc.new_service"> {{ pc.new_service }}</template>
                    </span>
                  </div>
                </div>
                <!-- Three-column comparison -->
                <div v-if="host.port_changes.length > 0" class="chg-body">
                  <div class="compare-head">
                    <div class="col-label">{{ t('scan.confirm.changedTab.field') }}</div>
                    <div class="col-scan">{{ t('scan.confirm.changedTab.scanValue') }}</div>
                    <div class="col-current">{{ t('scan.confirm.changedTab.currentValue') }}</div>
                  </div>
                  <div
                    v-for="pc in host.port_changes"
                    :key="`row-${pc.port_number}`"
                    class="compare-row"
                  >
                    <div class="col-label mono">{{ pc.port_number }}/{{ pc.protocol }}</div>
                    <div class="col-scan">
                      <span class="val">{{ pc.new_service || '-' }} {{ pc.new_version || '' }}</span>
                      <span v-if="pc.change_type === 'added'" class="diff-add">{{ t('scan.confirm.changedTab.added') }}</span>
                    </div>
                    <div class="col-current">
                      <span class="val">{{ pc.old_service || '-' }} {{ pc.old_version || '' }}</span>
                      <span v-if="pc.change_type === 'removed'" class="diff-del">{{ t('scan.confirm.changedTab.closed') }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <!-- Missing tab -->
          <el-tab-pane :label="`${t('scan.confirm.tabs.missing')} (${diffData.missing_count})`" name="missing">
            <div v-if="diffData.missing_hosts.length === 0" class="empty-hint">{{ t('scan.confirm.missingTab.empty') }}</div>
            <div v-else>
              <div class="missing-notice">
                <el-icon><InfoFilled /></el-icon>
                {{ t('scan.confirm.missingTab.notice') }}
              </div>
              <el-table :data="diffData.missing_hosts" stripe style="width: 100%">
                <el-table-column prop="matched_asset_no" :label="t('scan.confirm.missingTab.assetNo')" width="150">
                  <template #default="{ row }">
                    <span class="mono">{{ row.matched_asset_no || '-' }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="ip_address" :label="t('scan.confirm.missingTab.ip')" width="140">
                  <template #default="{ row }">
                    <span class="mono">{{ row.ip_address }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="hostname" :label="t('scan.confirm.missingTab.hostname')" width="160" />
                <el-table-column prop="missing_count" :label="t('scan.confirm.missingTab.consecutiveMiss')" width="120">
                  <template #default="{ row }">
                    <span :class="{ 'text-warning': row.missing_count >= 2 }">
                      {{ t('scan.confirm.missingTab.missCount', { count: row.missing_count }) }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column :label="t('scan.confirm.missingTab.statusPrediction')">
                  <template #default="{ row }">
                    <el-tag v-if="row.missing_count >= 2" type="warning" size="small">
                      {{ t('scan.confirm.missingTab.willOffline') }}
                    </el-tag>
                    <span v-else class="text-muted">{{ t('scan.confirm.missingTab.stayOnline') }}</span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>

      <!-- Bottom action bar -->
      <div class="action-bar">
        <div class="action-left">
          <span class="summary-item new">{{ t('scan.confirm.action.new') }} <b>{{ newAssetForms.filter(f => f.selected).length }}</b></span>
          <span class="summary-item chg">{{ t('scan.confirm.action.changed') }} <b>{{ diffData.changed_count }}</b></span>
          <span class="summary-item miss">{{ t('scan.confirm.action.missing') }} <b>{{ diffData.missing_count }}</b></span>
        </div>
        <div class="action-right">
          <el-button :loading="submitting" @click="handleReject">{{ t('scan.confirm.action.rejectBatch') }}</el-button>
          <el-button type="primary" :loading="submitting" @click="handleConfirm">
            {{ t('scan.confirm.action.confirmImport') }}
          </el-button>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.scan-confirm-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

/* Page header helpers */
.title-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}
.file-tag {
  font-family: var(--font-mono);
  font-size: 13px;
  background: var(--surface-sunken);
  color: var(--neutral-700);
  border: 1px solid var(--neutral-200);
  padding: 2px 10px;
  border-radius: 999px;
}

.empty-hint {
  text-align: center;
  padding: var(--space-12) var(--space-6);
  color: var(--neutral-400);
  font-size: var(--fs-body);
}

/* New discovery tab */
.tab-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-3);
  border-bottom: var(--border-base);
}
.tab-toolbar .hint {
  font-size: var(--fs-caption);
  color: var(--neutral-500);
}

.new-host-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.new-host-card {
  border: var(--border-base);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: border-color var(--dur-fast) var(--ease-out),
              box-shadow var(--dur-fast) var(--ease-out);
}
.new-host-card:hover {
  border-color: var(--neutral-300);
  box-shadow: var(--shadow-subtle);
}
.new-host-card.disabled {
  opacity: 0.5;
}
.nh-head {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--surface-sunken);
  border-bottom: var(--border-base);
}
.nh-ip {
  font-weight: 600;
  color: var(--neutral-900);
  font-family: var(--font-mono);
  font-size: 13px;
}
.nh-hostname { color: var(--neutral-700); }
.nh-os { font-size: var(--fs-caption); color: var(--neutral-500); }

.nh-form {
  padding: var(--space-4);
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
}
.form-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.form-item label {
  font-size: 12px;
  color: var(--neutral-700);
  font-weight: 500;
}

/* Changes tab */
.changed-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.chg-card {
  border: var(--border-base);
  border-radius: var(--radius-md);
  overflow: hidden;
}
.chg-head {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--surface-sunken);
}
.chg-id {
  color: var(--color-primary-600);
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 500;
}
.chg-ip {
  color: var(--neutral-900);
  font-weight: 500;
  font-family: var(--font-mono);
  font-size: 13px;
}
.chg-hostname { color: var(--neutral-500); font-size: var(--fs-caption); }
.chg-pills { display: flex; gap: 6px; flex-wrap: wrap; margin-left: auto; }
.chg-pill {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  font-family: var(--font-mono);
  font-weight: 500;
}
.chg-pill.added { background: var(--color-success-soft); color: #15803D; }
.chg-pill.removed { background: var(--color-danger-soft); color: #B91C1C; }
.chg-pill.modified { background: var(--color-warning-soft); color: #92400E; }

.chg-body {
  padding: var(--space-4);
  border-top: var(--border-base);
  background: linear-gradient(180deg, rgba(37, 99, 235, 0.02), transparent);
}
.compare-head {
  display: grid;
  grid-template-columns: 140px 1fr 1fr;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
  font-size: 11px;
  color: var(--neutral-500);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.compare-row {
  display: grid;
  grid-template-columns: 140px 1fr 1fr;
  gap: var(--space-3);
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--neutral-100);
  font-size: var(--fs-body);
}
.compare-row:last-child { border-bottom: none; }
.col-label {
  color: var(--neutral-700);
  font-weight: 500;
  font-family: var(--font-mono);
  font-size: 12.5px;
}
.col-scan .val { color: var(--neutral-900); }
.col-current .val { color: var(--neutral-500); }
.diff-add {
  font-size: 11px;
  background: var(--color-success-soft);
  color: #15803D;
  padding: 1px 6px;
  border-radius: 3px;
  margin-left: 6px;
  font-weight: 500;
}
.diff-del {
  font-size: 11px;
  background: var(--color-danger-soft);
  color: #B91C1C;
  padding: 1px 6px;
  border-radius: 3px;
  margin-left: 6px;
  font-weight: 500;
}

/* Missing tab */
.missing-notice {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 10px var(--space-4);
  background: linear-gradient(90deg, rgba(217, 119, 6, 0.06) 0%, rgba(245, 158, 11, 0.04) 100%);
  border: 1px solid rgba(217, 119, 6, 0.16);
  border-radius: var(--radius-md);
  font-size: var(--fs-caption);
  color: var(--neutral-700);
  margin-bottom: var(--space-4);
}
.text-warning { color: var(--color-warning); font-weight: 500; }
.text-muted { color: var(--neutral-400); font-size: var(--fs-caption); }

/* Bottom action bar (sticky) */
.action-bar {
  position: sticky;
  bottom: 0;
  background: var(--surface-overlay);
  -webkit-backdrop-filter: saturate(140%) blur(14px);
  backdrop-filter: saturate(140%) blur(14px);
  border: var(--border-base);
  border-radius: var(--radius-lg);
  padding: var(--space-3) var(--space-6);
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 -8px 24px -8px rgba(15, 23, 42, 0.08);
}
.action-left {
  display: flex;
  gap: var(--space-3);
}
.summary-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 999px;
  background: var(--surface-base);
  border: 1px solid var(--neutral-200);
  font-size: 12px;
  color: var(--neutral-700);
}
.summary-item b {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 13px;
}
.summary-item.new b { color: var(--color-primary-700); }
.summary-item.chg b { color: var(--color-warning); }
.summary-item.miss b { color: var(--neutral-500); }
.action-right { display: flex; gap: var(--space-3); }

.mono { font-family: var(--font-mono); font-size: 13px; }

/* Loading step indicators */
.loading-steps {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: var(--space-8) 0;
}
.loading-step-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--neutral-400);
  transition: color 0.3s;
}
.loading-step-item.active {
  color: var(--color-primary-600);
  font-weight: 500;
}
.loading-step-item.done {
  color: var(--color-success);
}
.step-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--neutral-300);
  transition: background 0.3s;
}
.loading-step-item.active .step-dot {
  background: var(--color-primary-500);
  animation: pulse-dot 1s infinite;
}
.loading-step-item.done .step-dot {
  background: var(--color-success);
}
@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* Import overlay */
.import-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
}
.import-overlay-content {
  text-align: center;
  color: var(--neutral-700);
  font-size: 16px;
  font-weight: 500;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}
.import-spinner {
  animation: spin 1s linear infinite;
  color: var(--color-primary-500);
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
