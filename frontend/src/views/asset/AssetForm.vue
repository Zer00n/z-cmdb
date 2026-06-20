<script setup lang="ts">
/**
 * 资产新增/编辑表单页
 * 基于 Claude Design 06-asset-form.html 实现
 * 路由 /assets/create 为新增，/assets/:id/edit 为编辑
 */
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { createAsset, fetchAsset, updateAsset } from '@/api/asset'
import type { AssetCreateRequest, AssetUpdateRequest } from '@/types/asset'
import { osOptionGroups } from '@/constants/os-options'
import { getOsFieldMode, filterVisibleOsGroups } from './os-policy'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()

const formRef = ref<FormInstance>()
const loading = ref(false)
const submitting = ref(false)

// 判断是新增还是编辑
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

/** 是否为云服务器模式 */
const isCloudServer = computed(() => form.asset_type === 'cloud_server')

/** 网络区域选项：云服务器时显示云服务商，其他类型显示传统区域 */
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

/** 切换资产类型时，若网络区域与当前选项集不匹配则重置为默认值 */
watch(
  () => form.asset_type,
  (newType) => {
    const validValues = networkZoneOptions.value.map((o) => o.value)
    if (!validValues.includes(form.network_zone as string)) {
      form.network_zone = newType === 'cloud_server' ? 'aliyun' : 'intranet'
    }
  },
)

// 编辑模式：加载已有数据
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
        // 空字符串的 asset_no 改为 null（让后端自动生成）
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

onMounted(loadAsset)
</script>

<template>
  <div v-loading="loading" class="asset-form-page">
    <div class="container">
      <!-- 页头 -->
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
        <!-- 段 1：基础信息 -->
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

        <!-- 段 2：归属信息 -->
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

        <!-- 段 3：硬件信息（可选） -->
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

/* 段卡片 */
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

/* 等宽输入框 */
:deep(.mono-input .el-input__inner) {
  font-family: var(--font-mono);
  font-size: 13px;
}

/* 云服务商提示文字 */
.zone-hint {
  margin-left: var(--space-3);
  font-size: 12px;
  color: var(--neutral-400);
}
</style>
