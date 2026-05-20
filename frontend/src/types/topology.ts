/**
 * 拓扑图 TypeScript 类型
 */

export interface TopologyVersion {
  id: number
  version_no: string
  title: string | null
  created_at: string
  is_current: boolean
}

export interface TopologyDetail {
  id: number
  version_no: string
  title: string | null
  description: string | null
  drawio_xml: string
  created_by: number | null
  created_at: string
  is_current: boolean
}

export interface TopologyGenerateRequest {
  provider?: string
  model?: string
}

export interface TopologySaveRequest {
  title?: string
  description?: string
  drawio_xml: string
}
