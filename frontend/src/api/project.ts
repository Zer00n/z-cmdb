/**
 * V0.6 project-perspective API calls
 */
import request from './request'
import type {
  Project,
  ProjectListResponse,
  ProjectCreateRequest,
  ProjectUpdateRequest,
  ConsumingUnit,
  ConsumingUnitCreate,
  ConsumingUnitPatch,
  ClaimRequest,
  PlacementCreate,
  HostSearchResult,
  BillingPolicy,
  BillingPolicyUpdate,
  BillSnapshot,
  TopologyResponse,
  UnclaimedResponse,
  ProjectSummary,
  UnitRelation,
} from '@/types/project'

// ── Projects ───────────────────────────────────────────────────

export function fetchProjectList(params?: {
  search?: string
  business_unit?: string
  owner?: string
  page?: number
  page_size?: number
}): Promise<ProjectListResponse> {
  return request.get('/api/projects', { params })
}

export function createProject(data: ProjectCreateRequest): Promise<Project> {
  return request.post('/api/projects', data)
}

export function fetchProject(id: string): Promise<Project> {
  return request.get(`/api/projects/${id}`)
}

export function updateProject(id: string, data: ProjectUpdateRequest): Promise<Project> {
  return request.patch(`/api/projects/${id}`, data)
}

export function fetchProjectTopology(id: string): Promise<TopologyResponse> {
  return request.get(`/api/projects/${id}/topology`)
}

export function fetchProjectUnits(id: string): Promise<ConsumingUnit[]> {
  return request.get(`/api/projects/${id}/units`)
}

export function fetchProjectBill(id: string, period: string): Promise<BillSnapshot> {
  return request.get(`/api/projects/${id}/bill`, { params: { period } })
}

export function fetchProjectSummary(id: string, lang: string = 'zh'): Promise<ProjectSummary> {
  return request.get(`/api/projects/${id}/summary`, { params: { lang } })
}

export function regenerateProjectSummary(id: string, lang: string = 'zh'): Promise<ProjectSummary> {
  return request.post(`/api/projects/${id}/summary/regenerate`, null, { params: { lang } })
}

// ── Units ──────────────────────────────────────────────────────

export function createUnit(data: ConsumingUnitCreate): Promise<ConsumingUnit> {
  return request.post('/api/units', data)
}

export function patchUnit(id: string, data: ConsumingUnitPatch): Promise<ConsumingUnit> {
  return request.patch(`/api/units/${id}`, data)
}

export function claimUnit(id: string, data: ClaimRequest): Promise<ConsumingUnit> {
  return request.post(`/api/units/${id}/claim`, data)
}

export function deleteUnit(id: string): Promise<void> {
  return request.delete(`/api/units/${id}`)
}

export function createPlacement(unitId: string, data: PlacementCreate): Promise<any> {
  return request.post(`/api/units/${unitId}/placements`, data)
}

// ── Hosts ───────────────────────────────────────────────────────

export function searchHosts(query: string): Promise<HostSearchResult[]> {
  return request.get('/api/hosts/search', { params: { q: query } })
}

// ── Unclaimed ──────────────────────────────────────────────────

export function fetchUnclaimed(): Promise<UnclaimedResponse> {
  return request.get('/api/unclaimed')
}

// ── Billing Policy ─────────────────────────────────────────────

export function fetchBillingPolicy(): Promise<BillingPolicy> {
  return request.get('/api/billing-policy')
}

export function updateBillingPolicy(data: BillingPolicyUpdate): Promise<BillingPolicy> {
  return request.put('/api/billing-policy', data)
}

// ── Relations ──────────────────────────────────────────────────

export function createRelation(data: {
  source_unit_id: string
  target_unit_id: string
  rel_type: string
}): Promise<UnitRelation> {
  return request.post('/api/relations', data)
}

export function deleteRelation(id: string): Promise<void> {
  return request.delete(`/api/relations/${id}`)
}
