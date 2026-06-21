/**
 * Topology API wrappers
 */
import request from './request'
import type {
  TopologyDetail,
  TopologyGenerateRequest,
  TopologySaveRequest,
  TopologyVersion,
} from '@/types/topology'

/** LLM generate topology draft (timeout extended, LLM may need 60-120 seconds) */
export function generateTopology(data?: TopologyGenerateRequest): Promise<{
  drawio_xml: string
  asset_count: number
  generated_at: string
}> {
  return request.post('/api/topology/generate', data || {}, { timeout: 300000 })
}

/** Get current topology */
export function fetchCurrentTopology(): Promise<TopologyDetail | null> {
  return request.get('/api/topology')
}

/** Version history list */
export function fetchTopologyVersions(): Promise<TopologyVersion[]> {
  return request.get('/api/topology/versions')
}

/** Save new version */
export function saveTopology(data: TopologySaveRequest): Promise<TopologyDetail> {
  return request.post('/api/topology', data)
}

/** Rollback to a version */
export function rollbackTopology(id: number): Promise<TopologyDetail> {
  return request.post(`/api/topology/${id}/rollback`)
}
