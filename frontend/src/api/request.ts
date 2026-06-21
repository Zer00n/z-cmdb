/**
 * Axios instance + unified interceptors
 * Error handling is centralized here; business components don't need try/catch for HTTP errors
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/',
  timeout: 30000,
  withCredentials: true, // Send cookies (refresh_token)
})

// ── Request interceptor: inject access_token ────────────────────────────
request.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ── Response interceptor: unified error handling ─────────────────────────────────
request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status
    const message =
      error.response?.data?.message ||
      // FastAPI 422 Pydantic validation error: detail is an array
      (Array.isArray(error.response?.data?.detail)
        ? error.response.data.detail.map((d: any) => d.msg).join('；')
        : error.response?.data?.detail) ||
      '请求失败，请稍后重试'

    if (status === 401) {
      // Clear local token, redirect to login page
      sessionStorage.removeItem('access_token')
      // Prevent redirect loop
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
      return Promise.reject(error)
    }

    if (status === 403) {
      ElMessage.error('权限不足')
      return Promise.reject(error)
    }

    if (status === 423) {
      ElMessage.error(message)
      return Promise.reject(error)
    }

    if (status && status >= 500) {
      ElMessage.error('服务器内部错误，请联系管理员')
      return Promise.reject(error)
    }

    ElMessage.error(message)
    return Promise.reject(error)
  }
)

export default request
