<script setup lang="ts">
/**
 * Asset create/edit form page
 * Based on Claude Design 06-asset-form.html
 * Route /assets/create for new, /assets/:id/edit for editing
 */
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { createAsset, fetchAsset, updateAsset } from '@/api/asset'
import { fetchDepartments, type Department } from '@/api/cost'
import type { AssetCreateRequest, AssetUpdateRequest } from '@/types/asset'
import { osOptionGroups } from '@/constants/os-options'
import { getOsFieldMode, filterVisibleOsGroups } from './os-policy'
import { useFeatureStore } from '@/stores/feature'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const featureStore = useFeatureStore()
const departments = ref<Department[]>([])

const formRef = ref<FormInstance>()
const loading = ref(false)
const submitting = ref(false)

// Determine if creating or editing
const isEdit = computed(() => !!route.params.id)
const assetId = computed(() => Number(route.params.id) || 0)
const pageTitle = computed(() => isEdit.value ? t('asset.form.editTitle') : t('asset.form.createTitle'))

const form = reactive<AssetCreateRequest>({
  asset_no: '',
  ip_address: '',
  mac_address: '',
  hostname: '',
  asset_type: 'virtual',
  os_info: '',
  location: '',
  owner: '',
  business_system: '',
  importance: 'normal',
  network_zone: 'intranet',
  cpu: '',
  memory_gb: undefined,
  disk_gb: undefined,
  purchase_date: '',
  warranty_expiry: '',
  remark: '',
  source: 'manual',
  // V0.4 Cost fields
  purchase_price: undefined,
  depreciation_months: undefined,
  residual_rate: undefined,
  depreciation_method: 'straight_line',
  end_of_life_strategy: 'zero',
  revalue_amount: undefined,
  revalue_months: undefined,
  billing_mode: 'cost',
  responsible_dept_id: undefined,
})

const rules = computed<FormRules>(() => ({
  ip_address: [
    { required: true, message: t('asset.form.validation.ipRequired'), trigger: 'blur' },
    {
      pattern: /^(\d{1,3}\.){3}\d{1,3}$/,
      message: t('asset.form.validation.ipFormat'),
      trigger: 'blur',
    },
  ],
  asset_type: [{ required: true, message: t('asset.form.validation.typeRequired'), trigger: 'change' }],
  location: [{ required: true, message: t('asset.form.validation.locationRequired'), trigger: 'blur' }],
  owner: [{ required: true, message: t('asset.form.validation.ownerRequired'), trigger: 'blur' }],
  business_system: [{ required: true, message: t('asset.form.validation.businessSystemRequired'), trigger: 'blur' }],
  importance: [{ required: true, message: t('asset.form.validation.importanceRequired'), trigger: 'change' }],
  network_zone: [{ required: true, message: t('asset.form.validation.networkZoneRequired'), trigger: 'change' }],
}))

const osFieldMode = computed(() => getOsFieldMode(form.asset_type))
const visibleOsGroups = computed(() => filterVisibleOsGroups(form.asset_type, osOptionGroups))

/** Whether cloud server mode is active */
const isCloudServer = computed(() => form.asset_type === 'cloud_server')

/** Network zone options: cloud providers for cloud servers, traditional zones for others */
const networkZoneOptions = computed(() => {
  if (isCloudServer.value) {
    return [
      { label: t('constants.zones.aliyun'), value: 'aliyun' },
      { label: t('constants.zones.tencent'), value: 'tencent' },
      { label: t('constants.zones.huawei'), value: 'huawei' },
      { label: 'AWS', value: 'aws' },
      { label: 'Azure', value: 'azure' },
      { label: 'Google Cloud', value: 'gcp' },
      { label: t('constants.zones.other_cloud'), value: 'other_cloud' },
    ]
  }
  return [
    { label: t('constants.zones.intranet'), value: 'intranet' },
    { label: 'DMZ', value: 'dmz' },
    { label: t('constants.zones.office'), value: 'office' },
    { label: t('constants.zones.management'), value: 'management' },
    { label: t('constants.zones.other'), value: 'other' },
  ]
})

/** Reset network zone to default if it doesn't match the current option set when switching asset type */
watch(
  () => form.asset_type,
  (newType) => {
    const validValues = networkZoneOptions.value.map((o) => o.value)
    if (!validValues.includes(form.network_zone as string)) {
      form.network_zone = newType === 'cloud_server' ? 'aliyun' : 'intranet'
    }
  },
)

// Edit mode: load existing data
async function loadAsset() {
  if (!isEdit.value) return
  loading.value = true
  try {
    const asset = await fetchAsset(assetId.value)
    Object.assign(form, {
      asset_no: asset.asset_no,
      ip_address: asset.ip_address,
      mac_address: asset.mac_address || '',
      hostname: asset.hostname || '',
      asset_type: asset.asset_type,
      os_info: asset.os_info || '',
      location: asset.location,
      owner: asset.owner,
      business_system: asset.business_system,
      importance: asset.importance,
      network_zone: asset.network_zone,
      cpu: asset.cpu || '',
      memory_gb: asset.memory_gb ?? undefined,
      disk_gb: asset.disk_gb ?? undefined,
      purchase_date: asset.purchase_date || '',
      warranty_expiry: asset.warranty_expiry || '',
      remark: asset.remark || '',
      // V0.4 Cost fields
      purchase_price: asset.purchase_price ?? undefined,
      depreciation_months: asset.depreciation_months ?? undefined,
      residual_rate: asset.residual_rate ?? undefined,
      depreciation_method: asset.depreciation_method || 'straight_line',
      end_of_life_strategy: asset.end_of_life_strategy || 'zero',
      revalue_amount: asset.revalue_amount ?? undefined,
      revalue_months: asset.revalue_months ?? undefined,
      billing_mode: asset.billing_mode || 'cost',
      responsible_dept_id: asset.responsible_dept_id ?? undefined,
    })
  } finally {
    loading.value = false
  }
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      if (isEdit.value) {
        const data: AssetUpdateRequest = { ...form }
        await updateAsset(assetId.value, data)
        ElMessage.success(t('asset.form.success.updated'))
        router.push(`/assets/${assetId.value}`)
      } else {
        const data: AssetCreateRequest = { ...form }
        // Convert empty asset_no to null (let backend auto-generate)
        if (!data.asset_no) data.asset_no = null
        const asset = await createAsset(data)
        ElMessage.success(t('asset.form.success.created'))
        router.push(`/assets/${asset.id}`)
      }
    } finally {
      submitting.value = false
    }
  })
}

function handleCancel() {
  router.back()
}

onMounted(async () => {
  await loadAsset()
  if (featureStore.costAccounting) {
    try { departments.value = await fetchDepartments() } catch { /* ignore */ }
  }
})
</script>

<template>
  <div v-loading="loading" class="asset-form-page">
    <div class="container">
      <!-- Page header -->
      <div class="ui-page-head" style="margin-bottom: var(--space-6)">
        <div>
          <h1 class="ui-page-title">{{ pageTitle }}</h1>
          <p class="ui-page-subtitle" v-html="t('asset.form.requiredHint')"></p>
        </div>
        <div class="ui-page-actions">
          <el-button @click="handleCancel">{{ t('asset.form.cancel') }}</el-button>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">
            <el-icon><Check /></el-icon>
            {{ t('asset.form.save') }}
          </el-button>
        </div>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="120px"
        label-position="right"
      >
        <!-- Section 1: Basic information -->
        <div class="sec-card">
          <div class="sec-head">
            <span class="sec-num">01</span>
            <span class="sec-title">{{ t('asset.form.sections.basic') }}</span>
            <el-tag size="small" type="danger" effect="plain">{{ t('asset.form.sections.required') }}</el-tag>
          </div>
          <div class="sec-body">
            <el-form-item :label="t('asset.form.fields.assetNo')">
              <el-input
                v-model="form.asset_no"
                :placeholder="t('asset.form.fields.assetNoPlaceholder')"
                style="width: 360px"
                :disabled="isEdit"
              />
            </el-form-item>

            <el-form-item :label="t('asset.form.fields.ip')" prop="ip_address">
              <el-input
                v-model="form.ip_address"
                :placeholder="t('asset.form.fields.ipPlaceholder')"
                style="width: 360px"
                class="mono-input"
              />
            </el-form-item>

            <el-form-item :label="t('asset.form.fields.mac')">
              <el-input
                v-model="form.mac_address"
                :placeholder="t('asset.form.fields.macPlaceholder')"
                style="width: 360px"
                class="mono-input"
              />
            </el-form-item>

            <el-form-item :label="t('asset.form.fields.hostname')">
              <el-input
                v-model="form.hostname"
                :placeholder="t('asset.form.fields.hostnamePlaceholder')"
                style="width: 360px"
              />
            </el-form-item>

            <el-form-item :label="t('asset.form.fields.assetType')" prop="asset_type">
              <el-radio-group v-model="form.asset_type">
                <el-radio-button value="physical">{{ t('asset.form.types.physical') }}</el-radio-button>
                <el-radio-button value="virtual">{{ t('asset.form.types.virtual') }}</el-radio-button>
                <el-radio-button value="cloud_server">{{ t('asset.form.types.cloudServer') }}</el-radio-button>
                <el-radio-button value="network_device">{{ t('asset.form.types.networkDevice') }}</el-radio-button>
                <el-radio-button value="other">{{ t('asset.form.types.other') }}</el-radio-button>
              </el-radio-group>
            </el-form-item>

            <el-form-item :label="t('asset.form.fields.networkZone')" prop="network_zone">
              <el-select v-model="form.network_zone" style="width: 360px">
                <el-option
                  v-for="opt in networkZoneOptions"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>
              <span v-if="isCloudServer" class="zone-hint">{{ t('asset.form.fields.cloudHint') }}</span>
            </el-form-item>

            <el-form-item :label="t('asset.form.fields.os')">
              <el-select
                v-if="osFieldMode === 'select'"
                v-model="form.os_info"
                :placeholder="t('asset.form.fields.osSelectPlaceholder')"
                style="width: 360px"
                filterable
                allow-create
                clearable
                default-first-option
              >
                <el-option-group
                  v-for="group in visibleOsGroups"
                  :key="group.label"
                  :label="group.label"
                >
                  <el-option
                    v-for="opt in group.options"
                    :key="opt.value"
                    :label="opt.label"
                    :value="opt.value"
                  />
                </el-option-group>
              </el-select>
              <el-input
                v-else
                v-model="form.os_info"
                :placeholder="t('asset.form.fields.osInputPlaceholder')"
                style="width: 360px"
              />
            </el-form-item>
          </div>
        </div>

        <!-- Section 2: Ownership information -->
        <div class="sec-card">
          <div class="sec-head">
            <span class="sec-num">02</span>
            <span class="sec-title">{{ t('asset.form.sections.ownership') }}</span>
            <el-tag size="small" type="danger" effect="plain">{{ t('asset.form.sections.required') }}</el-tag>
          </div>
          <div class="sec-body">
            <el-form-item :label="t('asset.form.fields.location')" prop="location">
              <el-input v-model="form.location" :placeholder="t('asset.form.fields.locationPlaceholder')" style="width: 360px" />
            </el-form-item>

            <el-form-item :label="t('asset.form.fields.owner')" prop="owner">
              <el-input v-model="form.owner" :placeholder="t('asset.form.fields.ownerPlaceholder')" style="width: 360px" />
            </el-form-item>

            <el-form-item :label="t('asset.form.fields.businessSystem')" prop="business_system">
              <el-input v-model="form.business_system" :placeholder="t('asset.form.fields.businessSystemPlaceholder')" style="width: 360px" />
            </el-form-item>

            <el-form-item :label="t('asset.form.fields.importance')" prop="importance">
              <el-radio-group v-model="form.importance">
                <el-radio-button value="core">
                  <span style="color: var(--color-danger)">{{ t('asset.form.importanceLevels.core') }}</span>
                </el-radio-button>
                <el-radio-button value="important">
                  <span style="color: var(--color-warning)">{{ t('asset.form.importanceLevels.important') }}</span>
                </el-radio-button>
                <el-radio-button value="normal">{{ t('asset.form.importanceLevels.normal') }}</el-radio-button>
              </el-radio-group>
            </el-form-item>
          </div>
        </div>

        <!-- Section 3: Hardware information (optional) -->
        <div class="sec-card">
          <div class="sec-head">
            <span class="sec-num">03</span>
            <span class="sec-title">{{ t('asset.form.sections.hardware') }}</span>
            <el-tag size="small" effect="plain">{{ t('asset.form.sections.optional') }}</el-tag>
          </div>
          <div class="sec-body">
            <el-form-item :label="t('asset.form.fields.cpu')">
              <el-input v-model="form.cpu" :placeholder="t('asset.form.fields.cpuPlaceholder')" style="width: 360px" />
            </el-form-item>

            <el-form-item :label="t('asset.form.fields.memory')">
              <el-input-number v-model="form.memory_gb" :min="0" :max="10240" placeholder="GB" />
            </el-form-item>

            <el-form-item :label="t('asset.form.fields.disk')">
              <el-input-number v-model="form.disk_gb" :min="0" :max="1048576" placeholder="GB" />
            </el-form-item>

            <el-form-item :label="t('asset.form.fields.purchaseDate')">
              <el-date-picker
                v-model="form.purchase_date"
                type="date"
                :placeholder="t('asset.form.fields.datePlaceholder')"
                value-format="YYYY-MM-DD"
                style="width: 180px"
              />
            </el-form-item>

            <el-form-item :label="t('asset.form.fields.warrantyExpiry')">
              <el-date-picker
                v-model="form.warranty_expiry"
                type="date"
                :placeholder="t('asset.form.fields.datePlaceholder')"
                value-format="YYYY-MM-DD"
                style="width: 180px"
              />
            </el-form-item>

            <el-form-item :label="t('asset.form.fields.remark')">
              <el-input
                v-model="form.remark"
                type="textarea"
                :rows="4"
                :placeholder="t('asset.form.fields.remarkPlaceholder')"
                style="width: 100%; max-width: 720px"
              />
            </el-form-item>
          </div>
        </div>

        <!-- V0.4 Section 4: Cost information (controlled by featureStore) -->
        <div v-if="featureStore.costAccounting" class="sec-card">
          <div class="sec-head">
            <span class="sec-num">04</span>
            <span class="sec-title">{{ t('cost.assetForm.sectionTitle') }}</span>
            <el-tag size="small" effect="plain">{{ t('asset.form.sections.optional') }}</el-tag>
          </div>
          <div class="sec-body">
            <el-form-item :label="t('cost.assetForm.purchasePrice')">
              <el-input-number
                v-model="form.purchase_price"
                :min="0"
                :precision="2"
                :placeholder="t('cost.assetForm.purchasePricePlaceholder')"
                style="width: 240px"
              />
              <span class="zone-hint">CNY</span>
            </el-form-item>

            <el-form-item :label="t('cost.assetForm.depreciationMonths')">
              <el-input-number
                v-model="form.depreciation_months"
                :min="1"
                :max="1200"
                :placeholder="t('cost.assetForm.depreciationMonthsPlaceholder')"
                style="width: 240px"
              />
            </el-form-item>

            <el-form-item :label="t('cost.assetForm.residualRate')">
              <el-input-number
                v-model="form.residual_rate"
                :min="0"
                :max="1"
                :step="0.01"
                :precision="2"
                :placeholder="t('cost.assetForm.residualRatePlaceholder')"
                style="width: 240px"
              />
            </el-form-item>

            <el-form-item :label="t('cost.assetForm.depreciationMethod')">
              <el-select v-model="form.depreciation_method" style="width: 240px">
                <el-option :label="t('cost.rates.deprTable.straightLine')" value="straight_line" />
                <el-option :label="t('cost.rates.deprTable.accelerated')" value="accelerated" />
              </el-select>
            </el-form-item>

            <el-form-item :label="t('cost.assetForm.eolStrategy')">
              <el-radio-group v-model="form.end_of_life_strategy">
                <el-radio value="zero">{{ t('cost.rates.deprTable.zero') }}</el-radio>
                <el-radio value="revalue">{{ t('cost.rates.deprTable.revalue') }}</el-radio>
              </el-radio-group>
            </el-form-item>

            <!-- Revalue fields (shown only when end-of-life strategy is revalue) -->
            <template v-if="form.end_of_life_strategy === 'revalue'">
              <el-form-item :label="t('cost.assetForm.revalueAmount')">
                <el-input-number
                  v-model="form.revalue_amount"
                  :min="0"
                  :precision="2"
                  :placeholder="t('cost.assetForm.revalueAmountPlaceholder')"
                  style="width: 240px"
                />
              </el-form-item>
              <el-form-item :label="t('cost.assetForm.revalueMonths')">
                <el-input-number
                  v-model="form.revalue_months"
                  :min="1"
                  :max="120"
                  :placeholder="t('cost.assetForm.revalueMonthsPlaceholder')"
                  style="width: 240px"
                />
              </el-form-item>
            </template>

            <el-form-item :label="t('cost.assetForm.billingMode')">
              <el-radio-group v-model="form.billing_mode">
                <el-radio value="cost">{{ t('cost.assetForm.billingModeCost') }}</el-radio>
                <el-radio value="unit_price">{{ t('cost.assetForm.billingModeUnitPrice') }}</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item :label="t('cost.assetForm.responsibleDept')">
              <el-select
                v-model="form.responsible_dept_id"
                :placeholder="t('cost.assetForm.selectDept')"
                clearable
                style="width: 360px"
              >
                <el-option
                  v-for="dept in departments"
                  :key="dept.id"
                  :label="dept.name"
                  :value="dept.id"
                />
              </el-select>
            </el-form-item>
          </div>
        </div>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.asset-form-page {
  padding-bottom: var(--space-12);
}

.container {
  max-width: 960px;
}

/* Section card */
.sec-card {
  background: var(--surface-base);
  border: var(--border-base);
  border-radius: var(--radius-lg);
  margin-bottom: var(--space-4);
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
.sec-num {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-md);
  background: var(--accent-gradient);
  color: #FFFFFF;
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 2px 6px -1px rgba(37, 99, 235, 0.4);
}
.sec-title {
  font-size: var(--fs-h4);
  font-weight: 600;
  color: var(--neutral-900);
}
.sec-body {
  padding: var(--space-6);
}

/* Monospace input */
:deep(.mono-input .el-input__inner) {
  font-family: var(--font-mono);
  font-size: 13px;
}

/* Cloud provider hint text */
.zone-hint {
  margin-left: var(--space-3);
  font-size: 12px;
  color: var(--neutral-400);
}
</style>
