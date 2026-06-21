/**
 * 成本核算相关 API
 */
import request from './request'

// ── Departments ──────────────────────────────────────────

export interface Department {
  id: number
  name: string
  code: string
}

export async function fetchDepartments(): Promise<Department[]> {
  return request.get('/api/departments')
}

export async function createDepartment(data: { name: string; code: string }): Promise<Department> {
  return request.post('/api/departments', data)
}

export async function updateDepartment(id: number, data: { name?: string; code?: string }): Promise<Department> {
  return request.put(`/api/departments/${id}`, data)
}

export async function deleteDepartment(id: number): Promise<void> {
  return request.delete(`/api/departments/${id}`)
}

// ── Asset Cost ───────────────────────────────────────────

export interface DepreciationInfo {
  purchase_price: number | null
  purchase_date: string | null
  depreciation_months: number | null
  residual_rate: number | null
  depreciation_method: string
  end_of_life_strategy: string
  months_elapsed: number
  monthly_depr: number
  accumulated_depr: number
  net_value: number
  remaining_months: number
  strategy: string
  is_expired: boolean
}

export interface AssetCostDetail {
  asset_id: number
  asset_no: string
  full_loaded_monthly: number
  daily_rate: number
  annual_cost: number
  direct_monthly: number
  allocation_monthly: number
  cost_breakdown: Record<string, number>
  depreciation_info: DepreciationInfo
  allocation_details: Array<{
    from_asset_id: number
    from_asset_no: string
    relation_type: string
    amount: number
  }>
}

export async function fetchAssetCost(assetId: number): Promise<AssetCostDetail> {
  return request.get(`/api/assets/${assetId}/cost`)
}

// ── Cost Summary ─────────────────────────────────────────

export interface GovernanceItem {
  type: string
  severity: string
  asset_id?: number
  asset_no?: string
  monthly_cost?: number
  remaining_months?: number
  count?: number
  message: string
}

export interface CostSummary {
  total_monthly: number
  annualized: number
  capex_ratio: number
  opex_ratio: number
  capex_monthly: number
  opex_monthly: number
  new_cost_assets: number
  missing_cost_data: number
  dept_ranking: Array<{ name: string; monthly_cost: number }>
  type_breakdown: Array<{ name: string; value: number }>
  governance: GovernanceItem[]
  governance_count: number
}

export async function fetchCostSummary(): Promise<CostSummary> {
  return request.get('/api/cost/summary')
}

// ── Department Billing ───────────────────────────────────

export interface BillingResource {
  asset_id: number
  asset_no: string
  hostname: string | null
  ip_address: string
  asset_type: string
  billing_mode: string
  monthly_cost: number
  daily_rate: number
  days_used: number
  period_amount: number
  cost_breakdown: Record<string, number>
}

export interface DepartmentBill {
  dept_id: number
  date_from: string
  date_to: string
  granularity: string
  bill_days: number
  total: number
  daily_avg: number
  annualized: number
  resources: BillingResource[]
  cost_type_totals: Record<string, number>
  resource_count: number
}

export async function fetchDepartmentBill(
  deptId: number,
  dateFrom: string,
  dateTo: string,
  granularity: string = 'month',
): Promise<DepartmentBill> {
  return request.get(`/api/billing/department/${deptId}`, {
    params: { from: dateFrom, to: dateTo, granularity },
  })
}

// ── Cost Rates ───────────────────────────────────────────

export interface CostRateEntry {
  value: string
  description: string | null
  updated_at: string | null
}

export async function fetchCostRates(): Promise<Record<string, CostRateEntry>> {
  return request.get('/api/cost/rates')
}

export async function updateCostRates(rates: Record<string, unknown>): Promise<{ updated: string[] }> {
  return request.put('/api/cost/rates', rates)
}

// ── Asset Relations ──────────────────────────────────────

export interface AssetRelation {
  id: number
  source_asset_id: number
  target_asset_id: number
  relation_type: string
  driver_type: string
  driver_value: number | null
  effective_from: string | null
  effective_to: string | null
}

export async function fetchAssetRelations(assetId: number): Promise<AssetRelation[]> {
  return request.get(`/api/assets/${assetId}/relations`)
}

export async function createAssetRelation(
  assetId: number,
  data: Omit<AssetRelation, 'id'>,
): Promise<AssetRelation> {
  return request.post(`/api/assets/${assetId}/relations`, data)
}

export async function deleteAssetRelation(assetId: number, relationId: number): Promise<void> {
  return request.delete(`/api/assets/${assetId}/relations/${relationId}`)
}
