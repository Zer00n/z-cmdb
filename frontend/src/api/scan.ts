/**
 * Scan batch API wrappers
 */
import request from './request'
import type { ScanBatch, ScanBatchListResponse, ScanConfirmRequest, ScanDiffResponse } from '@/types/scan'

export interface UploadProgressCallback {
  (event: { phase: 'uploading' | 'processing'; percent: number }): void
}

/** Upload nmap XML file (legacy, no progress) */
export function uploadScan(file: File): Promise<ScanBatch> {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/api/scans/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/** Upload nmap XML file with progress callback (XHR-based) */
export function uploadScanWithProgress(
  file: File,
  onProgress: UploadProgressCallback,
): Promise<ScanBatch> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const formData = new FormData()
    formData.append('file', file)

    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) {
        const percent = Math.round((e.loaded / e.total) * 100)
        onProgress({ phase: 'uploading', percent })
      }
    })

    xhr.upload.addEventListener('load', () => {
      onProgress({ phase: 'processing', percent: 100 })
    })

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText))
        } catch {
          reject(new Error('Invalid JSON response'))
        }
      } else {
        let message = 'Upload failed'
        try {
          const body = JSON.parse(xhr.responseText)
          message = body.message || message
        } catch { /* ignore */ }
        const err = new Error(message) as any
        err.response = { status: xhr.status, data: { message } }
        reject(err)
      }
    })

    xhr.addEventListener('error', () => reject(new Error('Network error')))
    xhr.addEventListener('timeout', () => reject(new Error('Upload timeout')))

    const token = sessionStorage.getItem('access_token')
    xhr.open('POST', '/api/scans/upload')
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)
    xhr.timeout = 120000 // 2 minutes for large files
    xhr.send(formData)
  })
}

/** Scan batch list */
export function fetchScanBatches(params?: {
  page?: number
  page_size?: number
}): Promise<ScanBatchListResponse> {
  return request.get('/api/scans', { params })
}

/** Scan batch detail */
export function fetchScanBatch(id: number): Promise<ScanBatch> {
  return request.get(`/api/scans/${id}`)
}

/** Scan batch diff detail (long timeout for large batches) */
export function fetchScanDiff(id: number): Promise<ScanDiffResponse> {
  return request.get(`/api/scans/${id}/diff`, { timeout: 120000 })
}

/** Confirm import batch (long timeout for large batches) */
export function confirmBatch(id: number, data: ScanConfirmRequest): Promise<ScanBatch> {
  return request.post(`/api/scans/${id}/confirm`, data, { timeout: 120000 })
}

/** Reject and delete batch */
export function rejectBatch(id: number): Promise<void> {
  return request.delete(`/api/scans/${id}`)
}
