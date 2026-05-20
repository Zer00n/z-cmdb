<script setup lang="ts">
/**
 * 用户管理页
 * 2026 UI Redesign：升级用户头像与角色徽标，逻辑保持不变
 */
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchUsers, createUser, updateUser, disableUser } from '@/api/user'
import type { UserInfo } from '@/types/auth'
import type { UserCreateRequest, UserUpdateRequest } from '@/api/user'

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
    ElMessage.success('用户创建成功')
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
    ElMessage.success('用户信息已更新')
    showEditDialog.value = false
    loadData()
  } finally {
    editing.value = false
  }
}

async function handleDisable(user: UserInfo) {
  await ElMessageBox.confirm(
    `确认禁用用户 ${user.username}？禁用后该用户将无法登录。`,
    '禁用确认',
    { confirmButtonText: '确认禁用', cancelButtonText: '取消', type: 'warning' }
  )
  await disableUser(user.id)
  ElMessage.success('用户已禁用')
  loadData()
}

function roleLabel(role: string): string {
  const map: Record<string, string> = { super_admin: '超级管理员', admin: '管理员', auditor: '审计员' }
  return map[role] || role
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
          用户管理
          <span class="ui-page-count">共 <b>{{ tableData.length }}</b> 项</span>
        </h1>
        <p class="ui-page-subtitle">
          活跃 {{ activeCount }} 人 · 审计员 {{ auditorCount }} 人
          <span v-if="auditorCount === 0" style="color: var(--color-warning); margin-left: 8px">
            ⚠ 必须创建至少一个审计员才能解锁完整功能
          </span>
        </p>
      </div>
      <div class="ui-page-actions">
        <el-button type="primary" @click="showCreateDialog = true">
          <el-icon><Plus /></el-icon>
          新增用户
        </el-button>
      </div>
    </div>

    <div class="ui-table-card">
      <el-table v-loading="loading" :data="tableData" stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="80">
          <template #default="{ row }">
            <span class="ui-mono ui-mono-muted">#{{ row.id }}</span>
          </template>
        </el-table-column>
        <el-table-column label="用户" min-width="220">
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
        <el-table-column prop="email" label="邮箱" min-width="200">
          <template #default="{ row }">
            <span class="ui-mono ui-mono-muted">{{ row.email || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="role" label="角色" width="140">
          <template #default="{ row }">
            <span class="ui-badge" :class="roleBadgeClass(row.role)">
              <span class="ui-badge-dot" />
              {{ roleLabel(row.role) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <span class="ui-badge" :class="row.status === 'active' ? 'is-success' : 'is-neutral'">
              <span class="ui-badge-dot" />
              {{ row.status === 'active' ? '正常' : '已禁用' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEdit(row)">
              编辑
            </el-button>
            <el-button
              v-if="row.status === 'active'"
              link
              type="danger"
              size="small"
              @click="handleDisable(row)"
            >
              禁用
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 新增用户弹窗 -->
    <el-dialog v-model="showCreateDialog" title="新增用户" width="480px">
      <el-form label-width="80px">
        <el-form-item label="用户名" required>
          <el-input v-model="newUser.username" placeholder="登录用户名" />
        </el-form-item>
        <el-form-item label="密码" required>
          <el-input v-model="newUser.password" type="password" show-password placeholder="至少 12 位，含大小写数字符号" />
        </el-form-item>
        <el-form-item label="角色" required>
          <el-select v-model="newUser.role" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="审计员" value="auditor" />
            <el-option label="超级管理员" value="super_admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="newUser.full_name" placeholder="真实姓名" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="newUser.email" placeholder="邮箱地址" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 编辑用户弹窗 -->
    <el-dialog v-model="showEditDialog" title="编辑用户" width="480px">
      <el-form label-width="80px">
        <el-form-item label="角色">
          <el-select v-model="editUser.role" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="审计员" value="auditor" />
            <el-option label="超级管理员" value="super_admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="editUser.full_name" placeholder="真实姓名" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="editUser.email" placeholder="邮箱地址" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="editUser.status" style="width: 100%">
            <el-option label="正常" value="active" />
            <el-option label="禁用" value="disabled" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" :loading="editing" @click="handleEdit">保存</el-button>
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
