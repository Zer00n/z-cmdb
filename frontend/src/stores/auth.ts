/**
 * 鉴权 Pinia Store
 * access_token 存 sessionStorage，用户信息存内存
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserInfo, UserRole } from '@/types/auth'

export const useAuthStore = defineStore('auth', () => {
  // ── State ──────────────────────────────────────────────────
  const accessToken = ref<string | null>(sessionStorage.getItem('access_token'))
  const userInfo = ref<UserInfo | null>(null)
  const mustChangePassword = ref(false)

  // 初始化时从已有 token 恢复 userInfo
  if (accessToken.value && !userInfo.value) {
    try {
      const payload = JSON.parse(atob(accessToken.value.split('.')[1]))
      userInfo.value = {
        id: parseInt(payload.sub),
        username: '',
        role: payload.role,
        full_name: null,
        email: null,
        status: 'active',
      }
    } catch {
      // token 无效，清除
      accessToken.value = null
      sessionStorage.removeItem('access_token')
    }
  }

  // ── Getters ────────────────────────────────────────────────
  const isLoggedIn = computed(() => !!accessToken.value)
  const role = computed<UserRole | null>(() => userInfo.value?.role ?? null)
  const isSuperAdmin = computed(() => role.value === 'super_admin')
  const isAdmin = computed(() => role.value === 'super_admin' || role.value === 'admin')
  const isAuditor = computed(() => role.value === 'auditor')

  // ── Actions ────────────────────────────────────────────────

  /** 登录成功后保存 token 和用户信息 */
  function setToken(token: string, mustChange: boolean = false) {
    accessToken.value = token
    mustChangePassword.value = mustChange
    sessionStorage.setItem('access_token', token)
    // 解析 JWT payload（不做安全校验，仅读取 role）
    try {
      const payload = JSON.parse(atob(token.split('.')[1]))
      // 用户信息从 token payload 中提取基础信息
      // 完整信息在登录后由 /api/users/me 补充（v0.5 实现）
      if (!userInfo.value) {
        userInfo.value = {
          id: parseInt(payload.sub),
          username: '',
          role: payload.role,
          full_name: null,
          email: null,
          status: 'active',
        }
      }
    } catch {
      // token 解析失败不影响登录流程
    }
  }

  /** 设置完整用户信息 */
  function setUserInfo(info: UserInfo) {
    userInfo.value = info
  }

  /** 退出登录，清除所有状态 */
  function clearAuth() {
    accessToken.value = null
    userInfo.value = null
    sessionStorage.removeItem('access_token')
  }

  return {
    accessToken,
    userInfo,
    mustChangePassword,
    isLoggedIn,
    role,
    isSuperAdmin,
    isAdmin,
    isAuditor,
    setToken,
    setUserInfo,
    clearAuth,
  }
})
