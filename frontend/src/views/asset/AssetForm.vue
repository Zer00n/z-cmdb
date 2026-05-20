<script setup lang="ts">
/**
 * 资产新增/编辑表单页
 * 基于 Claude Design 06-asset-form.html 实现
 * 路由 /assets/create 为新增，/assets/:id/edit 为编辑
 */
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { createAsset, fetchAsset, updateAsset } from '@/api/asset'
import type { AssetCreateRequest, AssetUpdateRequest } from '@/types/asset'

const route = useRoute()
const router = useRouter()

const formRef = ref<FormInstance>()
const loading = ref(false)
const submitting = ref(false)

// 判断是新增还是编辑
const isEdit = computed(() => !!route.params.id)
const assetId = computed(() => Number(route.params.id) || 0)
const pageTitle = computed(() => isEdit.value ? '编辑资产' : '新增资产')

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

const rules: FormRules = {
  ip_address: [
    { required: true, message: '请输入 IP 地址', trigger: 'blur' },
    {
      pattern: /^(\d{1,3}\.){3}\d{1,3}$/,
      message: 'IPv4 格式不正确',
      trigger: 'blur',
    },
  ],
  asset_type: [{ required: true, message: '请选择资产类型', trigger: 'change' }],
  location: [{ required: true, message: '请输入物理位置', trigger: 'blur' }],
  owner: [{ required: true, message: '请输入负责人', trigger: 'blur' }],
  business_system: [{ required: true, message: '请输入业务系统', trigger: 'blur' }],
  importance: [{ required: true, message: '请选择重要性', trigger: 'change' }],
  network_zone: [{ required: true, message: '请选择网络区域', trigger: 'change' }],
}

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
        ElMessage.success('资产更新成功')
        router.push(`/assets/${assetId.value}`)
      } else {
        const data: AssetCreateRequest = { ...form }
        // 空字符串的 asset_no 改为 null（让后端自动生成）
        if (!data.asset_no) data.asset_no = null
        const asset = await createAsset(data)
        ElMessage.success('资产创建成功')
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
          <p class="ui-page-subtitle">所有带 <span style="color: var(--color-danger)">*</span> 字段为必填</p>
        </div>
        <div class="ui-page-actions">
          <el-button @click="handleCancel">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">
            <el-icon><Check /></el-icon>
            保存
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
            <span class="sec-title">基础信息</span>
            <el-tag size="small" type="danger" effect="plain">必填</el-tag>
          </div>
          <div class="sec-body">
            <el-form-item label="资产编号">
              <el-input
                v-model="form.asset_no"
                placeholder="留空则自动生成（CMDB-YYYYMMDD-NNN）"
                style="width: 360px"
                :disabled="isEdit"
              />
            </el-form-item>

            <el-form-item label="IP 地址" prop="ip_address">
              <el-input
                v-model="form.ip_address"
                placeholder="例如 192.168.1.100"
                style="width: 360px"
                class="mono-input"
              />
            </el-form-item>

            <el-form-item label="MAC 地址">
              <el-input
                v-model="form.mac_address"
                placeholder="例如 52:54:00:8a:3f:21"
                style="width: 360px"
                class="mono-input"
              />
            </el-form-item>

            <el-form-item label="主机名">
              <el-input
                v-model="form.hostname"
                placeholder="例如 web-prod-04"
                style="width: 360px"
              />
            </el-form-item>

            <el-form-item label="资产类型" prop="asset_type">
              <el-radio-group v-model="form.asset_type">
                <el-radio-button value="physical">物理服务器</el-radio-button>
                <el-radio-button value="virtual">虚拟机</el-radio-button>
                <el-radio-button value="network_device">网络设备</el-radio-button>
                <el-radio-button value="other">其他</el-radio-button>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="网络区域" prop="network_zone">
              <el-select v-model="form.network_zone" style="width: 360px">
                <el-option label="内网" value="intranet" />
                <el-option label="DMZ" value="dmz" />
                <el-option label="办公网" value="office" />
                <el-option label="管理网" value="management" />
                <el-option label="其他" value="other" />
              </el-select>
            </el-form-item>

            <el-form-item label="操作系统">
              <el-input v-model="form.os_info" placeholder="例如 Ubuntu 22.04 LTS" style="width: 360px" />
            </el-form-item>
          </div>
        </div>

        <!-- 段 2：归属信息 -->
        <div class="sec-card">
          <div class="sec-head">
            <span class="sec-num">02</span>
            <span class="sec-title">归属信息</span>
            <el-tag size="small" type="danger" effect="plain">必填</el-tag>
          </div>
          <div class="sec-body">
            <el-form-item label="物理位置" prop="location">
              <el-input v-model="form.location" placeholder="机房-机架-U位 或 办公区房间号" style="width: 360px" />
            </el-form-item>

            <el-form-item label="负责人" prop="owner">
              <el-input v-model="form.owner" placeholder="负责人姓名" style="width: 360px" />
            </el-form-item>

            <el-form-item label="业务系统" prop="business_system">
              <el-input v-model="form.business_system" placeholder="所属业务系统名称" style="width: 360px" />
            </el-form-item>

            <el-form-item label="重要性" prop="importance">
              <el-radio-group v-model="form.importance">
                <el-radio-button value="core">
                  <span style="color: var(--color-danger)">核心</span>
                </el-radio-button>
                <el-radio-button value="important">
                  <span style="color: var(--color-warning)">重要</span>
                </el-radio-button>
                <el-radio-button value="normal">普通</el-radio-button>
              </el-radio-group>
            </el-form-item>
          </div>
        </div>

        <!-- 段 3：硬件信息（可选） -->
        <div class="sec-card">
          <div class="sec-head">
            <span class="sec-num">03</span>
            <span class="sec-title">硬件与采购</span>
            <el-tag size="small" effect="plain">可选</el-tag>
          </div>
          <div class="sec-body">
            <el-form-item label="CPU">
              <el-input v-model="form.cpu" placeholder="例如 Intel Xeon E5-2680 v4" style="width: 360px" />
            </el-form-item>

            <el-form-item label="内存 (GB)">
              <el-input-number v-model="form.memory_gb" :min="0" :max="10240" placeholder="GB" />
            </el-form-item>

            <el-form-item label="磁盘 (GB)">
              <el-input-number v-model="form.disk_gb" :min="0" :max="1048576" placeholder="GB" />
            </el-form-item>

            <el-form-item label="采购日期">
              <el-date-picker
                v-model="form.purchase_date"
                type="date"
                placeholder="选择日期"
                value-format="YYYY-MM-DD"
                style="width: 180px"
              />
            </el-form-item>

            <el-form-item label="保修到期">
              <el-date-picker
                v-model="form.warranty_expiry"
                type="date"
                placeholder="选择日期"
                value-format="YYYY-MM-DD"
                style="width: 180px"
              />
            </el-form-item>

            <el-form-item label="备注">
              <el-input
                v-model="form.remark"
                type="textarea"
                :rows="4"
                placeholder="补充说明"
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
</style>
