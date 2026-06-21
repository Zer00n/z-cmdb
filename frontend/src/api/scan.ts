/**
 * Scan batch API wrappers
 */
import request from './request'
import type { ScanBatch, ScanBatchListResponse, ScanConfirmRequest, ScanDiffResponse } from '@/types/scan'

/** Upload nmap XML file */
export function uploadScan(file: File): Promise<ScanBatch> {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/api/scans/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
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

/** Scan batch diff detail */
export function fetchScanDiff(id: number): Promise<ScanDiffResponse> {
  return request.get(`/api/scans/${id}/diff`)
}

/** Confirm import batch */
export function confirmBatch(id: number, data: ScanConfirmRequest): Promise<ScanBatch> {
  return request.post(`/api/scans/${id}/confirm`, data)
}

/** Reject and delete batch */
export function rejectBatch(id: number): Promise<void> {
  return request.delete(`/api/scans/${id}`)
}
