/**
 * Auth API wrappers
 */
import request from './request'
import type { ChangePasswordRequest, LoginRequest, TokenResponse } from '@/types/auth'

/** Login */
export function login(data: LoginRequest): Promise<TokenResponse> {
  return request.post('/api/auth/login', data)
}

/** Refresh access_token (using httpOnly cookie refresh_token) */
export function refreshToken(): Promise<TokenResponse> {
  return request.post('/api/auth/refresh')
}

/** Logout */
export function logout(): Promise<{ message: string }> {
  return request.post('/api/auth/logout')
}

/** Change password */
export function changePassword(data: ChangePasswordRequest): Promise<{ message: string }> {
  return request.post('/api/auth/change-password', data)
}
