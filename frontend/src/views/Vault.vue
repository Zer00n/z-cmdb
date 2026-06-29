<script setup lang="ts">
/**
 * Vault page — handles first-time setup and subsequent unlock
 * Shown when the database is in LOCKED state (SQLite static encryption)
 */
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { getLockStatus, vaultSetup, vaultUnlock, type LockStatus, type SetupResult } from '@/api/vault'

const { t } = useI18n()
const router = useRouter()
const authStore = useAuthStore()

// ── State ────────────────────────────────────────────────────
const loading = ref(true)
const lockStatus = ref<LockStatus | null>(null)
const mode = ref<'setup' | 'unlock'>('unlock')
const unlockTab = ref<'password' | 'recovery'>('password')
const setupResult = ref<SetupResult | null>(null)
const submitting = ref(false)

// Setup form
const setupForm = reactive({
  username: '',
  password: '',
})

// Unlock form
const unlockForm = reactive({
  username: '',
  password: '',
  recoveryCode: '',
})

// ── Computed ─────────────────────────────────────────────────
const isSetup = computed(() => mode.value === 'setup')

// ── Lifecycle ────────────────────────────────────────────────
onMounted(async () => {
  try {
    const status = await getLockStatus()
    lockStatus.value = status
    mode.value = status.needs_setup ? 'setup' : 'unlock'
  } catch {
    // If lock-status fails, assume locked and show unlock
    mode.value = 'unlock'
  } finally {
    loading.value = false
  }
})

// ── Setup ────────────────────────────────────────────────────
async function handleSetup() {
  submitting.value = true
  try {
    const res = await vaultSetup({
      username: setupForm.username || undefined,
      password: setupForm.password || undefined,
    })
    setupResult.value = res
  } finally {
    submitting.value = false
  }
}

// ── Unlock ───────────────────────────────────────────────────
async function handleUnlock() {
  submitting.value = true
  try {
    if (unlockTab.value === 'password') {
      const res = await vaultUnlock({
        username: unlockForm.username,
        password: unlockForm.password,
      })
      // Password unlock auto-issues JWT
      if (res.access_token) {
        authStore.setToken(res.access_token)
        sessionStorage.removeItem('lock_status')
        ElMessage.success(t('vault.unlock.success'))
        router.push('/')
        return
      }
    } else {
      await vaultUnlock({ recovery_code: unlockForm.recoveryCode })
      // Recovery unlock needs a separate login
      sessionStorage.removeItem('lock_status')
      ElMessage.success(t('vault.unlock.success'))
      router.push('/login')
    }
  } finally {
    submitting.value = false
  }
}

// ── Copy helper ──────────────────────────────────────────────
function copyText(text: string) {
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success(t('vault.recovery.copied'))
  })
}

// ── Enter system after setup ─────────────────────────────────
function enterSystem() {
  // After setup, the vault is already unlocked but no JWT was issued
  // Clear cached lock status and go to login
  sessionStorage.removeItem('lock_status')
  router.push('/login')
}
</script>

<template>
  <div class="vault-page">
    <!-- Background -->
    <div class="bg-aura" aria-hidden="true" />
    <div class="bg-grid" aria-hidden="true" />

    <!-- Top bar -->
    <header class="vault-top">
      <div class="brand">
        <span class="brand-logo" aria-hidden="true">
          <span class="brand-logo-inner" />
        </span>
        <span class="brand-name">Z-CMDB <em>Lite</em></span>
      </div>
      <span class="top-status" :class="isSetup ? 'setup' : 'locked'">
        <span class="status-dot" />
        {{ isSetup ? t('vault.status.needsSetup') : t('vault.status.locked') }}
      </span>
    </header>

    <!-- Loading -->
    <div v-if="loading" class="vault-loading">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
    </div>

    <!-- Recovery code display (after setup) -->
    <main v-else-if="setupResult" class="vault-shell">
      <div class="vault-card recovery-card">
        <div class="recovery-icon">
          <el-icon :size="48"><Key /></el-icon>
        </div>
        <h2>{{ t('vault.recovery.title') }}</h2>

        <el-alert type="warning" :closable="false" show-icon class="recovery-warning">
          {{ t('vault.recovery.warning') }}
        </el-alert>

        <div class="recovery-info">
          <div class="info-row" v-if="setupResult.admin_username">
            <span class="info-label">{{ t('vault.recovery.username') }}</span>
            <span class="info-value mono">{{ setupResult.admin_username }}</span>
          </div>
          <div class="info-row" v-if="setupResult.admin_password">
            <span class="info-label">{{ t('vault.recovery.adminPassword') }}</span>
            <span class="info-value mono">
              {{ setupResult.admin_password }}
              <el-button link type="primary" @click="copyText(setupResult.admin_password!)">
                <el-icon><CopyDocument /></el-icon>
              </el-button>
            </span>
          </div>
          <div class="info-row recovery-code-row">
            <span class="info-label">{{ t('vault.recovery.code') }}</span>
            <span class="info-value mono recovery-value">
              {{ setupResult.recovery_code }}
              <el-button link type="primary" @click="copyText(setupResult.recovery_code)">
                <el-icon><CopyDocument /></el-icon>
              </el-button>
            </span>
          </div>
        </div>

        <el-button type="primary" size="large" class="enter-btn" @click="enterSystem">
          {{ t('vault.recovery.enter') }}
          <el-icon style="margin-left: 6px"><Right /></el-icon>
        </el-button>
      </div>
    </main>

    <!-- Main: Setup or Unlock -->
    <main v-else class="vault-shell">
      <!-- Setup mode -->
      <div v-if="isSetup" class="vault-card">
        <div class="card-head">
          <h2>{{ t('vault.setup.title') }}</h2>
          <p>{{ t('vault.setup.subtitle') }}</p>
        </div>

        <el-form @submit.prevent="handleSetup" class="vault-form">
          <el-form-item>
            <el-input
              v-model="setupForm.username"
              :placeholder="t('vault.setup.usernamePlaceholder')"
              size="large"
            >
              <template #prefix>
                <el-icon><User /></el-icon>
              </template>
            </el-input>
          </el-form-item>
          <el-form-item>
            <el-input
              v-model="setupForm.password"
              type="password"
              show-password
              :placeholder="t('vault.setup.passwordPlaceholder')"
              size="large"
            >
              <template #prefix>
                <el-icon><Lock /></el-icon>
              </template>
            </el-input>
            <div class="field-hint">{{ t('vault.setup.passwordHint') }}</div>
          </el-form-item>

          <el-button
            type="primary"
            size="large"
            class="submit-btn"
            :loading="submitting"
            @click="handleSetup"
          >
            <span>{{ t('vault.setup.submit') }}</span>
            <el-icon style="margin-left: 6px"><Right /></el-icon>
          </el-button>
        </el-form>
      </div>

      <!-- Unlock mode -->
      <div v-else class="vault-card">
        <div class="card-head">
          <h2>{{ t('vault.unlock.title') }}</h2>
          <p>{{ t('vault.unlock.subtitle') }}</p>
        </div>

        <el-tabs v-model="unlockTab" class="unlock-tabs">
          <!-- Password tab -->
          <el-tab-pane :label="t('vault.unlock.tabPassword')" name="password">
            <el-form @submit.prevent="handleUnlock" class="vault-form">
              <el-form-item>
                <el-input
                  v-model="unlockForm.username"
                  :placeholder="t('vault.unlock.usernamePlaceholder')"
                  size="large"
                  autocomplete="username"
                >
                  <template #prefix>
                    <el-icon><User /></el-icon>
                  </template>
                </el-input>
              </el-form-item>
              <el-form-item>
                <el-input
                  v-model="unlockForm.password"
                  type="password"
                  show-password
                  :placeholder="t('vault.unlock.passwordPlaceholder')"
                  size="large"
                  autocomplete="current-password"
                  @keyup.enter="handleUnlock"
                >
                  <template #prefix>
                    <el-icon><Lock /></el-icon>
                  </template>
                </el-input>
              </el-form-item>

              <el-button
                type="primary"
                size="large"
                class="submit-btn"
                :loading="submitting"
                @click="handleUnlock"
              >
                <span>{{ t('vault.unlock.submit') }}</span>
                <el-icon style="margin-left: 6px"><Unlock /></el-icon>
              </el-button>
            </el-form>
          </el-tab-pane>

          <!-- Recovery code tab -->
          <el-tab-pane :label="t('vault.unlock.tabRecovery')" name="recovery">
            <el-form @submit.prevent="handleUnlock" class="vault-form">
              <el-form-item>
                <el-input
                  v-model="unlockForm.recoveryCode"
                  :placeholder="t('vault.unlock.recoveryCodePlaceholder')"
                  size="large"
                  @keyup.enter="handleUnlock"
                >
                  <template #prefix>
                    <el-icon><Key /></el-icon>
                  </template>
                </el-input>
              </el-form-item>

              <el-button
                type="primary"
                size="large"
                class="submit-btn"
                :loading="submitting"
                @click="handleUnlock"
              >
                <span>{{ t('vault.unlock.submit') }}</span>
                <el-icon style="margin-left: 6px"><Unlock /></el-icon>
              </el-button>
            </el-form>
          </el-tab-pane>
        </el-tabs>
      </div>
    </main>

    <footer class="vault-footer">
      {{ t('login.footer') }}
    </footer>
  </div>
</template>

<style scoped>
.vault-page {
  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--surface-canvas);
  overflow: hidden;
}

/* ── Background (same as Login) ── */
.bg-aura {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  background:
    radial-gradient(900px 500px at 12% 18%, rgba(37, 99, 235, 0.18) 0%, transparent 60%),
    radial-gradient(720px 480px at 88% 78%, rgba(99, 102, 241, 0.16) 0%, transparent 60%);
}
.bg-grid {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  background-image: radial-gradient(circle at 1px 1px, rgba(15, 23, 42, 0.05) 1px, transparent 0);
  background-size: 32px 32px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.55) 0%, rgba(0, 0, 0, 0) 70%);
  -webkit-mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.55) 0%, rgba(0, 0, 0, 0) 70%);
}

/* ── Top bar ── */
.vault-top {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 10;
  padding: var(--space-6) var(--space-12);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
}
.brand-logo {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--accent-gradient);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow:
    0 4px 12px -2px rgba(37, 99, 235, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.25);
}
.brand-logo-inner {
  width: 16px;
  height: 16px;
  position: relative;
}
.brand-logo-inner::before,
.brand-logo-inner::after {
  content: '';
  position: absolute;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 1.5px;
}
.brand-logo-inner::before { left: 0; top: 1px; width: 16px; height: 4px; }
.brand-logo-inner::after  { left: 0; top: 11px; width: 11px; height: 4px; }
.brand-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--neutral-900);
  letter-spacing: -0.01em;
}
.brand-name em {
  font-style: normal;
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  font-weight: 700;
}

.top-status {
  font-family: var(--font-mono);
  font-size: 12px;
  padding: 5px 14px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}
.top-status.locked {
  background: rgba(239, 68, 68, 0.08);
  color: #dc2626;
  border: 1px solid rgba(239, 68, 68, 0.2);
}
.top-status.setup {
  background: rgba(245, 158, 11, 0.08);
  color: #d97706;
  border: 1px solid rgba(245, 158, 11, 0.2);
}
.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.locked .status-dot { background: #ef4444; box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.2); }
.setup .status-dot  { background: #f59e0b; box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.2); }

/* ── Loading ── */
.vault-loading {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: var(--neutral-400);
}

/* ── Main shell ── */
.vault-shell {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 480px;
  padding: var(--space-12) var(--space-6);
}

/* ── Card ── */
.vault-card {
  background: var(--surface-base);
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 16px;
  padding: var(--space-8);
  box-shadow:
    0 24px 48px -16px rgba(15, 23, 42, 0.12),
    0 8px 16px -8px rgba(15, 23, 42, 0.06);
}
.vault-card::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  padding: 1px;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.18), rgba(99, 102, 241, 0.04) 50%, transparent);
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
}

.card-head {
  margin-bottom: var(--space-6);
}
.card-head h2 {
  margin: 0 0 4px;
  font-size: 22px;
  font-weight: 600;
  color: var(--neutral-900);
  letter-spacing: -0.01em;
}
.card-head p {
  margin: 0;
  font-size: 13px;
  color: var(--neutral-500);
}

/* ── Form ── */
.vault-form {
  display: flex;
  flex-direction: column;
}
.field-hint {
  margin-top: 4px;
  font-size: 12px;
  color: var(--neutral-400);
}
.submit-btn {
  width: 100%;
  margin-top: var(--space-2);
  height: 48px;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.02em;
}

/* ── Tabs ── */
.unlock-tabs {
  margin-top: var(--space-2);
}

/* ── Recovery display ── */
.recovery-card {
  text-align: center;
}
.recovery-icon {
  color: var(--color-primary-500);
  margin-bottom: var(--space-4);
}
.recovery-card h2 {
  margin: 0 0 var(--space-4);
  font-size: 20px;
  font-weight: 600;
  color: var(--neutral-900);
}
.recovery-warning {
  margin-bottom: var(--space-6);
  text-align: left;
}
.recovery-info {
  text-align: left;
  margin-bottom: var(--space-6);
}
.info-row {
  display: flex;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--neutral-100);
  gap: 12px;
}
.info-label {
  font-size: 13px;
  color: var(--neutral-500);
  flex-shrink: 0;
  min-width: 80px;
}
.info-value {
  font-size: 14px;
  color: var(--neutral-900);
  display: flex;
  align-items: center;
  gap: 8px;
  word-break: break-all;
}
.info-value.mono {
  font-family: var(--font-mono);
}
.recovery-code-row {
  background: var(--color-primary-50);
  border-radius: 8px;
  padding: 12px;
  margin-top: 8px;
  border: 1px solid rgba(37, 99, 235, 0.12);
}
.recovery-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-primary-700);
  letter-spacing: 0.05em;
}
.enter-btn {
  width: 100%;
  height: 48px;
  font-size: 15px;
  font-weight: 600;
}

/* ── Footer ── */
.vault-footer {
  position: relative;
  z-index: 1;
  text-align: center;
  padding: var(--space-6);
  font-size: 12px;
  color: var(--neutral-400);
  font-family: var(--font-mono);
}
</style>
