/**
 * 用户管理 API 封装
 */
import request from './request'
import type { UserInfo } from '@/types/auth'

export interface UserCreateRequest {
  username: string
  password: string
  role: 'super_admin' | 'admin' | 'auditor'
  full_name?: string
  email?: string
}

export interface UserUpdateRequest {
  full_name?: string
  email?: string
  role?: 'super_admin' | 'admin' | 'auditor'
  status?: 'active' | 'disabled'
}

/** 用户列表 */
export function fetchUsers(): Promise<UserInfo[]> {
  return request.get('/api/users')
}

/** 创建用户 */
export function createUser(data: UserCreateRequest): Promise<UserInfo> {
  return request.post('/api/users', data)
}

/** 用户详情 */
export function fetchUser(id: number): Promise<UserInfo> {
  return request.get(`/api/users/${id}`)
}

/** 更新用户 */
export function updateUser(id: number, data: UserUpdateRequest): Promise<UserInfo> {
  return request.patch(`/api/users/${id}`, data)
}

/** 禁用用户 */
export function disableUser(id: number): Promise<void> {
  return request.delete(`/api/users/${id}`)
}
