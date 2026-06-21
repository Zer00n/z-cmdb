/**
 * Auth Pinia Store
 * access_token stored in sessionStorage, user info in memory
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserInfo, UserRole } from '@/types/auth'

export const useAuthStore = defineStore('auth', () => {
  // ── State ──────────────────────────────────────────────────
  const accessToken = ref<string | null>(sessionStorage.getItem('access_token'))
  const userInfo = ref<UserInfo | null>(null)
  const mustChangePassword = ref(false)

  // Restore userInfo from existing token on initialization
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
      // Invalid token, clear it
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

  /** Save token and user info after successful login */
  function setToken(token: string, mustChange: boolean = false) {
    accessToken.value = token
    mustChangePassword.value = mustChange
    sessionStorage.setItem('access_token', token)
    // Parse JWT payload (no security validation, only reading role)
    try {
      const payload = JSON.parse(atob(token.split('.')[1]))
      // Extract basic user info from token payload
      // Full info will be supplemented by /api/users/me after login (v0.5)
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
      // Token parse failure doesn't affect login flow
    }
  }

  /** Set complete user info */
  function setUserInfo(info: UserInfo) {
    userInfo.value = info
  }

  /** Logout, clear all state */
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
