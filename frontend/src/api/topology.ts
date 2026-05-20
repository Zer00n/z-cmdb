/**
 * 拓扑图 API 封装
 */
import request from './request'
import type {
  TopologyDetail,
  TopologyGenerateRequest,
  TopologySaveRequest,
  TopologyVersion,
} from '@/types/topology'

/** LLM 生成拓扑图初稿（timeout 加长，LLM 可能需要 60-120 秒） */
export function generateTopology(data?: TopologyGenerateRequest): Promise<{
  drawio_xml: string
  asset_count: number
  generated_at: string
}> {
  return request.post('/api/topology/generate', data || {}, { timeout: 300000 })
}

/** 获取当前拓扑图 */
export function fetchCurrentTopology(): Promise<TopologyDetail | null> {
  return request.get('/api/topology')
}

/** 历史版本列表 */
export function fetchTopologyVersions(): Promise<TopologyVersion[]> {
  return request.get('/api/topology/versions')
}

/** 保存新版本 */
export function saveTopology(data: TopologySaveRequest): Promise<TopologyDetail> {
  return request.post('/api/topology', data)
}

/** 回滚到某版本 */
export function rollbackTopology(id: number): Promise<TopologyDetail> {
  return request.post(`/api/topology/${id}/rollback`)
}
