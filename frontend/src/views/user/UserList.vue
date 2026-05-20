<script setup lang="ts">
/**
 * 用户管理页
 * 复用列表模板结构
 */
import { ref, onMounted } from 'vue'
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

onMounted(loadData)
</script>

<template>
  <div class="user-list-page">
    <div class="page-head">
      <h1>用户管理</h1>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>
        新增用户
      </el-button>
    </div>

    <div class="table-card">
      <el-table v-loading="loading" :data="tableData" stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="用户名" width="140" />
        <el-table-column prop="full_name" label="姓名" width="120" />
        <el-table-column prop="email" label="邮箱" width="200" />
        <el-table-column prop="role" label="角色" width="120">
          <template #default="{ row }">
            <el-tag size="small" :type="row.role === 'super_admin' ? 'danger' : row.role === 'auditor' ? 'info' : ''">
              {{ roleLabel(row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
              {{ row.status === 'active' ? '正常' : '已禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140">
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
          <el-input v-model="newUser.password" type="password" show-password placeholder="至少12位，含大小写数字符号" />
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
.user-list-page { display: flex; flex-direction: column; gap: var(--space-4); }
.page-head { display: flex; align-items: flex-end; justify-content: space-between; }
.page-head h1 { margin: 0; font-size: var(--fs-h2); color: var(--neutral-900); font-weight: 600; }
.table-card { background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: var(--radius-lg); overflow: hidden; }
</style>
