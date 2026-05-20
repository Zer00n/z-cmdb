/**
 * 扫描批次 API 封装
 */
import request from './request'
import type { ScanBatch, ScanBatchListResponse, ScanConfirmRequest, ScanDiffResponse } from '@/types/scan'

/** 上传 nmap XML 文件 */
export function uploadScan(file: File): Promise<ScanBatch> {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/api/scans/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/** 扫描批次列表 */
export function fetchScanBatches(params?: {
  page?: number
  page_size?: number
}): Promise<ScanBatchListResponse> {
  return request.get('/api/scans', { params })
}

/** 扫描批次详情 */
export function fetchScanBatch(id: number): Promise<ScanBatch> {
  return request.get(`/api/scans/${id}`)
}

/** 扫描批次差异详情 */
export function fetchScanDiff(id: number): Promise<ScanDiffResponse> {
  return request.get(`/api/scans/${id}/diff`)
}

/** 确认导入批次 */
export function confirmBatch(id: number, data: ScanConfirmRequest): Promise<ScanBatch> {
  return request.post(`/api/scans/${id}/confirm`, data)
}

/** 拒绝并删除批次 */
export function rejectBatch(id: number): Promise<void> {
  return request.delete(`/api/scans/${id}`)
}
