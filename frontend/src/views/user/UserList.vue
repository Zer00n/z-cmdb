<script setup lang="ts">
/**
 * User management page
 * 2026 UI Redesign: upgraded user avatars and role badges, logic unchanged
 */
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchUsers, createUser, updateUser, disableUser } from '@/api/user'
import type { UserInfo } from '@/types/auth'
import type { UserCreateRequest, UserUpdateRequest } from '@/api/user'
import { useI18n } from 'vue-i18n'
import { useTranslatedLabels } from '@/composables/useTranslatedLabels'

const { t } = useI18n()
const { roleLabel } = useTranslatedLabels()

const loading = ref(false)
const tableData = ref<UserInfo[]>([])
const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const creating = ref(false)
const editing = ref(false)

const newUser = ref<UserCreateRequest>({
  username: '',
  password: '',
  role: 'admin',
  full_name: '',
  email: '',
})

const editUser = ref<{ id: number } & UserUpdateRequest>({
  id: 0,
  full_name: '',
  email: '',
  role: 'admin',
  status: 'active',
})

async function loadData() {
  loading.value = true
  try {
    tableData.value = await fetchUsers()
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  creating.value = true
  try {
    await createUser(newUser.value)
    ElMessage.success(t('user.createDialog.success'))
    showCreateDialog.value = false
    newUser.value = { username: '', password: '', role: 'admin', full_name: '', email: '' }
    loadData()
  } finally {
    creating.value = false
  }
}

function openEdit(user: UserInfo) {
  editUser.value = {
    id: user.id,
    full_name: user.full_name || '',
    email: user.email || '',
    role: user.role as 'super_admin' | 'admin' | 'auditor',
    status: user.status as 'active' | 'disabled',
  }
  showEditDialog.value = true
}

async function handleEdit() {
  editing.value = true
  try {
    const { id, ...data } = editUser.value
    await updateUser(id, data)
    ElMessage.success(t('user.editDialog.success'))
    showEditDialog.value = false
    loadData()
  } finally {
    editing.value = false
  }
}

async function handleDisable(user: UserInfo) {
  await ElMessageBox.confirm(
    t('user.disableConfirm', { username: user.username }),
    t('user.disableTitle'),
    { confirmButtonText: t('user.disableBtn'), cancelButtonText: t('common.cancel'), type: 'warning' }
  )
  await disableUser(user.id)
  ElMessage.success(t('user.disableSuccess'))
  loadData()
}

function roleBadgeClass(role: string): string {
  const map: Record<string, string> = {
    super_admin: 'is-danger',
    admin: 'is-info',
    auditor: 'is-neutral',
  }
  return map[role] || 'is-neutral'
}

function getInitials(user: UserInfo): string {
  const name = user.full_name || user.username
  return (name || '?').slice(0, 2).toUpperCase()
}

const activeCount = computed(() => tableData.value.filter((u) => u.status === 'active').length)
const auditorCount = computed(() => tableData.value.filter((u) => u.role === 'auditor').length)

onMounted(loadData)
</script>

<template>
  <div class="ui-page">
    <div class="ui-page-head">
      <div>
        <h1 class="ui-page-title">
          {{ t('user.title') }}
          <span class="ui-page-count">{{ t('user.total', { count: tableData.length }) }}</span>
        </h1>
        <p class="ui-page-subtitle">
          {{ t('user.summary', { active: activeCount, auditors: auditorCount }) }}
          <span v-if="auditorCount === 0" style="color: var(--color-warning); margin-left: 8px">
            {{ t('user.auditorWarning') }}
          </span>
        </p>
      </div>
      <div class="ui-page-actions">
        <el-button type="primary" @click="showCreateDialog = true">
          <el-icon><Plus /></el-icon>
          {{ t('user.newUser') }}
        </el-button>
      </div>
    </div>

    <div class="ui-table-card">
      <el-table v-loading="loading" :data="tableData" stripe style="width: 100%">
        <el-table-column prop="id" :label="t('user.columns.id')" width="80">
          <template #default="{ row }">
            <span class="ui-mono ui-mono-muted">#{{ row.id }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('user.columns.user')" min-width="220">
          <template #default="{ row }">
            <div class="user-cell">
              <div class="user-avatar" :class="row.role">{{ getInitials(row) }}</div>
              <div class="user-meta">
                <span class="user-name">{{ row.full_name || row.username }}</span>
                <span class="user-username">@{{ row.username }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="email" :label="t('user.columns.email')" min-width="200">
          <template #default="{ row }">
            <span class="ui-mono ui-mono-muted">{{ row.email || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="role" :label="t('user.columns.role')" width="140">
          <template #default="{ row }">
            <span class="ui-badge" :class="roleBadgeClass(row.role)">
              <span class="ui-badge-dot" />
              {{ roleLabel(row.role) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="status" :label="t('user.columns.status')" width="100">
          <template #default="{ row }">
            <span class="ui-badge" :class="row.status === 'active' ? 'is-success' : 'is-neutral'">
              <span class="ui-badge-dot" />
              {{ row.status === 'active' ? t('user.statusLabels.active') : t('user.statusLabels.disabled') }}
            </span>
          </template>
        </el-table-column>
        <el-table-column :label="t('user.columns.actions')" width="160">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEdit(row)">
              {{ t('user.edit') }}
            </el-button>
            <el-button
              v-if="row.status === 'active'"
              link
              type="danger"
              size="small"
              @click="handleDisable(row)"
            >
              {{ t('user.disable') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Create user dialog -->
    <el-dialog v-model="showCreateDialog" :title="t('user.createDialog.title')" width="480px">
      <el-form label-width="80px">
        <el-form-item :label="t('user.createDialog.username')" required>
          <el-input v-model="newUser.username" :placeholder="t('user.createDialog.usernamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('user.createDialog.password')" required>
          <el-input v-model="newUser.password" type="password" show-password :placeholder="t('user.createDialog.passwordPlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('user.createDialog.role')" required>
          <el-select v-model="newUser.role" style="width: 100%">
            <el-option :label="t('user.roles.admin')" value="admin" />
            <el-option :label="t('user.roles.auditor')" value="auditor" />
            <el-option :label="t('user.roles.superAdmin')" value="super_admin" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('user.createDialog.fullName')">
          <el-input v-model="newUser.full_name" :placeholder="t('user.createDialog.fullNamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('user.createDialog.email')">
          <el-input v-model="newUser.email" :placeholder="t('user.createDialog.emailPlaceholder')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">{{ t('user.createDialog.create') }}</el-button>
      </template>
    </el-dialog>

    <!-- Edit user dialog -->
    <el-dialog v-model="showEditDialog" :title="t('user.editDialog.title')" width="480px">
      <el-form label-width="80px">
        <el-form-item :label="t('user.createDialog.role')">
          <el-select v-model="editUser.role" style="width: 100%">
            <el-option :label="t('user.roles.admin')" value="admin" />
            <el-option :label="t('user.roles.auditor')" value="auditor" />
            <el-option :label="t('user.roles.superAdmin')" value="super_admin" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('user.createDialog.fullName')">
          <el-input v-model="editUser.full_name" :placeholder="t('user.createDialog.fullNamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('user.createDialog.email')">
          <el-input v-model="editUser.email" :placeholder="t('user.createDialog.emailPlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('user.columns.status')">
          <el-select v-model="editUser.status" style="width: 100%">
            <el-option :label="t('user.statusLabels.active')" value="active" />
            <el-option :label="t('common.disable')" value="disabled" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="editing" @click="handleEdit">{{ t('user.editDialog.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}
.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #FFFFFF;
  font-weight: 600;
  font-size: 11.5px;
  letter-spacing: 0.02em;
  flex-shrink: 0;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.2);
}
.user-avatar.super_admin {
  background: linear-gradient(135deg, #BE123C, #DC2626);
}
.user-avatar.admin {
  background: linear-gradient(135deg, #1E40AF, #3B82F6);
}
.user-avatar.auditor {
  background: linear-gradient(135deg, #475569, #64748B);
}
.user-meta {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}
.user-name {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--neutral-900);
}
.user-username {
  font-size: 11.5px;
  color: var(--neutral-500);
  font-family: var(--font-mono);
}
</style>
