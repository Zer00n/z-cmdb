<script setup lang="ts">
/**
 * 主框架布局
 * 2026 UI Redesign：升级视觉（毛玻璃顶栏 + 侧边栏柔光），保持原有逻辑不变
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useFeatureStore } from '@/stores/feature'
import { logout } from '@/api/auth'
import { setLocale } from '@/i18n'
import { useTranslatedLabels } from '@/composables/useTranslatedLabels'
import AppSidebar from '@/components/common/AppSidebar.vue'
import ChangePasswordDialog from '@/components/common/ChangePasswordDialog.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const featureStore = useFeatureStore()
const { t, locale } = useI18n()
const { roleLabel: getRoleLabel } = useTranslatedLabels()

const collapsed = ref(false)
const showChangePwd = ref(false)

const pageTitle = computed(() => {
  const key = route.meta.title as string
  return key ? t(key) : ''
})

const avatarText = computed(() => {
  const name = authStore.userInfo?.full_name || authStore.userInfo?.username || ''
  return name.slice(0, 2).toUpperCase()
})

onMounted(() => {
  if (authStore.mustChangePassword) {
    showChangePwd.value = true
  }
  // 拉取功能特性开关状态
  featureStore.fetchFeatureFlags()
})

watch(showChangePwd, (newVal) => {
  if (!newVal && authStore.mustChangePassword) {
    authStore.clearAuth()
    router.push('/login')
  }
})

async function handleLogout() {
  await ElMessageBox.confirm(t('layout.topbar.confirmLogout'), t('layout.topbar.logoutTitle'), {
    confirmButtonText: t('layout.topbar.logoutConfirm'),
    cancelButtonText: t('common.cancel'),
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

const roleLabel = computed(() => getRoleLabel(authStore.role || ''))

function toggleLocale() {
  setLocale(locale.value === 'zh' ? 'en' : 'zh')
}
</script>

<template>
  <div class="app" :class="{ collapsed }">
    <!-- 背景装饰：极弱的网格 + 顶部光晕 -->
    <div class="app-bg" aria-hidden="true" />

    <!-- ── 顶部栏 ─────────────────────────────────────────── -->
    <header class="topbar">
      <!-- 品牌区 -->
      <div class="brand-zone">
        <span class="brand-logo" aria-hidden="true">
          <span class="brand-logo-inner" />
        </span>
        <span v-if="!collapsed" class="brand-word">Z-CMDB <em>Lite</em></span>
      </div>

      <!-- 左：折叠按钮 + 面包屑 -->
      <div class="topbar-left">
        <button
          class="icon-btn"
          :title="collapsed ? t('layout.topbar.expandSidebar') : t('layout.topbar.collapseSidebar')"
          @click="collapsed = !collapsed"
        >
          <el-icon size="18"><Fold v-if="!collapsed" /><Expand v-else /></el-icon>
        </button>

        <nav class="crumb" :aria-label="t('layout.topbar.breadcrumb')">
          <span class="crumb-prefix">CMDB</span>
          <span class="crumb-sep">/</span>
          <span class="crumb-here">{{ pageTitle }}</span>
        </nav>
      </div>

      <div class="topbar-spacer" />

      <!-- 右：环境标签 + 用户菜单 -->
      <div class="topbar-right">
        <span class="env-chip">
          <span class="env-dot" />
          v0.4
        </span>

        <button class="lang-toggle" @click="toggleLocale" :title="t('layout.topbar.switchLanguage')">
          {{ locale === 'zh' ? 'EN' : '中' }}
        </button>

        <el-dropdown @command="handleCommand">
          <div class="user-chip">
            <div class="user-avatar">{{ avatarText }}</div>
            <div class="user-info">
              <span class="user-name">{{ authStore.userInfo?.full_name || authStore.userInfo?.username || t('layout.topbar.user') }}</span>
              <span class="role-badge" :class="authStore.role">
                <span class="role-dot" />
                {{ roleLabel }}
              </span>
            </div>
            <el-icon size="12" color="var(--neutral-400)"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="change-pwd">
                <el-icon><Lock /></el-icon>
                {{ t('layout.topbar.changePassword') }}
              </el-dropdown-item>
              <el-dropdown-item divided command="logout" style="color: var(--color-danger)">
                <el-icon><SwitchButton /></el-icon>
                {{ t('layout.topbar.logout') }}
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

    <ChangePasswordDialog v-model="showChangePwd" />
  </div>
</template>

<style scoped>
.app {
  --sidebar-w: var(--sidebar-w, 220px);
  position: relative;
  min-height: 100vh;
  background: var(--surface-canvas);
  isolation: isolate;
}
.app.collapsed {
  --sidebar-w: 60px;
}

/* 背景装饰：在最底层放一层柔光网格 */
.app-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background:
    radial-gradient(1200px 600px at 18% -10%, rgba(37, 99, 235, 0.06) 0%, transparent 60%),
    radial-gradient(900px 500px at 95% 0%, rgba(99, 102, 241, 0.05) 0%, transparent 55%),
    var(--surface-canvas);
}
.app-bg::after {
  content: '';
  position: absolute;
  inset: 0;
  background-image: radial-gradient(circle at 1px 1px, rgba(15, 23, 42, 0.035) 1px, transparent 0);
  background-size: 28px 28px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.55) 0%, rgba(0, 0, 0, 0) 70%);
  -webkit-mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.55) 0%, rgba(0, 0, 0, 0) 70%);
}

/* ── 顶部栏：半透明 + 模糊背景 ── */
.topbar {
  position: sticky;
  top: 0;
  z-index: 30;
  height: var(--topbar-h);
  background: var(--surface-overlay);
  -webkit-backdrop-filter: saturate(140%) blur(14px);
  backdrop-filter: saturate(140%) blur(14px);
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
  display: flex;
  align-items: stretch;
  padding: 0 var(--space-6) 0 0;
}

.brand-zone {
  width: 220px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 var(--space-4);
  border-right: 1px solid rgba(15, 23, 42, 0.06);
  transition: width var(--dur-base) var(--ease-out);
  overflow: hidden;
  flex-shrink: 0;
}
.app.collapsed .brand-zone { width: 60px; }

.brand-logo {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: var(--accent-gradient);
  position: relative;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow:
    0 4px 12px -2px rgba(37, 99, 235, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.25);
}
.brand-logo-inner {
  width: 14px;
  height: 14px;
  position: relative;
}
.brand-logo-inner::before,
.brand-logo-inner::after {
  content: '';
  position: absolute;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 1.5px;
}
.brand-logo-inner::before { left: 0; top: 1px; width: 14px; height: 3px; }
.brand-logo-inner::after  { left: 0; top: 9px; width: 10px; height: 3px; }

.brand-word {
  font-weight: 600;
  color: var(--neutral-900);
  font-size: 16px;
  letter-spacing: -0.01em;
  white-space: nowrap;
}
.brand-word em {
  font-style: normal;
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  font-weight: 700;
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
  transition: background-color var(--dur-fast) var(--ease-out),
              color var(--dur-fast) var(--ease-out);
}
.icon-btn:hover {
  background: var(--neutral-100);
  color: var(--neutral-900);
}

.crumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--fs-body);
  color: var(--neutral-500);
}
.crumb-prefix {
  font-family: var(--font-mono);
  font-size: 12.5px;
  color: var(--neutral-400);
}
.crumb-sep { color: var(--neutral-300); }
.crumb-here {
  color: var(--neutral-900);
  font-weight: 500;
}

.topbar-spacer { flex: 1; }

.topbar-right {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

/* 环境徽标 */
.env-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 999px;
  background: var(--surface-sunken);
  border: 1px solid var(--neutral-200);
  color: var(--neutral-500);
  font-size: 12px;
  font-family: var(--font-mono);
  font-weight: 500;
}

/* 语言切换按钮 */
.lang-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 28px;
  border-radius: var(--radius-md);
  border: 1px solid var(--neutral-200);
  background: var(--surface-base);
  color: var(--neutral-700);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color var(--dur-fast) var(--ease-out),
              border-color var(--dur-fast) var(--ease-out);
}
.lang-toggle:hover {
  background: var(--color-primary-50);
  border-color: var(--color-primary-300);
  color: var(--color-primary-700);
}
.env-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-success);
  box-shadow: 0 0 0 3px rgba(22, 163, 74, 0.18);
}

/* 用户区 */
.user-chip {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: 4px 10px 4px 4px;
  border-radius: 999px;
  cursor: pointer;
  height: 40px;
  transition: background-color var(--dur-fast) var(--ease-out);
}
.user-chip:hover {
  background: var(--neutral-100);
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--accent-gradient);
  color: #FFFFFF;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  letter-spacing: 0.02em;
  box-shadow:
    0 2px 6px -1px rgba(37, 99, 235, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
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
  letter-spacing: -0.005em;
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
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: auto 1fr;
  min-height: calc(100vh - var(--topbar-h));
}

.main-content {
  padding: var(--space-6);
  min-width: 0;
  position: relative;
}
</style>
