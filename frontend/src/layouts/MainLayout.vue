<script setup lang="ts">
/**
 * 主框架布局
 * 基于 Claude Design 03-layout.html 实现
 * 顶部栏 + 可折叠侧边栏 + 主内容区
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { logout } from '@/api/auth'
import AppSidebar from '@/components/common/AppSidebar.vue'
import ChangePasswordDialog from '@/components/common/ChangePasswordDialog.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const collapsed = ref(false)
const showChangePwd = ref(false)

// 面包屑：取当前路由 meta.title
const pageTitle = computed(() => (route.meta.title as string) || '')

// 用户头像首字母
const avatarText = computed(() => {
  const name = authStore.userInfo?.full_name || authStore.userInfo?.username || ''
  return name.slice(0, 2).toUpperCase()
})

// 首次登录或密码过期时强制弹出改密对话框
onMounted(() => {
  if (authStore.mustChangePassword) {
    showChangePwd.value = true
  }
})

// 如果用户关闭改密对话框但仍需改密，强制登出
// 但如果是改密成功后关闭的（mustChangePassword 已被重置），则不登出
watch(showChangePwd, (newVal) => {
  if (!newVal && authStore.mustChangePassword) {
    // 用户未改密就关闭了对话框 → 强制登出
    authStore.clearAuth()
    router.push('/login')
  }
})

async function handleLogout() {
  await ElMessageBox.confirm('确认退出登录？', '退出', {
    confirmButtonText: '退出',
    cancelButtonText: '取消',
    type: 'warning',
  })
  await logout()
  authStore.clearAuth()
  router.push('/login')
}

function handleCommand(cmd: string) {
  if (cmd === 'logout') handleLogout()
  if (cmd === 'change-pwd') showChangePwd.value = true
}
</script>

<template>
  <div class="app" :class="{ collapsed }">
    <!-- ── 顶部栏 ─────────────────────────────────────────── -->
    <header class="topbar">
      <!-- 品牌区 -->
      <div class="brand-zone">
        <span class="brand-logo" aria-hidden="true" />
        <span v-if="!collapsed" class="brand-word">CMDB <em>Lite</em></span>
      </div>

      <!-- 左侧：折叠按钮 + 面包屑 -->
      <div class="topbar-left">
        <button
          class="icon-btn"
          :title="collapsed ? '展开侧边栏' : '折叠侧边栏'"
          @click="collapsed = !collapsed"
        >
          <el-icon size="18"><Fold v-if="!collapsed" /><Expand v-else /></el-icon>
        </button>

        <nav class="crumb" aria-label="面包屑">
          <span class="crumb-here">{{ pageTitle }}</span>
        </nav>
      </div>

      <div class="topbar-spacer" />

      <!-- 右侧：用户菜单 -->
      <div class="topbar-right">
        <el-dropdown @command="handleCommand">
          <div class="user-chip">
            <div class="user-avatar">{{ avatarText }}</div>
            <div class="user-info">
              <span class="user-name">{{ authStore.userInfo?.username || '用户' }}</span>
              <span class="role-badge" :class="authStore.role">
                <span class="role-dot" />
                {{ authStore.role }}
              </span>
            </div>
            <el-icon size="12" color="var(--neutral-400)"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="change-pwd">
                <el-icon><Lock /></el-icon>
                修改密码
              </el-dropdown-item>
              <el-dropdown-item divided command="logout" style="color: var(--color-danger)">
                <el-icon><SwitchButton /></el-icon>
                退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <!-- ── 主体：侧边栏 + 内容区 ─────────────────────────── -->
    <div class="body-grid">
      <AppSidebar :collapsed="collapsed" />

      <main class="main-content">
        <RouterView />
      </main>
    </div>

    <!-- 修改密码弹窗 -->
    <ChangePasswordDialog v-model="showChangePwd" />
  </div>
</template>

<style scoped>
.app {
  --sidebar-w: var(--sidebar-w, 220px);
  min-height: 100vh;
  background: var(--neutral-50);
}
.app.collapsed {
  --sidebar-w: 60px;
}

/* ── 顶部栏 ── */
.topbar {
  position: sticky;
  top: 0;
  z-index: 30;
  height: var(--topbar-h);
  background: var(--neutral-0);
  border-bottom: 1px solid var(--neutral-200);
  display: flex;
  align-items: stretch;
  padding: 0 var(--space-6) 0 0;
}

.brand-zone {
  width: 220px;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 0 var(--space-4);
  border-right: 1px solid var(--neutral-200);
  transition: width 0.18s ease;
  overflow: hidden;
  flex-shrink: 0;
}
.app.collapsed .brand-zone {
  width: 60px;
}

.brand-logo {
  width: 28px;
  height: 28px;
  background: var(--color-primary-500);
  border-radius: var(--radius-md);
  position: relative;
  flex-shrink: 0;
}
.brand-logo::before,
.brand-logo::after {
  content: '';
  position: absolute;
  background: rgba(255, 255, 255, 0.92);
  border-radius: 1.5px;
}
.brand-logo::before { left: 6px; top: 8px; width: 16px; height: 3px; }
.brand-logo::after  { left: 6px; top: 16px; width: 10px; height: 3px; }

.brand-word {
  font-weight: 600;
  color: var(--neutral-900);
  font-size: 16px;
  letter-spacing: -0.01em;
  white-space: nowrap;
}
.brand-word em {
  font-style: normal;
  color: var(--color-primary-500);
}

.topbar-left {
  display: flex;
  align-items: center;
  padding-left: var(--space-3);
  gap: var(--space-3);
}

.icon-btn {
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  color: var(--neutral-500);
  background: transparent;
  border: 0;
  cursor: pointer;
  transition: background-color 0.12s ease, color 0.12s ease;
}
.icon-btn:hover {
  background: var(--neutral-100);
  color: var(--neutral-900);
}

.crumb {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--fs-body);
  color: var(--neutral-500);
}
.crumb-here {
  color: var(--neutral-900);
  font-weight: 500;
}

.topbar-spacer { flex: 1; }

.topbar-right {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

/* 用户区 */
.user-chip {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: 4px 8px 4px 4px;
  border-radius: var(--radius-md);
  cursor: pointer;
  height: 40px;
  transition: background-color 0.12s ease;
}
.user-chip:hover {
  background: var(--neutral-100);
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--color-primary-100);
  color: var(--color-primary-700);
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  border: 2px solid var(--color-primary-200);
}

.user-info {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}
.user-name {
  color: var(--neutral-900);
  font-size: 13px;
  font-weight: 500;
}

.role-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  line-height: 14px;
  padding: 1px 6px;
  border-radius: 3px;
  font-weight: 500;
  margin-top: 2px;
}
.role-badge.super_admin {
  background: #FEE7EE;
  color: var(--role-super-admin);
}
.role-badge.admin {
  background: var(--color-primary-50);
  color: var(--role-admin);
}
.role-badge.auditor {
  background: var(--neutral-100);
  color: var(--role-auditor);
}
.role-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
}

/* ── 主体 ── */
.body-grid {
  display: grid;
  grid-template-columns: auto 1fr;
  min-height: calc(100vh - var(--topbar-h));
}

.main-content {
  padding: var(--space-6);
  min-width: 0;
}
</style>
