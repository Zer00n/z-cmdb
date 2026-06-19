/**
 * axios 实例 + 统一拦截器
 * 错误处理统一在此，业务组件不写 try/catch 处理 HTTP 错误
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/',
  timeout: 30000,
  withCredentials: true, // 携带 cookie（refresh_token）
})

// ── 请求拦截器：注入 access_token ────────────────────────────
request.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ── 响应拦截器：统一错误处理 ─────────────────────────────────
request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status
    const message =
      error.response?.data?.message ||
      // FastAPI 422 Pydantic 校验错误：detail 为数组
      (Array.isArray(error.response?.data?.detail)
        ? error.response.data.detail.map((d: any) => d.msg).join('；')
        : error.response?.data?.detail) ||
      '请求失败，请稍后重试'

    if (status === 401) {
      // 清除本地 token，跳转登录页
      sessionStorage.removeItem('access_token')
      // 避免循环跳转
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
