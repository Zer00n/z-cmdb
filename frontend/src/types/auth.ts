/**
 * 鉴权相关 TypeScript 类型定义
 */

export type UserRole = 'super_admin' | 'admin' | 'auditor'

export interface UserInfo {
  id: number
  username: string
  role: UserRole
  full_name: string | null
  email: string | null
  status: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  must_change_password: boolean
}

export interface ChangePasswordRequest {
  old_password: string
  new_password: string
}

/** JWT payload（前端解码用，不做安全校验） */
export interface TokenPayload {
  sub: string
  role: UserRole
  exp: number
  type: string
}
