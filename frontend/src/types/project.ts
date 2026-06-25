/**
 * V0.6 project-perspective TypeScript types
 */

// ── Project ────────────────────────────────────────────────────

export interface Project {
  id: string
  name: string
  business_unit: string | null
  owner: string | null
  billing_enabled: number
  created_at: string
  updated_at: string
}

export interface ProjectListItem extends Project {
  unit_count: number
  host_count: number
  current_month_cost: number | null
}

export interface ProjectListResponse {
  items: ProjectListItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface ProjectCreateRequest {
  name: string
  owner?: string | null
  business_unit?: string | null
}

export interface ProjectUpdateRequest {
  name?: string | null
  owner?: string | null
  business_unit?: string | null
  billing_enabled?: number | null
}

// ── Consuming Unit ─────────────────────────────────────────────

export type ConsumingUnitType = 'k8s_workload' | 'docker' | 'vm_app' | 'host_process'
export type EnvironmentType = 'prod' | 'staging' | 'dev'

export interface ConsumingUnit {
  id: string
  project_id: string | null
  name: string
  type: ConsumingUnitType
  owner: string | null
  environment: EnvironmentType | null
  host_id?: string | null
  created_at: string
  updated_at: string
  runtime?: {
    instances: number
    cpu: number
    mem: number
    source: string
    observed_at: string
  }
}

export interface ConsumingUnitPatch {
  name?: string | null
  type?: ConsumingUnitType | null
  owner?: string | null
  environment?: EnvironmentType | null
}

export interface ClaimRequest {
  project_id: string
}

// ── Placement (read-only) ──────────────────────────────────────

export interface Placement {
  id: string
  unit_id: string
  host_id: string
  cpu_request: number
  mem_request: number
  instances: number
  source: string | null
  observed_at: string
}

// ── Unit Relation ──────────────────────────────────────────────

export type RelType = 'HTTP' | 'SQL' | 'cache' | 'mq' | 'depends'

export interface UnitRelation {
  id: string
  source_unit_id: string
  target_unit_id: string
  rel_type: RelType
  source: string
  created_at: string
}

// ── Billing Policy ─────────────────────────────────────────────

export interface BillingPolicy {
  id: string
  version: number
  denominator: 'allocatable' | 'sum_requests'
  weight_mode: 'mem' | 'cpu' | 'weighted' | 'max'
  weight_cpu: number
  weight_mem: number
  idle_cost: 'unallocated_bucket' | 'force_allocate'
  sampling: 'daily' | 'hourly'
  freeze: number
  is_active: number
  created_at: string
}

export interface BillingPolicyUpdate {
  denominator: 'allocatable' | 'sum_requests'
  weight_mode: 'mem' | 'cpu' | 'weighted' | 'max'
  weight_cpu: number
  weight_mem: number
  idle_cost: 'unallocated_bucket' | 'force_allocate'
  sampling: 'daily' | 'hourly'
}

// ── Bill Snapshot ──────────────────────────────────────────────

export interface BillSnapshot {
  id: string
  project_id: string
  period: string
  policy_version: number
  total_cost: number
  detail: BillDetail
  generated_at: string
  frozen: boolean
}

export interface BillDetail {
  project_cost: number
  bucket_idle: number
  lines: BillLine[]
}

export interface BillLine {
  unit_id: string
  host_id: string
  share: number
  amount: number
}

// ── Topology ───────────────────────────────────────────────────

export interface TopologyResponse {
  project_id: string
  generated_at: string
  source: string
  hosts: TopologyHost[]
  units: TopologyUnit[]
  dependencies: TopologyDependency[]
  cycles: TopologyCycle[]
}

export interface TopologyHost {
  id: string
  name: string
  ip_address: string | null
  monthly_cost: number
  shared: boolean
  shares: { project_id: string; ratio: number }[]
}

export interface TopologyUnit {
  id: string
  name: string
  type: string
  owner: string | null
  environment: string | null
  host_id: string | null
  runtime: {
    instances: number
    cpu: number
    mem: number
    source: string
    observed_at: string
  } | null
}

export interface TopologyDependency {
  id: string
  source: string
  target: string
  type: string
  in_cycle: boolean
}

export interface TopologyCycle {
  edges: string[]
  nodes: string[]
}

// ── Unclaimed ──────────────────────────────────────────────────

export interface UnclaimedUnit {
  id: string
  name: string
  type: string
  owner: string | null
  environment: string | null
  created_at: string
  host_name: string | null
  cpu_request: number | null
  mem_request: number | null
  instances: number | null
  monthly_cost: number | null
}

export interface ZombieHost {
  id: string
  name: string
  type: string
  cpu_total: number
  mem_total: number
  monthly_cost: number
  source: string | null
  created_at: string
}

export interface UnclaimedResponse {
  unclaimed_units: UnclaimedUnit[]
  zombie_hosts: ZombieHost[]
  summary: {
    unclaimed_count: number
    zombie_count: number
    total_monthly_waste: number
  }
}

// ── Project Summary ────────────────────────────────────────────

export interface ProjectSummary {
  overview: string | null
  risk: string | null
  draft: boolean
  lang?: string
  generated_at?: string
  disclaimer?: string
  degraded?: boolean
  reason?: string
}

// ── Consuming Unit Create ──────────────────────────────────────

export interface ConsumingUnitCreate {
  name: string
  type: 'k8s_workload' | 'docker' | 'vm_app' | 'host_process'
  owner?: string
  environment?: 'prod' | 'staging' | 'dev'
  project_id: string
}

export interface PlacementCreate {
  host_id: string
  cpu_request: number
  mem_request: number
  instances?: number
  source?: string
}

export interface HostSearchResult {
  id: string
  name: string
  ip_address: string | null
  type: string
  cpu_total: number
  mem_total: number
  monthly_cost: number
}
