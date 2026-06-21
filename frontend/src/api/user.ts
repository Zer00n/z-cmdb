/**
 * User management API wrappers
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

/** User list */
export function fetchUsers(): Promise<UserInfo[]> {
  return request.get('/api/users')
}

/** Create user */
export function createUser(data: UserCreateRequest): Promise<UserInfo> {
  return request.post('/api/users', data)
}

/** User detail */
export function fetchUser(id: number): Promise<UserInfo> {
  return request.get(`/api/users/${id}`)
}

/** Update user */
export function updateUser(id: number, data: UserUpdateRequest): Promise<UserInfo> {
  return request.patch(`/api/users/${id}`, data)
}

/** Disable user */
export function disableUser(id: number): Promise<void> {
  return request.delete(`/api/users/${id}`)
}
