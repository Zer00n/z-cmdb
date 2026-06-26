/**
 * V0.6 project-perspective TypeScript types
 */

// ── Project ────────────────────────────────────────────────────

export interface Project {
  id: string
  name: string
  business_unit: string | null
  department: string | null
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
  department?: string | null
}

export interface ProjectUpdateRequest {
  name?: string | null
  owner?: string | null
  business_unit?: string | null
  department?: string | null
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
  host_details?: BillHostDetail[]
  previous_total_cost?: number | null
  policy_denominator?: string
  policy_weight_mode?: string
}

export interface BillLine {
  unit_id: string
  host_id: string
  share: number
  amount: number
  unit_name?: string
  host_name?: string
  host_ip?: string | null
  host_monthly_cost?: number
  mem_request_total?: number
  mem_total?: number
}

export interface BillHostDetail {
  host_id: string
  name: string
  ip: string | null
  monthly_cost: number
  mem_total: number
  allocated_cost: number
  allocated_share: number
  idle_share: number
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

// ── Consuming Unit Create ────────────────────────────────────────────

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

// ── Department Billing Aggregation ───────────────────────────────

export interface DepartmentBillingItem {
  department: string
  project_count: number
  total_cost: number
  billing_enabled_count: number
}

export interface DepartmentBillingResponse {
  period: string
  items: DepartmentBillingItem[]
  grand_total: number
}
