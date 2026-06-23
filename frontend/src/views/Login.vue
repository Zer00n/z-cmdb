<script setup lang="ts">
/**
 * Login page
 * 2026 UI Redesign: split layout (left product intro + right login card), logic unchanged
 */
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { login } from '@/api/auth'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)

// Fallback GoatCounter: load if not already present in index.html
onMounted(() => {
  if (!document.querySelector('[data-goatcounter]')) {
    ;(window as any).goatcounter = { allow_local: true }
    const s = document.createElement('script')
    s.dataset.goatcounter = 'https://alex57xp32.goatcounter.com/count'
    s.async = true
    s.src = '//gc.zgo.at/count.js'
    document.head.appendChild(s)
  }
})

const form = reactive({
  username: '',
  password: '',
})

const rules = computed<FormRules>(() => ({
  username: [{ required: true, message: t('login.form.usernameRequired'), trigger: 'blur' }],
  password: [{ required: true, message: t('login.form.passwordRequired'), trigger: 'blur' }],
}))

async function handleLogin() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      const res = await login(form)
      authStore.setToken(res.access_token, res.must_change_password || false)
      const redirect = (route.query.redirect as string) || '/'
      router.push(redirect)
    } finally {
      loading.value = false
    }
  })
}

const features = computed(() => [
  { icon: 'CircleCheck', text: t('login.features.accuracy') },
  { icon: 'Lock', text: t('login.features.desensitize') },
  { icon: 'Key', text: t('login.features.rbac') },
  { icon: 'TrendCharts', text: t('login.features.exposure') },
])
</script>

<template>
  <div class="login-page">
    <!-- Background layer: dual radial gradients + grid -->
    <div class="bg-aura" aria-hidden="true" />
    <div class="bg-grid" aria-hidden="true" />

    <!-- Top bar: brand display only -->
    <header class="login-top">
      <div class="brand">
        <span class="brand-logo" aria-hidden="true">
          <span class="brand-logo-inner" />
        </span>
        <span class="brand-name">Z-CMDB <em>Lite</em></span>
      </div>
      <span class="top-version">v0.5.1</span>
    </header>

    <!-- Main body: left intro + right login card -->
    <main class="login-shell">
      <!-- Left: product intro -->
      <section class="intro">
        <div class="intro-tag">
          <span class="intro-tag-dot" />
          {{ t('login.tag') }}
        </div>
        <h1 class="intro-title">
          {{ t('login.title').split('\n')[0] }}<br />
          <em>{{ t('login.title').split('\n')[1] }}</em>
        </h1>
        <p class="intro-desc">
          {{ t('login.desc') }}
        </p>

        <ul class="feature-list">
          <li v-for="f in features" :key="f.text">
            <span class="feat-ico">
              <el-icon size="14"><component :is="f.icon" /></el-icon>
            </span>
            <span>{{ f.text }}</span>
          </li>
        </ul>

        <div class="intro-stats">
          <div class="stat">
            <div class="stat-num">10<span>min</span></div>
            <div class="stat-label">{{ t('login.stats.setup') }}</div>
          </div>
          <div class="stat-sep" />
          <div class="stat">
            <div class="stat-num">3</div>
            <div class="stat-label">{{ t('login.stats.roles') }}</div>
          </div>
          <div class="stat-sep" />
          <div class="stat">
            <div class="stat-num">SQLite</div>
            <div class="stat-label">{{ t('login.stats.deploy') }}</div>
          </div>
        </div>
      </section>

      <!-- Right: login card -->
      <section class="login-side">
        <div class="login-card">
          <div class="login-card-head">
            <h2>{{ t('login.card.title') }}</h2>
            <p>{{ t('login.card.subtitle') }}</p>
          </div>

          <el-form
            ref="formRef"
            :model="form"
            :rules="rules"
            class="login-form"
            @submit.prevent="handleLogin"
          >
            <el-form-item prop="username">
              <el-input
                v-model="form.username"
                :placeholder="t('login.form.username')"
                size="large"
                autocomplete="username"
              >
                <template #prefix>
                  <el-icon><User /></el-icon>
                </template>
              </el-input>
            </el-form-item>
            <el-form-item prop="password">
              <el-input
                v-model="form.password"
                type="password"
                :placeholder="t('login.form.password')"
                size="large"
                show-password
                autocomplete="current-password"
                @keyup.enter="handleLogin"
              >
                <template #prefix>
                  <el-icon><Lock /></el-icon>
                </template>
              </el-input>
            </el-form-item>

            <el-button
              type="primary"
              size="large"
              class="login-btn"
              :loading="loading"
              @click="handleLogin"
            >
              <span>{{ t('login.form.login') }}</span>
              <el-icon style="margin-left: 6px"><Right /></el-icon>
            </el-button>
          </el-form>

          <div class="help-line">
            <el-icon size="14"><InfoFilled /></el-icon>
            {{ t('login.help') }}
          </div>

          <div class="status-chips">
            <span class="chip">
              <span class="chip-dot online" />
              {{ t('login.status.serviceOk') }}
            </span>
            <span class="chip-sep">·</span>
            <span class="chip">{{ t('login.status.rateLimit') }}</span>
            <span class="chip-sep">·</span>
            <span class="chip">{{ t('login.status.intranetOnly') }}</span>
          </div>
        </div>
      </section>
    </main>

    <footer class="login-footer">
      {{ t('login.footer') }}
      <span class="sep">·</span>
      © 2026
    </footer>
  </div>
</template>

<style scoped>
.login-page {
  position: relative;
  min-height: 100vh;
  min-width: 1280px;
  display: flex;
  flex-direction: column;
  background: var(--surface-canvas);
  overflow: hidden;
}

/* ── Background layer ── */
.bg-aura {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  background:
    radial-gradient(900px 500px at 12% 18%, rgba(37, 99, 235, 0.18) 0%, transparent 60%),
    radial-gradient(720px 480px at 88% 78%, rgba(99, 102, 241, 0.16) 0%, transparent 60%),
    radial-gradient(1200px 600px at 50% -200px, rgba(99, 102, 241, 0.10) 0%, transparent 65%);
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
.login-top {
  position: relative;
  z-index: 1;
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
.top-version {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--neutral-500);
  padding: 4px 10px;
  background: var(--surface-base);
  border: 1px solid var(--neutral-200);
  border-radius: 999px;
}

/* ── Main two-column layout ── */
.login-shell {
  position: relative;
  z-index: 1;
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 460px;
  gap: var(--space-12);
  align-items: center;
  padding: 0 var(--space-12) var(--space-8);
  max-width: 1440px;
  width: 100%;
  margin: 0 auto;
}

/* ── Left: product intro ── */
.intro {
  max-width: 580px;
}
.intro-tag {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 5px 12px;
  border-radius: 999px;
  background: var(--surface-base);
  border: 1px solid rgba(37, 99, 235, 0.16);
  color: var(--color-primary-700);
  font-size: 12.5px;
  font-weight: 500;
  margin-bottom: var(--space-6);
  box-shadow: 0 2px 8px -2px rgba(37, 99, 235, 0.16);
}
.intro-tag-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-primary-500);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.16);
}

.intro-title {
  margin: 0 0 var(--space-4);
  font-size: 56px;
  line-height: 64px;
  font-weight: 700;
  color: var(--neutral-900);
  letter-spacing: -0.025em;
}
.intro-title em {
  font-style: normal;
  background: linear-gradient(135deg, #2563EB 0%, #6366F1 50%, #8B5CF6 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.intro-desc {
  margin: 0 0 var(--space-8);
  font-size: 16px;
  line-height: 26px;
  color: var(--neutral-500);
  max-width: 520px;
}

.feature-list {
  list-style: none;
  margin: 0 0 var(--space-8);
  padding: 0;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px var(--space-4);
}
.feature-list li {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13.5px;
  color: var(--neutral-700);
}
.feat-ico {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  background: var(--color-primary-50);
  color: var(--color-primary-600);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.intro-stats {
  display: flex;
  align-items: center;
  gap: var(--space-6);
  padding: var(--space-4) var(--space-6);
  background: var(--surface-base);
  border: var(--border-base);
  border-radius: var(--radius-lg);
  width: fit-content;
  box-shadow: var(--shadow-subtle);
}
.stat-sep {
  width: 1px;
  height: 28px;
  background: var(--neutral-200);
}
.stat-num {
  font-family: var(--font-mono);
  font-size: 22px;
  font-weight: 700;
  color: var(--neutral-900);
  letter-spacing: -0.02em;
  display: flex;
  align-items: baseline;
  gap: 2px;
}
.stat-num span {
  font-size: 12px;
  font-weight: 500;
  color: var(--neutral-500);
}
.stat-label {
  font-size: 11px;
  color: var(--neutral-500);
  margin-top: 2px;
  letter-spacing: 0.02em;
}

/* ── Right: login card ── */
.login-side {
  display: flex;
  justify-content: flex-end;
}
.login-card {
  width: 460px;
  background: var(--surface-base);
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 16px;
  padding: var(--space-8);
  box-shadow:
    0 24px 48px -16px rgba(15, 23, 42, 0.12),
    0 8px 16px -8px rgba(15, 23, 42, 0.06);
  position: relative;
}
.login-card::before {
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

.login-card-head {
  margin-bottom: var(--space-6);
}
.login-card-head h2 {
  margin: 0 0 4px;
  font-size: 22px;
  font-weight: 600;
  color: var(--neutral-900);
  letter-spacing: -0.01em;
}
.login-card-head p {
  margin: 0;
  font-size: 13px;
  color: var(--neutral-500);
}

.login-form {
  display: flex;
  flex-direction: column;
}

.login-btn {
  width: 100%;
  margin-top: var(--space-2);
  height: 48px;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.help-line {
  margin-top: var(--space-6);
  padding-top: var(--space-4);
  border-top: 1px solid var(--neutral-200);
  font-size: var(--fs-caption);
  color: var(--neutral-500);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.status-chips {
  margin-top: var(--space-4);
  display: flex;
  gap: 10px;
  font-size: 11px;
  color: var(--neutral-500);
  font-family: var(--font-mono);
  align-items: center;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.chip-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.chip-dot.online {
  background: var(--color-success);
  box-shadow: 0 0 0 3px rgba(22, 163, 74, 0.18);
}
.chip-sep { color: var(--neutral-300); }

/* ── Footer ── */
.login-footer {
  position: relative;
  z-index: 1;
  text-align: center;
  padding: 0 var(--space-6) var(--space-6);
  font-size: 12px;
  color: var(--neutral-400);
  font-family: var(--font-mono);
}
.sep { color: var(--neutral-300); margin: 0 var(--space-2); }
</style>
