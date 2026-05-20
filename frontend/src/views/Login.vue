<script setup lang="ts">
/**
 * 登录页
 * 基于 Claude Design 02-login.html 实现
 */
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { login } from '@/api/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
})

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

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
</script>

<template>
  <div class="login-page">
    <!-- 背景网格 -->
    <div class="bg-grid" aria-hidden="true" />

    <main class="login-shell">
      <div class="login-wrap">
        <!-- 登录卡片 -->
        <div class="login-card">
          <!-- 品牌 -->
          <div class="brand">
            <span class="brand-logo" aria-hidden="true" />
            <span class="brand-name">CMDB <em>Lite</em></span>
          </div>
          <p class="subtitle">轻量级资产配置管理系统</p>

          <!-- 表单 -->
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
                placeholder="请输入用户名"
                size="large"
                autocomplete="username"
                :prefix-icon="'User'"
              />
            </el-form-item>
            <el-form-item prop="password">
              <el-input
                v-model="form.password"
                type="password"
                placeholder="请输入密码"
                size="large"
                show-password
                autocomplete="current-password"
                :prefix-icon="'Lock'"
                @keyup.enter="handleLogin"
              />
            </el-form-item>

            <el-button
              type="primary"
              size="large"
              class="login-btn"
              :loading="loading"
              @click="handleLogin"
            >
              登 录
            </el-button>
          </el-form>

          <!-- 帮助提示 -->
          <div class="help-line">
            <el-icon size="14" color="var(--neutral-400)"><InfoFilled /></el-icon>
            忘记密码？请联系系统管理员
          </div>
        </div>

        <!-- 状态提示 -->
        <div class="status-chips">
          <span class="chip">
            <span class="chip-dot online" />
            服务正常
          </span>
          <span class="chip-sep">·</span>
          <span class="chip">登录尝试受限：5 次 / 15 分钟</span>
          <span class="chip-sep">·</span>
          <span class="chip">仅限企业内网访问</span>
        </div>
      </div>
    </main>

    <footer class="login-footer">
      CMDB Lite v0.1.0
      <span class="sep">·</span>
      内部运维平台
    </footer>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  min-width: 1280px;
  background:
    radial-gradient(1200px 600px at 50% -200px, #EEF2FA 0%, transparent 65%),
    var(--neutral-50);
}

.bg-grid {
  position: fixed;
  inset: 0;
  pointer-events: none;
  background-image: radial-gradient(circle at 1px 1px, rgba(15, 23, 42, 0.04) 1px, transparent 0);
  background-size: 32px 32px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.6) 0%, rgba(0, 0, 0, 0) 60%);
  -webkit-mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.6) 0%, rgba(0, 0, 0, 0) 60%);
}

.login-shell {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-12) var(--space-6);
}

.login-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.login-card {
  width: 420px;
  background: var(--neutral-0);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-lg);
  padding: var(--space-8);
  box-shadow: var(--shadow-subtle);
}

/* 品牌 */
.brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
}

.brand-logo {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  background: var(--color-primary-500);
  position: relative;
  flex-shrink: 0;
}
.brand-logo::before,
.brand-logo::after {
  content: '';
  position: absolute;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 1.5px;
}
.brand-logo::before { left: 7px; top: 9px; width: 18px; height: 4px; }
.brand-logo::after  { left: 7px; top: 19px; width: 12px; height: 4px; }

.brand-name {
  font-size: 20px;
  line-height: 28px;
  font-weight: 600;
  color: var(--neutral-900);
  letter-spacing: -0.01em;
}
.brand-name em {
  font-style: normal;
  color: var(--color-primary-500);
}

.subtitle {
  color: var(--neutral-500);
  font-size: var(--fs-body);
  margin: 0 0 var(--space-8);
}

/* 表单 */
.login-form {
  display: flex;
  flex-direction: column;
}

.login-btn {
  width: 100%;
  margin-top: var(--space-2);
}

/* 帮助 */
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

/* 状态提示 */
.status-chips {
  margin-top: var(--space-6);
  display: flex;
  gap: var(--space-3);
  font-size: var(--fs-caption);
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
.chip-dot.online { background: var(--color-success); }
.chip-sep { color: var(--neutral-300); }

/* 页脚 */
.login-footer {
  text-align: center;
  padding: 0 var(--space-6) var(--space-8);
  font-size: var(--fs-caption);
  color: var(--neutral-400);
  font-family: var(--font-mono);
}
.sep { color: var(--neutral-300); margin: 0 var(--space-2); }
</style>
