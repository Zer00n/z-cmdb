/**
 * 鉴权相关 API 封装
 */
import request from './request'
import type { ChangePasswordRequest, LoginRequest, TokenResponse } from '@/types/auth'

/** 登录 */
export function login(data: LoginRequest): Promise<TokenResponse> {
  return request.post('/api/auth/login', data)
}

/** 刷新 access_token（使用 httpOnly cookie 中的 refresh_token） */
export function refreshToken(): Promise<TokenResponse> {
  return request.post('/api/auth/refresh')
}

/** 退出登录 */
export function logout(): Promise<{ message: string }> {
  return request.post('/api/auth/logout')
}

/** 修改密码 */
export function changePassword(data: ChangePasswordRequest): Promise<{ message: string }> {
  return request.post('/api/auth/change-password', data)
}
