/**
 * Vault (SQLite 静态加密) API
 * /api/lock-status, /api/setup, /api/unlock
 */
import request from './request'

export interface LockStatus {
  state: 'LOCKED' | 'UNLOCKED'
  needs_setup: boolean
}

export interface SetupResult {
  recovery_code: string
  admin_username: string
  admin_password: string | null
  message: string
}

export interface UnlockResult {
  state: string
  access_token: string | null
  needs_login: boolean
  username: string | null
}

export function getLockStatus(): Promise<LockStatus> {
  return request.get('/api/lock-status')
}

export function vaultSetup(data: {
  username?: string
  password?: string
}): Promise<SetupResult> {
  return request.post('/api/setup', data)
}

export function vaultUnlock(data: {
  username?: string
  password?: string
  recovery_code?: string
}): Promise<UnlockResult> {
  return request.post('/api/unlock', data)
}
