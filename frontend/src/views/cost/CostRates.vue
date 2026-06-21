<script setup lang="ts">
/**
 * 成本费率设置页
 * 折旧、电力、带宽、资源单价表、分摊动因 — 全局生效
 */
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { fetchCostRates, updateCostRates, CostRateEntry } from '@/api/cost'
import { useCostCurrency } from '@/composables/useCostCurrency'
import { useTimeFormat } from '@/composables/useTimeFormat'

const { t } = useI18n()
const authStore = useAuthStore()
const { symbol, refreshCurrency } = useCostCurrency()
const { formatTime: fmtTime } = useTimeFormat()

const loading = ref(false)
const saving = ref(false)
const lastSavedTime = ref('')
const lastSavedUser = ref('')
const showSaveSuccess = ref(false)

// ── Rate key mapping ─────────────────────────────────────
const rateKeys = {
  depreciation: 'depreciation_defaults',
  electricity_price: 'electricity_price',
  pue: 'pue',
  load_factor: 'load_factor',
  bandwidth_price: 'bandwidth_price',
  rack_cost: 'rack_cost',
  idc_hosting: 'idc_hosting',
  currency: 'default_currency',
  tax_basis: 'tax_basis',
  price_book: 'price_book',
  allocation_drivers: 'allocation_drivers',
}

// ── Asset type definitions ────────────────────────────────
interface DeprRow {
  key: string
  color: string
  years: number
  residual: number
  method: string
  strategy: string
}

const defaultDeprRows: DeprRow[] = [
  { key: 'physical_server', color: '#2563EB', years: 5, residual: 10, method: 'straight', strategy: 'zero' },
  { key: 'virtual_machine', color: '#5A82F4', years: 3, residual: 5, method: 'straight', strategy: 'zero' },
  { key: 'network_device', color: '#0891B2', years: 8, residual: 5, method: 'straight', strategy: 'revalue' },
  { key: 'storage_device', color: '#D97706', years: 7, residual: 10, method: 'straight', strategy: 'zero' },
  { key: 'security_device', color: '#EA580C', years: 5, residual: 5, method: 'straight', strategy: 'zero' },
  { key: 'software_license', color: '#94A3B8', years: 3, residual: 0, method: 'straight', strategy: 'zero' },
]

function assetTypeLabel(key: string): string {
  const i18nMap: Record<string, string> = {
    physical_server: t('cost.rates.assetType.physicalServer'),
    virtual_machine: t('cost.rates.assetType.virtualMachine'),
    network_device: t('cost.rates.assetType.networkDevice'),
    storage_device: t('cost.rates.assetType.storageDevice'),
    security_device: t('cost.rates.assetType.securityDevice'),
    software_license: t('cost.rates.assetType.softwareLicense'),
  }
  return i18nMap[key] || key
}

function priceBookLabel(key: string): string {
  const i18nMap: Record<string, string> = {
    vcpu: 'vCPU',
    memory: t('cost.rates.priceBookLabels.memory'),
    storage_hdd: t('cost.rates.priceBookLabels.storageHdd'),
    storage_ssd: t('cost.rates.priceBookLabels.storageSsd'),
    bandwidth: t('cost.rates.priceBookLabels.bandwidth'),
    public_ip: t('cost.rates.priceBookLabels.publicIp'),
  }
  return i18nMap[key] || key
}

// ── Price book definitions ────────────────────────────────
interface PriceRow {
  key: string
  unitKey: string
  stdPrice: number
  costPrice: number
  enabled: boolean
}

const defaultPriceBook: PriceRow[] = [
  { key: 'vcpu', unitKey: 'cpuMonth', stdPrice: 25, costPrice: 18, enabled: true },
  { key: 'memory', unitKey: 'gbMonth', stdPrice: 8, costPrice: 5.5, enabled: true },
  { key: 'storage_hdd', unitKey: 'gbMonth', stdPrice: 0.25, costPrice: 0.18, enabled: true },
  { key: 'storage_ssd', unitKey: 'gbMonth', stdPrice: 0.80, costPrice: 0.60, enabled: true },
  { key: 'bandwidth', unitKey: 'mbpsMonth', stdPrice: 150, costPrice: 120, enabled: true },
  { key: 'public_ip', unitKey: 'countMonth', stdPrice: 30, costPrice: 22, enabled: false },
]

function priceBookUnit(unitKey: string): string {
  return t(`cost.rates.priceBookUnits.${unitKey}`)
}

// ── Allocation driver definitions ─────────────────────────
interface AllocRow {
  key: string
  nameKey: string
  descKey: string
  basis: string
  isFallback?: boolean
}

const defaultAllocDrivers: AllocRow[] = [
  { key: 'storage', nameKey: 'storage', descKey: 'storage', basis: 'gb_capacity' },
  { key: 'firewall', nameKey: 'firewall', descKey: 'firewall', basis: 'protected_assets' },
  { key: 'network', nameKey: 'network', descKey: 'network', basis: 'port_usage' },
  { key: 'loadbalancer', nameKey: 'loadbalancer', descKey: 'loadbalancer', basis: 'backend_services' },
  { key: 'fallback', nameKey: 'fallback', descKey: 'fallback', basis: 'asset_count', isFallback: true },
]

function driverName(key: string): string {
  return t(`cost.rates.allocDriver.${key}`) || key
}

function driverDesc(key: string): string {
  return t(`cost.rates.allocDriverDesc.${key}`) || ''
}

// ── Local reactive state ──────────────────────────────────
const deprRows = ref<DeprRow[]>(JSON.parse(JSON.stringify(defaultDeprRows)))
const electricityPrice = ref(0.72)
const pue = ref(1.45)
const loadFactor = ref(0.65)
const bandwidthPrice = ref(150)
const rackCost = ref(800)
const idcHosting = ref(2500)
const currency = ref('CNY')
const taxBasis = ref('inclusive')
const priceBook = ref<PriceRow[]>(JSON.parse(JSON.stringify(defaultPriceBook)))
const allocDrivers = ref<AllocRow[]>(JSON.parse(JSON.stringify(defaultAllocDrivers)))

// ── Populate from API response ────────────────────────────
function populateFromRates(rates: Record<string, CostRateEntry>) {
  const get = (key: string): string | undefined => rates[key]?.value

  // Depreciation
  const depRaw = get(rateKeys.depreciation)
  if (depRaw) {
    try {
      const depData = typeof depRaw === 'string' ? JSON.parse(depRaw) : depRaw
      if (Array.isArray(depData)) {
        deprRows.value = depData.map((d: any, i: number) => ({
          key: d.type || defaultDeprRows[i]?.key || `type_${i}`,
          color: defaultDeprRows[i]?.color || '#94A3B8',
          years: Number(d.years ?? defaultDeprRows[i]?.years ?? 5),
          residual: Number(d.residual_rate ?? defaultDeprRows[i]?.residual ?? 0),
          method: d.method || defaultDeprRows[i]?.method || 'straight',
          strategy: d.strategy || defaultDeprRows[i]?.strategy || 'zero',
        }))
      }
    } catch {
      /* keep defaults */
    }
  }

  // Scalar params
  const ep = get(rateKeys.electricity_price)
  if (ep != null) electricityPrice.value = Number(ep)
  const p = get(rateKeys.pue)
  if (p != null) pue.value = Number(p)
  const lf = get(rateKeys.load_factor)
  if (lf != null) loadFactor.value = Number(lf)
  const bp = get(rateKeys.bandwidth_price)
  if (bp != null) bandwidthPrice.value = Number(bp)
  const rc = get(rateKeys.rack_cost)
  if (rc != null) rackCost.value = Number(rc)
  const ih = get(rateKeys.idc_hosting)
  if (ih != null) idcHosting.value = Number(ih)
  const cur = get(rateKeys.currency)
  if (cur) currency.value = cur
  const tb = get(rateKeys.tax_basis)
  if (tb) taxBasis.value = tb

  // Price book
  const pbRaw = get(rateKeys.price_book)
  if (pbRaw) {
    try {
      const pbData = typeof pbRaw === 'string' ? JSON.parse(pbRaw) : pbRaw
      if (Array.isArray(pbData)) {
        priceBook.value = pbData.map((p: any, i: number) => ({
          key: p.type || defaultPriceBook[i]?.key || `res_${i}`,
          unitKey: p.unit_key || defaultPriceBook[i]?.unitKey || 'gbMonth',
          stdPrice: Number(p.std_price ?? defaultPriceBook[i]?.stdPrice ?? 0),
          costPrice: Number(p.cost_price ?? defaultPriceBook[i]?.costPrice ?? 0),
          enabled: p.enabled !== undefined ? Boolean(p.enabled) : (defaultPriceBook[i]?.enabled ?? true),
        }))
      }
    } catch {
      /* keep defaults */
    }
  }

  // Allocation drivers
  const adRaw = get(rateKeys.allocation_drivers)
  if (adRaw) {
    try {
      const adData = typeof adRaw === 'string' ? JSON.parse(adRaw) : adRaw
      if (Array.isArray(adData)) {
        allocDrivers.value = adData.map((d: any, i: number) => ({
          key: d.type || defaultAllocDrivers[i]?.key || `drv_${i}`,
          nameKey: d.type || defaultAllocDrivers[i]?.nameKey || '',
          descKey: d.type || defaultAllocDrivers[i]?.descKey || '',
          basis: d.basis || defaultAllocDrivers[i]?.basis || 'asset_count',
          isFallback: defaultAllocDrivers[i]?.isFallback ?? false,
        }))
      }
    } catch {
      /* keep defaults */
    }
  }

  // Last saved metadata from any entry
  for (const entry of Object.values(rates)) {
    if (entry.updated_at) {
      lastSavedTime.value = fmtTime(entry.updated_at, 'YYYY-MM-DD HH:mm:ss')
      break
    }
  }
}

// ── Fetch on mount ────────────────────────────────────────
async function loadRates() {
  loading.value = true
  try {
    const rates = await fetchCostRates()
    populateFromRates(rates)
  } catch {
    /* keep defaults */
  } finally {
    loading.value = false
  }
}

onMounted(loadRates)

// ── Serialize for save ────────────────────────────────────
function buildPayload(): Record<string, unknown> {
  return {
    [rateKeys.depreciation]: JSON.stringify(
      deprRows.value.map(r => ({
        type: r.key,
        years: r.years,
        residual_rate: r.residual,
        method: r.method,
        strategy: r.strategy,
      })),
    ),
    [rateKeys.electricity_price]: String(electricityPrice.value),
    [rateKeys.pue]: String(pue.value),
    [rateKeys.load_factor]: String(loadFactor.value),
    [rateKeys.bandwidth_price]: String(bandwidthPrice.value),
    [rateKeys.rack_cost]: String(rackCost.value),
    [rateKeys.idc_hosting]: String(idcHosting.value),
    [rateKeys.currency]: currency.value,
    [rateKeys.tax_basis]: taxBasis.value,
    [rateKeys.price_book]: JSON.stringify(
      priceBook.value.map(r => ({
        type: r.key,
        unit_key: r.unitKey,
        std_price: r.stdPrice,
        cost_price: r.costPrice,
        enabled: r.enabled,
      })),
    ),
    [rateKeys.allocation_drivers]: JSON.stringify(
      allocDrivers.value.map(r => ({
        type: r.key,
        description: driverDesc(r.key),
        basis: r.basis,
      })),
    ),
  }
}

// ── Actions ───────────────────────────────────────────────
async function handleSave() {
  saving.value = true
  try {
    const payload = buildPayload()
    await updateCostRates(payload)
    showSaveSuccess.value = true
    ElMessage.success(t('cost.rates.saveSuccess'))
    refreshCurrency()
    setTimeout(() => {
      showSaveSuccess.value = false
    }, 2000)
    // Refresh metadata
    await loadRates()
  } finally {
    saving.value = false
  }
}

async function handleReset() {
  try {
    await ElMessageBox.confirm(
      t('cost.rates.resetConfirmMessage'),
      t('cost.rates.resetConfirmTitle'),
      {
        confirmButtonText: t('cost.rates.reset'),
        cancelButtonText: t('common.cancel'),
        type: 'warning',
      },
    )
  } catch {
    return
  }
  deprRows.value = JSON.parse(JSON.stringify(defaultDeprRows))
  electricityPrice.value = 0.72
  pue.value = 1.45
  loadFactor.value = 0.65
  bandwidthPrice.value = 150
  rackCost.value = 800
  idcHosting.value = 2500
  currency.value = 'CNY'
  taxBasis.value = 'inclusive'
  priceBook.value = JSON.parse(JSON.stringify(defaultPriceBook))
  allocDrivers.value = JSON.parse(JSON.stringify(defaultAllocDrivers))
  ElMessage.success(t('cost.rates.resetSuccess'))
}

function handleCancel() {
  loadRates()
}
</script>

<template>
  <div v-loading="loading" class="cost-rates-page">
    <div class="cost-rates-container">

      <!-- Access banner -->
      <div class="access-banner">
        <el-icon class="ab-icon" :size="16">
          <Lock />
        </el-icon>
        <span>{{ t('cost.rates.accessBanner') }}</span>
      </div>

      <!-- Page header -->
      <div class="ui-page-head" style="margin-bottom: var(--space-6)">
        <div>
          <h1 class="ui-page-title">{{ t('cost.rates.title') }}</h1>
          <p class="ui-page-subtitle">{{ t('cost.rates.lastSaved', { time: lastSavedTime || '—', user: lastSavedUser || '—' }) }}</p>
        </div>
        <div class="ui-page-actions">
          <el-button @click="handleReset">
            <el-icon><RefreshRight /></el-icon>
            {{ t('cost.rates.resetDefault') }}
          </el-button>
          <el-button type="primary" :loading="saving" @click="handleSave">
            <el-icon><Check /></el-icon>
            {{ t('cost.rates.saveSettings') }}
          </el-button>
        </div>
      </div>

      <!-- ===== SECTION 1: 成本参数 ===== -->
      <div class="sec-card">
        <div class="sec-head">
          <div class="sec-icon sec-icon--purple">
            <el-icon :size="16"><Setting /></el-icon>
          </div>
          <div class="sec-head-text">
            <span class="sec-title">{{ t('cost.rates.costParams') }}</span>
            <span class="sec-desc">{{ t('cost.rates.costParamsDesc') }}</span>
          </div>
        </div>
        <div class="sec-body">

          <!-- Depreciation parameters -->
          <div class="form-group">
            <div class="fg-label">
              <span>{{ t('cost.rates.deprTable.assetType') }} — {{ t('cost.rates.costParams') }}</span>
            </div>
            <div class="depr-table-wrap">
              <table class="depr-table">
                <thead>
                  <tr>
                    <th style="width:170px">{{ t('cost.rates.deprTable.assetType') }}</th>
                    <th style="width:130px">{{ t('cost.rates.deprTable.deprYears') }}</th>
                    <th style="width:130px">{{ t('cost.rates.deprTable.residualRate') }}</th>
                    <th style="width:150px">{{ t('cost.rates.deprTable.deprMethod') }}</th>
                    <th>{{ t('cost.rates.deprTable.eolStrategy') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, idx) in deprRows" :key="row.key">
                    <td>
                      <div class="asset-label">
                        <span class="asset-dot" :style="{ background: row.color }"></span>
                        {{ assetTypeLabel(row.key) }}
                      </div>
                    </td>
                    <td>
                      <el-input-number
                        v-model="row.years"
                        :min="1"
                        :max="50"
                        size="small"
                        controls-position="right"
                        class="depr-input"
                        :disabled="!authStore.isSuperAdmin"
                      />
                    </td>
                    <td>
                      <el-input-number
                        v-model="row.residual"
                        :min="0"
                        :max="50"
                        size="small"
                        controls-position="right"
                        class="depr-input"
                        :disabled="!authStore.isSuperAdmin"
                      />
                    </td>
                    <td>
                      <el-select v-model="row.method" size="small" style="width:130px" :disabled="!authStore.isSuperAdmin">
                        <el-option :label="t('cost.rates.deprTable.straightLine')" value="straight" />
                        <el-option :label="t('cost.rates.deprTable.accelerated')" value="accelerated" />
                      </el-select>
                    </td>
                    <td>
                      <el-radio-group v-model="row.strategy" :disabled="!authStore.isSuperAdmin">
                        <el-radio value="zero">{{ t('cost.rates.deprTable.zero') }}</el-radio>
                        <el-radio value="revalue">{{ t('cost.rates.deprTable.revalue') }}</el-radio>
                      </el-radio-group>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Power parameters -->
          <div class="form-group">
            <div class="fg-label">
              <span>{{ t('cost.rates.powerParams') }}</span>
            </div>
            <div class="form-row">
              <div class="field">
                <label>{{ t('cost.rates.electricityPrice') }}</label>
                <div class="field-inline">
                  <el-input-number
                    v-model="electricityPrice"
                    :precision="2"
                    :step="0.01"
                    :min="0"
                    size="small"
                    controls-position="right"
                    :disabled="!authStore.isSuperAdmin"
                  />
                  <span class="field-unit">{{ t('cost.rates.electricityUnit', { currency }) }}</span>
                </div>
              </div>
              <div class="field">
                <label>{{ t('cost.rates.pue') }}</label>
                <div class="field-inline">
                  <el-input-number
                    v-model="pue"
                    :precision="2"
                    :step="0.01"
                    :min="1"
                    :max="3"
                    size="small"
                    controls-position="right"
                    :disabled="!authStore.isSuperAdmin"
                  />
                </div>
              </div>
              <div class="field">
                <label>{{ t('cost.rates.loadFactor') }}</label>
                <div class="field-inline">
                  <el-input-number
                    v-model="loadFactor"
                    :precision="2"
                    :step="0.01"
                    :min="0"
                    :max="1"
                    size="small"
                    controls-position="right"
                    :disabled="!authStore.isSuperAdmin"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- Bandwidth & datacenter -->
          <div class="form-group">
            <div class="fg-label">
              <span>{{ t('cost.rates.bandwidthPrice') }} &amp; IDC</span>
            </div>
            <div class="form-row">
              <div class="field">
                <label>{{ t('cost.rates.bandwidthPrice') }}</label>
                <div class="field-inline">
                  <span class="field-currency">{{ symbol }}</span>
                  <el-input-number
                    v-model="bandwidthPrice"
                    :min="0"
                    size="small"
                    controls-position="right"
                    :disabled="!authStore.isSuperAdmin"
                  />
                  <span class="field-unit">{{ t('cost.rates.bandwidthUnit', { currency }) }}</span>
                </div>
              </div>
              <div class="field">
                <label>{{ t('cost.rates.rackCost') }}</label>
                <div class="field-inline">
                  <span class="field-currency">{{ symbol }}</span>
                  <el-input-number
                    v-model="rackCost"
                    :min="0"
                    size="small"
                    controls-position="right"
                    :disabled="!authStore.isSuperAdmin"
                  />
                  <span class="field-unit">{{ t('cost.rates.rackUnit', { currency }) }}</span>
                </div>
              </div>
              <div class="field">
                <label>{{ t('cost.rates.idcHosting') }}</label>
                <div class="field-inline">
                  <span class="field-currency">{{ symbol }}</span>
                  <el-input-number
                    v-model="idcHosting"
                    :min="0"
                    size="small"
                    controls-position="right"
                    :disabled="!authStore.isSuperAdmin"
                  />
                  <span class="field-unit">{{ t('cost.rates.idcUnit', { currency }) }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Currency & tax -->
          <div class="form-group form-group--last">
            <div class="fg-label">
              <span>{{ t('cost.rates.currency') }} &amp; {{ t('cost.rates.taxBasis') }}</span>
            </div>
            <div class="form-row">
              <div class="field">
                <label>{{ t('cost.rates.currency') }}</label>
                <el-select v-model="currency" style="width:160px" :disabled="!authStore.isSuperAdmin">
                  <el-option label="CNY" value="CNY" />
                  <el-option label="USD" value="USD" />
                </el-select>
              </div>
              <div class="field">
                <label>{{ t('cost.rates.taxBasis') }}</label>
                <el-radio-group v-model="taxBasis" :disabled="!authStore.isSuperAdmin">
                  <el-radio value="inclusive">{{ t('cost.rates.taxIncluded') }}</el-radio>
                  <el-radio value="exclusive">{{ t('cost.rates.taxExcluded') }}</el-radio>
                </el-radio-group>
              </div>
            </div>
          </div>

        </div>
      </div>

      <!-- ===== SECTION 2: 资源单价表 ===== -->
      <div class="sec-card">
        <div class="sec-head">
          <div class="sec-icon sec-icon--cyan">
            <el-icon :size="16"><PriceTag /></el-icon>
          </div>
          <div class="sec-head-text">
            <span class="sec-title">{{ t('cost.rates.priceBook') }}</span>
            <span class="sec-desc">{{ t('cost.rates.priceBookDesc') }}</span>
          </div>
        </div>
        <div class="sec-body sec-body--compact">
          <table class="price-tbl">
            <thead>
              <tr>
                <th>{{ t('cost.rates.resourceType') }}</th>
                <th>{{ t('cost.rates.billingUnit') }}</th>
                <th style="text-align:right">{{ t('cost.rates.standardPrice') }} ({{ symbol }})</th>
                <th style="text-align:right">{{ t('cost.rates.internalCost') }} ({{ symbol }})</th>
                <th style="width:80px;text-align:center">{{ t('cost.rates.enabled') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in priceBook" :key="row.key">
                <td><span class="price-name">{{ priceBookLabel(row.key) }}</span></td>
                <td><span class="price-unit">{{ priceBookUnit(row.unitKey) }}</span></td>
                <td style="text-align:right">
                  <el-input-number
                    v-model="row.stdPrice"
                    :precision="2"
                    :step="1"
                    :min="0"
                    size="small"
                    controls-position="right"
                    class="price-input"
                    :disabled="!authStore.isSuperAdmin"
                  />
                </td>
                <td style="text-align:right">
                  <el-input-number
                    v-model="row.costPrice"
                    :precision="2"
                    :step="1"
                    :min="0"
                    size="small"
                    controls-position="right"
                    class="price-input"
                    :disabled="!authStore.isSuperAdmin"
                  />
                </td>
                <td style="text-align:center">
                  <el-switch
                    v-model="row.enabled"
                    size="small"
                    :disabled="!authStore.isSuperAdmin"
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="sec-foot">
          <el-button size="small" :disabled="!authStore.isSuperAdmin">
            <el-icon><Plus /></el-icon>
            {{ t('cost.rates.addResourceType') }}
          </el-button>
          <span class="sec-foot-hint">{{ t('cost.rates.priceBookHint') }}</span>
        </div>
      </div>

      <!-- ===== SECTION 3: 分摊默认动因 ===== -->
      <div class="sec-card">
        <div class="sec-head">
          <div class="sec-icon sec-icon--green">
            <el-icon :size="16"><Share /></el-icon>
          </div>
          <div class="sec-head-text">
            <span class="sec-title">{{ t('cost.rates.allocDrivers') }}</span>
            <span class="sec-desc">{{ t('cost.rates.allocDriversDesc') }}</span>
          </div>
        </div>
        <div class="sec-body">
          <div class="alloc-grid">
            <div class="alloc-head">{{ t('cost.rates.deprTable.assetType') }}</div>
            <div class="alloc-head">{{ t('cost.rates.driverDescription') }}</div>
            <div class="alloc-head">{{ t('cost.rates.allocBasis') }}</div>
            <template v-for="(row, idx) in allocDrivers" :key="row.key">
              <div class="alloc-cell alloc-cell--name" :class="{ 'alloc-cell--fallback': row.isFallback }">
                {{ driverName(row.key) }}
              </div>
              <div class="alloc-cell alloc-cell--desc" :class="{ 'alloc-cell--fallback': row.isFallback }">
                {{ driverDesc(row.key) }}
              </div>
              <div class="alloc-cell" :class="{ 'alloc-cell--fallback': row.isFallback }">
                <el-select
                  v-model="row.basis"
                  size="small"
                  style="width:200px"
                  :disabled="!authStore.isSuperAdmin"
                >
                  <template v-if="row.isFallback">
                    <el-option :label="t('cost.rates.fallbackDesc')" value="asset_count" />
                    <el-option :label="t('cost.rates.allocBasisOptions.noAlloc')" value="no_alloc" />
                  </template>
                  <template v-else>
                    <el-option :label="t(`cost.rates.allocBasisOptions.${row.key === 'storage' ? 'byGbCapacity' : row.key === 'firewall' ? 'byProtectedAssets' : row.key === 'network' ? 'byPortUsage' : 'byBackendServices'}`)" :value="row.basis" />
                    <el-option :label="t('cost.rates.allocBasisOptions.byAssetCount')" value="asset_count" />
                    <el-option :label="t('cost.rates.allocBasisOptions.customWeight')" value="custom" />
                  </template>
                </el-select>
              </div>
            </template>
          </div>
        </div>
      </div>

      <!-- Save bar (sticky footer) -->
      <div class="save-bar">
        <span class="save-info">
          {{ t('cost.rates.lastSaved', { time: lastSavedTime || '—', user: lastSavedUser || '—' }) }}
          <span class="save-info-note"> · {{ t('cost.rates.saveNote') }}</span>
        </span>
        <el-button @click="handleCancel" :disabled="!authStore.isSuperAdmin">
          {{ t('cost.rates.cancelChanges') }}
        </el-button>
        <el-button
          type="primary"
          :loading="saving"
          :class="{ 'save-btn--success': showSaveSuccess }"
          :disabled="!authStore.isSuperAdmin"
          @click="handleSave"
        >
          <template v-if="showSaveSuccess">
            <el-icon><Check /></el-icon> {{ t('cost.rates.saved') }}
          </template>
          <template v-else>
            {{ t('cost.rates.saveSettings') }}
          </template>
        </el-button>
      </div>

    </div>
  </div>
</template>

<style scoped>
.cost-rates-page {
  padding-bottom: var(--space-12);
}

.cost-rates-container {
  max-width: 1040px;
}

/* ── Access banner ── */
.access-banner {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  background: var(--color-danger-soft, #FEF2F2);
  border: 1px solid rgba(220, 38, 38, 0.2);
  border-radius: var(--radius-md);
  padding: 10px var(--space-4);
  margin-bottom: var(--space-6);
  font-size: var(--fs-body);
  color: var(--color-danger, #9F1239);
}
.access-banner .ab-icon {
  color: var(--color-danger, #BE123C);
  flex-shrink: 0;
}
.access-banner strong {
  font-weight: 600;
}

/* ── Section card (same pattern as Settings.vue) ── */
.sec-card {
  background: var(--surface-base);
  border: var(--border-base);
  border-radius: var(--radius-lg);
  margin-bottom: var(--space-6);
  box-shadow: var(--shadow-subtle);
  transition: box-shadow var(--dur-base) var(--ease-out);
}
.sec-card:hover {
  box-shadow: var(--shadow-medium);
}
.sec-head {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-6);
  border-bottom: var(--border-base);
  background: linear-gradient(180deg, rgba(37, 99, 235, 0.02) 0%, transparent 100%);
}
.sec-head-text {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex: 1;
  min-width: 0;
}
.sec-title {
  font-size: var(--fs-h4);
  font-weight: 600;
  color: var(--neutral-900);
  white-space: nowrap;
}
.sec-desc {
  font-size: 12.5px;
  color: var(--neutral-500);
  margin-left: var(--space-2);
}
.sec-body {
  padding: var(--space-6);
}
.sec-body--compact {
  padding-top: 0;
  padding-bottom: 0;
}
.sec-icon {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.sec-icon--purple {
  background: #EDE9FE;
  color: #5B21B6;
}
.sec-icon--cyan {
  background: var(--color-info-soft, #ECFEFF);
  color: #0E7490;
}
.sec-icon--green {
  background: var(--color-success-soft, #F0FDF4);
  color: #15803D;
}
.sec-foot {
  padding: var(--space-4) var(--space-6);
  border-top: var(--border-base);
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.sec-foot-hint {
  font-size: var(--fs-caption);
  color: var(--neutral-500);
}

/* ── Form group within section ── */
.form-group {
  margin-bottom: var(--space-6);
}
.form-group:last-child,
.form-group--last {
  margin-bottom: 0;
}
.fg-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--neutral-500);
  text-transform: uppercase;
  letter-spacing: 0.07em;
  font-family: var(--font-mono);
  margin-bottom: var(--space-3);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.fg-label span {
  position: relative;
}
.fg-label::after {
  content: "";
  flex: 1;
  height: 1px;
  background: var(--neutral-200);
}
.form-row {
  display: flex;
  align-items: flex-end;
  gap: var(--space-6);
  flex-wrap: wrap;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.field label {
  font-size: var(--fs-caption);
  color: var(--neutral-500);
}
.field-inline {
  display: flex;
  align-items: center;
  gap: 6px;
}
.field-unit {
  font-size: var(--fs-caption);
  color: var(--neutral-500);
  white-space: nowrap;
}
.field-currency {
  color: var(--neutral-500);
  font-size: var(--fs-body);
  line-height: 1;
}

/* ── Depreciation table ── */
.depr-table-wrap {
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  overflow: hidden;
}
.depr-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--fs-body);
}
.depr-table thead th {
  text-align: left;
  font-weight: 600;
  color: var(--neutral-700);
  background: var(--neutral-50);
  border-bottom: 1px solid var(--neutral-200);
  padding: 8px 12px;
  font-size: 13px;
}
.depr-table tbody td {
  padding: 8px 12px;
  border-bottom: 1px solid var(--neutral-100);
  vertical-align: middle;
}
.depr-table tbody tr:last-child td {
  border-bottom: 0;
}
.asset-label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--fs-body);
  font-weight: 500;
  color: var(--neutral-900);
}
.asset-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.depr-input {
  width: 90px;
}

/* ── Price book table ── */
.price-tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--fs-body);
}
.price-tbl thead th {
  text-align: left;
  font-weight: 600;
  color: var(--neutral-700);
  background: var(--neutral-50);
  border-bottom: 1px solid var(--neutral-200);
  padding: 9px 14px;
  font-size: 13px;
}
.price-tbl tbody td {
  padding: 8px 14px;
  border-bottom: 1px solid var(--neutral-100);
  vertical-align: middle;
}
.price-tbl tbody tr:last-child td {
  border-bottom: 0;
}
.price-name {
  font-weight: 500;
  color: var(--neutral-900);
}
.price-unit {
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--neutral-500);
}
.price-input {
  width: 120px;
}

/* ── Allocation drivers grid ── */
.alloc-grid {
  display: grid;
  grid-template-columns: 180px 1fr 220px;
  gap: 0;
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  overflow: hidden;
}
.alloc-head {
  background: var(--neutral-50);
  font-size: 13px;
  font-weight: 600;
  color: var(--neutral-700);
  padding: 8px 16px;
  border-bottom: 1px solid var(--neutral-200);
}
.alloc-cell {
  padding: 10px 16px;
  border-bottom: 1px solid var(--neutral-100);
  display: flex;
  align-items: center;
  font-size: var(--fs-body);
}
.alloc-cell--name {
  font-weight: 500;
  color: var(--neutral-900);
}
.alloc-cell--desc {
  color: var(--neutral-500);
  font-size: var(--fs-caption);
}
.alloc-cell--fallback {
  background: var(--neutral-50);
  color: var(--neutral-500);
  font-weight: 400;
  font-style: italic;
}
.alloc-grid > *:nth-last-child(-n+3) {
  border-bottom: 0;
}

/* ── Save bar (sticky footer) ── */
.save-bar {
  position: sticky;
  bottom: 0;
  background: var(--surface-base);
  border: var(--border-base);
  border-radius: var(--radius-lg);
  padding: var(--space-4) var(--space-6);
  display: flex;
  align-items: center;
  gap: var(--space-3);
  z-index: 10;
  backdrop-filter: blur(12px);
  box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.06);
}
.save-info {
  font-size: var(--fs-caption);
  color: var(--neutral-500);
  font-family: var(--font-mono);
  margin-right: auto;
}
.save-info-note {
  color: var(--neutral-400);
}
.save-btn--success {
  background: var(--color-success, #16A34A) !important;
  border-color: var(--color-success, #16A34A) !important;
}
</style>
