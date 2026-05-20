<script setup lang="ts">
/**
 * 应用服务新增/编辑对话框
 */
import { ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { createAssetApp, updateAssetApp, fetchAppNames } from '@/api/asset-app'
import { APP_CATEGORIES } from '@/constants/app-categories'
import type { AssetApp, AssetAppCreateRequest, AssetAppUpdateRequest } from '@/types/asset-app'

const props = defineProps<{
  visible: boolean
  assetId: number
  editing: AssetApp | null
}>()

const emit = defineEmits<{
  (e: 'update:visible', val: boolean): void
  (e: 'success'): void
}>()

const isEdit = computed(() => !!props.editing)
const title = computed(() => (isEdit.value ? '编辑应用' : '新增应用'))

// 表单数据
const form = ref({
  name: '',
  version: '',
  category: '',
  port: null as number | null,
  protocol: 'tcp',
  install_path: '',
  config_path: '',
  notes: '',
})

// autocomplete 数据
const appNames = ref<string[]>([])
const appNameSuggestions = computed(() => {
  const q = form.value.name.toLowerCase()
  if (!q) return appNames.value.map((n) => ({ value: n }))
  return appNames.value
    .filter((n) => n.toLowerCase().includes(q))
    .map((n) => ({ value: n }))
})

const submitting = ref(false)

// 监听 visible 变化，初始化表单
watch(
  () => props.visible,
  async (val) => {
    if (val) {
      if (props.editing) {
        form.value = {
          name: props.editing.name,
          version: props.editing.version || '',
          category: props.editing.category || '',
          port: props.editing.port,
          protocol: props.editing.protocol || 'tcp',
          install_path: props.editing.install_path || '',
          config_path: props.editing.config_path || '',
          notes: props.editing.notes || '',
        }
      } else {
        form.value = {
          name: '',
          version: '',
          category: '',
          port: null,
          protocol: 'tcp',
          install_path: '',
          config_path: '',
          notes: '',
        }
      }
      // 加载 autocomplete 数据
      try {
        appNames.value = await fetchAppNames()
      } catch {
        // 静默失败
      }
    }
  }
)

function handleClose() {
  emit('update:visible', false)
}

async function handleSubmit() {
  if (!form.value.name.trim()) {
    ElMessage.warning('应用名称不能为空')
    return
  }

  submitting.value = true
  try {
    if (isEdit.value && props.editing) {
      const data: AssetAppUpdateRequest = {
        name: form.value.name.trim(),
        version: form.value.version.trim() || null,
        category: form.value.category || null,
        port: form.value.port || null,
        protocol: form.value.port ? form.value.protocol : null,
        install_path: form.value.install_path.trim() || null,
        config_path: form.value.config_path.trim() || null,
        notes: form.value.notes.trim() || null,
      }
      await updateAssetApp(props.assetId, props.editing.id, data)
      ElMessage.success('应用已更新')
    } else {
      const data: AssetAppCreateRequest = {
        name: form.value.name.trim(),
        version: form.value.version.trim() || null,
        category: form.value.category || null,
        port: form.value.port || null,
        protocol: form.value.port ? form.value.protocol : null,
        install_path: form.value.install_path.trim() || null,
        config_path: form.value.config_path.trim() || null,
        notes: form.value.notes.trim() || null,
      }
      await createAssetApp(props.assetId, data)
      ElMessage.success('应用已添加')
    }
    emit('success')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="visible"
    :title="title"
    width="560px"
    @close="handleClose"
    destroy-on-close
  >
    <el-form :model="form" label-width="100px" label-position="right">
      <el-form-item label="应用名称" required>
        <el-autocomplete
          v-model="form.name"
          :fetch-suggestions="(_q: string, cb: Function) => cb(appNameSuggestions)"
          placeholder="如 nginx、mysql-server、tomcat"
          style="width: 100%"
          clearable
        />
      </el-form-item>

      <el-form-item label="版本号">
        <el-input v-model="form.version" placeholder="如 1.24.0、8.0.36" clearable />
      </el-form-item>

      <el-form-item label="应用大类">
        <el-select
          v-model="form.category"
          placeholder="选择或输入大类"
          filterable
          allow-create
          clearable
          style="width: 100%"
        >
          <el-option
            v-for="cat in APP_CATEGORIES"
            :key="cat.value"
            :label="cat.label"
            :value="cat.value"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="监听端口">
        <div style="display: flex; gap: 8px; width: 100%">
          <el-input-number
            v-model="form.port"
            :min="1"
            :max="65535"
            placeholder="端口号"
            controls-position="right"
            style="flex: 1"
          />
          <el-select
            v-if="form.port"
            v-model="form.protocol"
            style="width: 100px"
          >
            <el-option label="TCP" value="tcp" />
            <el-option label="UDP" value="udp" />
          </el-select>
        </div>
      </el-form-item>

      <el-form-item label="安装路径">
        <el-input v-model="form.install_path" placeholder="如 /usr/local/nginx" clearable />
      </el-form-item>

      <el-form-item label="配置路径">
        <el-input v-model="form.config_path" placeholder="如 /etc/nginx/nginx.conf" clearable />
      </el-form-item>

      <el-form-item label="备注">
        <el-input
          v-model="form.notes"
          type="textarea"
          :rows="3"
          placeholder="自由备注"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">
        {{ isEdit ? '保存' : '添加' }}
      </el-button>
    </template>
  </el-dialog>
</template>
