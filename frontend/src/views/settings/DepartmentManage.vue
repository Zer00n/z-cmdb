<script setup lang="ts">
/**
 * Department Management page — /departments
 * CRUD for departments. Super-admin only (write ops).
 */
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  fetchDepartments, createDepartment, updateDepartment, deleteDepartment,
} from '@/api/cost'
import type { Department } from '@/api/cost'
import { useAuthStore } from '@/stores/auth'

const { t } = useI18n()
const authStore = useAuthStore()
const isAdmin = authStore.role === 'super_admin'

const loading = ref(true)
const departments = ref<Department[]>([])

// ── Dialog state ──────────────────────────────────────────
const showDialog = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const editingId = ref<number | null>(null)
const form = ref({ name: '', code: '' })
const saving = ref(false)

async function loadData() {
  loading.value = true
  try {
    departments.value = await fetchDepartments()
  } catch (e: any) {
    ElMessage.error(e?.message || t('settings.deptManage.loadError'))
  } finally {
    loading.value = false
  }
}

function openCreate() {
  dialogMode.value = 'create'
  editingId.value = null
  form.value = { name: '', code: '' }
  showDialog.value = true
}

function openEdit(dept: Department) {
  dialogMode.value = 'edit'
  editingId.value = dept.id
  form.value = { name: dept.name, code: dept.code }
  showDialog.value = true
}

async function handleSave() {
  if (!form.value.name.trim() || !form.value.code.trim()) {
    ElMessage.warning(t('settings.deptManage.nameCodeRequired'))
    return
  }
  saving.value = true
  try {
    if (dialogMode.value === 'create') {
      await createDepartment({ name: form.value.name.trim(), code: form.value.code.trim() })
      ElMessage.success(t('settings.deptManage.createSuccess'))
    } else {
      await updateDepartment(editingId.value!, { name: form.value.name.trim(), code: form.value.code.trim() })
      ElMessage.success(t('settings.deptManage.updateSuccess'))
    }
    showDialog.value = false
    loadData()
  } catch (e: any) {
    ElMessage.error(e?.message || t('settings.deptManage.saveError'))
  } finally {
    saving.value = false
  }
}

async function handleDelete(dept: Department) {
  try {
    await ElMessageBox.confirm(
      t('settings.deptManage.confirmDelete', { name: dept.name }),
      t('settings.deptManage.deleteTitle'),
      { type: 'warning' },
    )
    await deleteDepartment(dept.id)
    ElMessage.success(t('settings.deptManage.deleteSuccess'))
    loadData()
  } catch (e: any) {
    if (e === 'cancel' || e?.message === 'cancel') return
    ElMessage.error(e?.message || t('settings.deptManage.deleteError'))
  }
}

onMounted(loadData)
</script>

<template>
  <div class="ui-page">
    <!-- Page Header -->
    <div class="ui-page-head">
      <div>
        <h1 class="ui-page-title">{{ t('settings.deptManage.title') }}</h1>
        <p class="ui-page-sub">{{ t('settings.deptManage.subtitle') }}</p>
      </div>
      <div class="ui-page-actions" v-if="isAdmin">
        <el-button type="primary" @click="openCreate">{{ t('settings.deptManage.create') }}</el-button>
      </div>
    </div>

    <!-- Table -->
    <div class="ui-card dept-table-wrap">
      <el-table :data="departments" v-loading="loading" :header-cell-style="{ background: '#F8FAFC', color: '#334155', fontWeight: 600, fontSize: '13px' }">
        <el-table-column :label="t('settings.deptManage.colName')" min-width="200" prop="name">
          <template #default="{ row }">
            <span class="dept-name">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('settings.deptManage.colCode')" width="200" prop="code">
          <template #default="{ row }">
            <span class="dept-code">{{ row.code }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('settings.deptManage.colActions')" width="160" align="center" v-if="isAdmin">
          <template #default="{ row }">
            <el-link type="primary" :underline="false" @click="openEdit(row)">{{ t('settings.deptManage.edit') }}</el-link>
            <span class="dept-sep">|</span>
            <el-link type="danger" :underline="false" @click="handleDelete(row)">{{ t('settings.deptManage.delete') }}</el-link>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="!loading && departments.length === 0" class="dept-empty">
        {{ t('settings.deptManage.noData') }}
      </div>
    </div>

    <!-- Create / Edit Dialog -->
    <el-dialog v-model="showDialog" :title="dialogMode === 'create' ? t('settings.deptManage.createTitle') : t('settings.deptManage.editTitle')" width="440px">
      <el-form label-position="top">
        <el-form-item :label="t('settings.deptManage.colName')" required>
          <el-input v-model="form.name" :placeholder="t('settings.deptManage.namePlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('settings.deptManage.colCode')" required>
          <el-input v-model="form.code" :placeholder="t('settings.deptManage.codePlaceholder')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">{{ t('project.cancel') }}</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">{{ t('project.confirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.ui-page-sub {
  font-size: 13px;
  color: var(--neutral-500);
  margin-top: 4px;
}
.dept-table-wrap { overflow: hidden; }
.dept-name { font-weight: 600; color: var(--neutral-900); }
.dept-code { font-family: var(--font-mono); font-size: 13px; color: var(--neutral-600); }
.dept-sep { margin: 0 8px; color: var(--neutral-300); }
.dept-empty {
  padding: 40px;
  text-align: center;
  color: var(--neutral-400);
  font-size: 14px;
}
</style>
