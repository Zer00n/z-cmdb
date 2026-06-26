<script setup lang="ts">
/**
 * Project Architecture page — /projects/:id
 * Contains: Vue Flow topology graph, component table, and billing tab.
 */
import { ref, onMounted, computed, markRaw } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'

import HostGroupNode from '@/components/topology/HostGroupNode.vue'
import UnitNode from '@/components/topology/UnitNode.vue'
import { computeTopologyLayout } from '@/utils/topologyLayout'

import {
  fetchProject, fetchProjectTopology, fetchProjectUnits, fetchProjectBill,
  createUnit, createPlacement, searchHosts,
  patchUnit, deleteUnit,
  updateProject,
  createRelation, deleteRelation,
} from '@/api/project'
import { fetchDepartments } from '@/api/cost'
import type { Department } from '@/api/cost'
import type {
  Project, TopologyResponse, ConsumingUnit, BillSnapshot,
  ConsumingUnitPatch, ConsumingUnitCreate, HostSearchResult,
  TopologyDependency, RelType,
} from '@/types/project'

const { t } = useI18n()
const route = useRoute()
const projectId = computed(() => route.params.id as string)

const loading = ref(true)
const project = ref<Project | null>(null)
const topology = ref<TopologyResponse | null>(null)
const units = ref<ConsumingUnit[]>([])
const bill = ref<BillSnapshot | null>(null)
const activeTab = ref('overview')
const departmentOptions = ref<Department[]>([])

// ── Vue Flow layout ────────────────────────────────────────────

const { fitView } = useVueFlow()

const nodeTypes: Record<string, any> = {
  hostGroup: markRaw(HostGroupNode),
  unit: markRaw(UnitNode),
}

const layoutResult = computed(() => {
  if (!topology.value) return { nodes: [], edges: [] }
  return computeTopologyLayout(topology.value)
})

// ── Add Consuming Unit dialog state ──
const showAddUnitDialog = ref(false)
const addUnitStep = ref(0) // 0 = basic, 1 = deploy
const addUnitSaving = ref(false)
const addUnitForm = ref<{
  name: string
  type: string
  owner: string
  environment: string
}>({ name: '', type: 'docker', owner: '', environment: 'prod' })
const addDeployForm = ref<{
  host_id: string
  cpu_request: number
  mem_request: number
  instances: number
}>({ host_id: '', cpu_request: 1, mem_request: 512, instances: 1 })
const hostSearchQuery = ref('')
const hostSearchResults = ref<HostSearchResult[]>([])
const hostSearching = ref(false)
const selectedHost = ref<HostSearchResult | null>(null)

// ── Manage Dependencies dialog state ──
const showDepsDialog = ref(false)
const depsDialogUnit = ref<ConsumingUnit | null>(null)
const depsForm = ref<{ target_unit_id: string; rel_type: RelType }>({ target_unit_id: '', rel_type: 'HTTP' })
const depsSaving = ref(false)

// Current period for billing
const currentPeriod = computed(() => {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
})

// Host lookup: host_id → display string
const hostMap = computed(() => {
  const map: Record<string, string> = {}
  if (topology.value) {
    for (const h of topology.value.hosts) {
      map[h.id] = h.ip_address ? `${h.name} (${h.ip_address})` : h.name
    }
  }
  return map
})

// Dependencies for the unit currently being edited
const currentUnitDeps = computed<TopologyDependency[]>(() => {
  if (!depsDialogUnit.value || !topology.value) return []
  return topology.value.dependencies.filter(d => d.source === depsDialogUnit.value!.id)
})

// Units available as dependency targets (exclude current unit)
const availableTargets = computed(() => {
  if (!depsDialogUnit.value) return []
  return units.value.filter(u => u.id !== depsDialogUnit.value!.id)
})

// Unit name lookup
const unitNameMap = computed(() => {
  const map: Record<string, string> = {}
  for (const u of units.value) {
    map[u.id] = u.name
  }
  return map
})

// ── Billing helpers ────────────────────────────────────────────

const billDetail = computed(() => bill.value?.detail as any || null)

const billHostCostTotal = computed(() => {
  if (!billDetail.value?.host_details) return 0
  return billDetail.value.host_details.reduce((sum: number, h: any) => sum + h.monthly_cost, 0)
})

const costChangePercent = computed(() => {
  if (!billDetail.value?.previous_total_cost || !bill.value?.total_cost) return null
  const prev = billDetail.value.previous_total_cost
  const curr = bill.value.total_cost
  if (prev === 0) return null
  return ((curr - prev) / prev) * 100
})

const periodRange = computed(() => {
  if (!bill.value?.period) return ''
  const [y, m] = bill.value.period.split('-')
  const lastDay = new Date(parseInt(y), parseInt(m), 0).getDate()
  return `${y}-${m}-01 ~ ${m}-${String(lastDay).padStart(2, '0')}`
})

function policyModeLabel(mode: string): string {
  const map: Record<string, string> = {
    mem: t('project.billing.memMode'),
    cpu: t('project.billing.cpuMode'),
    weighted: t('project.billing.weightedMode'),
    max: t('project.billing.maxMode'),
  }
  return map[mode] || mode
}

function denomLabel(denom: string): string {
  return denom === 'allocatable'
    ? t('project.billing.denomAllocatable')
    : t('project.billing.denomSumRequests')
}

function formatMem(mb: number): string {
  if (mb >= 1024) return `${(mb / 1024).toFixed(1)}G`
  return `${Math.round(mb)}MB`
}

// Shared hosts for the explanation module
const sharedHosts = computed(() => {
  if (!topology.value || !billDetail.value?.host_details) return []
  const sharedIds = new Set(
    topology.value.hosts.filter(h => h.shared).map(h => h.id)
  )
  return billDetail.value.host_details.filter((h: any) => sharedIds.has(h.host_id))
})

function isHostShared(hostId: string): boolean {
  if (!topology.value) return false
  const host = topology.value.hosts.find(h => h.id === hostId)
  return host?.shared || false
}

function getHostLines(hostId: string): any[] {
  if (!billDetail.value?.lines) return []
  return billDetail.value.lines.filter((l: any) => l.host_id === hostId)
}

async function loadData() {
  loading.value = true
  try {
    const [proj, topo, unitList] = await Promise.all([
      fetchProject(projectId.value),
      fetchProjectTopology(projectId.value),
      fetchProjectUnits(projectId.value),
    ])
    project.value = proj
    origProjectFields.value = { owner: proj.owner || '', business_unit: proj.business_unit || '', department: proj.department || '' }
    topology.value = topo
    units.value = unitList

    // Load bill if billing enabled
    if (proj.billing_enabled) {
      try {
        bill.value = await fetchProjectBill(projectId.value, currentPeriod.value)
      } catch { /* ignore */ }
    }
  } catch (e: any) {
    ElMessage.error(e?.message || t('project.architecture.loadError'))
  } finally {
    loading.value = false
  }
}

async function reloadTopology() {
  try {
    topology.value = await fetchProjectTopology(projectId.value)
  } catch { /* ignore */ }
}

async function handlePatchUnit(unitId: string, field: string, value: any) {
  try {
    const patch: ConsumingUnitPatch = { [field]: value }
    await patchUnit(unitId, patch)
    ElMessage.success(t('project.architecture.updated'))
    units.value = await fetchProjectUnits(projectId.value)
  } catch (e: any) {
    ElMessage.error(e?.message || t('project.architecture.updateError'))
  }
}

const origProjectFields = ref<Record<string, string>>({})

async function handleProjectFieldBlur(field: string) {
  if (!project.value) return
  const newVal = ((project.value as any)[field] || '').trim()
  const oldVal = origProjectFields.value[field] ?? ''
  if (newVal === oldVal) return
  try {
    await updateProject(projectId.value, { [field]: newVal || null })
    origProjectFields.value[field] = newVal
    if (!newVal) (project.value as any)[field] = null
    ElMessage.success(t('project.architecture.updated'))
  } catch (e: any) {
    ElMessage.error(e?.message || t('project.architecture.updateError'))
    ;(project.value as any)[field] = oldVal || null
  }
}

async function handleToggleBilling(val: boolean) {
  if (!project.value) return
  try {
    await updateProject(projectId.value, { billing_enabled: val ? 1 : 0 })
    project.value.billing_enabled = val ? 1 : 0
    ElMessage.success(t('project.architecture.updated'))
    if (val) {
      try {
        bill.value = await fetchProjectBill(projectId.value, currentPeriod.value)
      } catch { /* ignore */ }
    }
  } catch (e: any) {
    ElMessage.error(e?.message || t('project.architecture.updateError'))
  }
}

async function handleDeleteUnit(unitId: string, unitName: string) {
  try {
    await deleteUnit(unitId)
    ElMessage.success(t('project.architecture.deleted'))
    units.value = await fetchProjectUnits(projectId.value)
    await reloadTopology()
  } catch (e: any) {
    ElMessage.error(e?.message || t('project.architecture.deleteError'))
  }
}

// ── Manage Dependencies logic ──

function openDepsDialog(unit: ConsumingUnit) {
  depsDialogUnit.value = unit
  depsForm.value = { target_unit_id: '', rel_type: 'HTTP' }
  showDepsDialog.value = true
}

async function handleAddDep() {
  if (!depsDialogUnit.value || !depsForm.value.target_unit_id) return
  depsSaving.value = true
  try {
    await createRelation({
      source_unit_id: depsDialogUnit.value.id,
      target_unit_id: depsForm.value.target_unit_id,
      rel_type: depsForm.value.rel_type,
    })
    ElMessage.success(t('project.architecture.depAdded'))
    depsForm.value.target_unit_id = ''
    await reloadTopology()
  } catch (e: any) {
    ElMessage.error(e?.message || t('project.architecture.updateError'))
  } finally {
    depsSaving.value = false
  }
}

async function handleDeleteDep(depId: string) {
  try {
    await deleteRelation(depId)
    ElMessage.success(t('project.architecture.depDeleted'))
    await reloadTopology()
  } catch (e: any) {
    ElMessage.error(e?.message || t('project.architecture.updateError'))
  }
}

// ── Add Consuming Unit logic ──

function openAddUnitDialog() {
  addUnitStep.value = 0
  addUnitForm.value = { name: '', type: 'docker', owner: '', environment: 'prod' }
  addDeployForm.value = { host_id: '', cpu_request: 1, mem_request: 512, instances: 1 }
  hostSearchQuery.value = ''
  hostSearchResults.value = []
  selectedHost.value = null
  showAddUnitDialog.value = true
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
async function onHostSearch(query: string) {
  hostSearchQuery.value = query
  if (!query || query.length < 2) { hostSearchResults.value = []; return }
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(async () => {
    hostSearching.value = true
    try {
      hostSearchResults.value = await searchHosts(query)
    } catch { hostSearchResults.value = [] }
    finally { hostSearching.value = false }
  }, 300)
}

async function handleAddUnit() {
  addUnitSaving.value = true
  try {
    const unitData: ConsumingUnitCreate = {
      name: addUnitForm.value.name,
      type: addUnitForm.value.type as any,
      owner: addUnitForm.value.owner || undefined,
      environment: addDeployForm.value.host_id ? addUnitForm.value.environment as any : undefined,
      project_id: projectId.value,
    }
    const unit = await createUnit(unitData)

    if (addDeployForm.value.host_id) {
      await createPlacement(unit.id, {
        host_id: addDeployForm.value.host_id,
        cpu_request: addDeployForm.value.cpu_request,
        mem_request: addDeployForm.value.mem_request,
        instances: addDeployForm.value.instances,
        source: 'manual',
      })
    }

    ElMessage.success(t('project.architecture.addUnit.success'))
    showAddUnitDialog.value = false
    units.value = await fetchProjectUnits(projectId.value)
    await reloadTopology()
  } catch (e: any) {
    ElMessage.error(e?.message || t('project.architecture.addUnit.error'))
  } finally {
    addUnitSaving.value = false
  }
}

onMounted(async () => {
  loadData()
  try { departmentOptions.value = await fetchDepartments() } catch { /* ignore */ }
})
</script>

<template>
  <div class="ui-page" v-loading="loading">
    <!-- Breadcrumb -->
    <div class="v06-crumb">
      <router-link to="/projects">{{ t('project.architecture.breadcrumbProjects') }}</router-link>
      <span class="v06-crumb-sep">/</span>
      <span class="v06-crumb-here">{{ project?.name }}</span>
    </div>

    <!-- Project Info Header Card -->
    <div v-if="project" class="v06-proj-header">
      <span class="v06-proj-name">{{ project.name }}</span>
      <span class="v06-proj-sep"></span>
      <div class="v06-proj-field"><div class="lbl">{{ t('project.list.colOwner') }}</div><div class="val"><input class="v06-proj-input" :value="project.owner || ''" @input="project.owner = ($event.target as HTMLInputElement).value || null" @blur="handleProjectFieldBlur('owner')" @keyup.enter="($event.target as HTMLInputElement).blur()" /></div></div>
      <span class="v06-proj-sep"></span>
      <div class="v06-proj-field"><div class="lbl">{{ t('project.list.colBusinessUnit') }}</div><div class="val">{{ project.business_unit || '-' }}</div></div>
      <span class="v06-proj-sep"></span>
      <div class="v06-proj-field"><div class="lbl">{{ t('project.list.colDepartment') }}</div>
        <div class="val">
          <el-select
            :model-value="project.department || ''"
            clearable filterable size="small"
            :placeholder="t('project.list.selectDepartment')"
            @update:model-value="(val: string) => { project!.department = val || null; handleProjectFieldBlur('department') }"
          >
            <el-option v-for="dept in departmentOptions" :key="dept.id" :label="dept.name" :value="dept.name" />
          </el-select>
        </div>
      </div>
      <span class="v06-proj-sep"></span>
      <div class="v06-proj-field"><div class="lbl">{{ t('project.list.colUnits') }}</div><div class="val">{{ units.length }}</div></div>
      <span class="v06-proj-sep"></span>
      <div class="v06-proj-field"><div class="lbl">{{ t('project.list.colBillingMode') }}</div>
        <div class="val">
          <el-switch
            :model-value="!!project.billing_enabled"
            :active-text="t('project.billing.enabled')"
            :inactive-text="t('project.billing.disabled')"
            @change="handleToggleBilling"
          />
        </div>
      </div>
    </div>

    <!-- Tab Bar -->
    <div v-if="project" class="v06-tab-bar">
      <div class="v06-tab-item" :class="{ active: activeTab === 'overview' }" @click="activeTab = 'overview'">{{ t('project.architecture.tabOverview') }}</div>
      <div class="v06-tab-item" :class="{ active: activeTab === 'billing' }" @click="activeTab = 'billing'">{{ t('project.architecture.tabBilling') }}</div>
    </div>

    <!-- Tab 1: Architecture Overview -->
    <div v-if="activeTab === 'overview' && project">
      <!-- Topology Card (full width, Vue Flow) -->
      <div class="v06-card v06-topology-card">
        <div class="v06-card-head">
          <h3>{{ t('project.architecture.topologyTitle') }}</h3>
        </div>
        <div class="v06-topology-canvas-wrap">
          <VueFlow
            v-if="topology && layoutResult.nodes.length > 0"
            :nodes="layoutResult.nodes"
            :edges="layoutResult.edges"
            :node-types="nodeTypes"
            :default-edge-options="{ type: 'smoothstep', markerEnd: 'arrowclosed' }"
            :nodes-draggable="false"
            :nodes-connectable="false"
            :edges-updatable="false"
            :min-zoom="0.2"
            :max-zoom="2"
            :fit-view-on-init="true"
            class="v06-topology-canvas"
          >
            <Background :gap="20" :size="1" pattern-color="#E2E8F0" />
            <Controls position="bottom-right" />
          </VueFlow>
          <div v-else-if="topology" class="v06-topo-empty">
            <p>{{ t('project.architecture.noTopologyData') }}</p>
          </div>
        </div>
        <div class="v06-card-foot">
          <span>{{ t('project.architecture.dataSource') }}</span>
          <span>{{ t('project.architecture.deterministic') }}</span>
        </div>
      </div>

      <!-- Component Table -->
      <div class="v06-card v06-comp-card">
        <div class="v06-card-head">
          <h3>{{ t('project.architecture.componentTable.title') }}</h3>
          <el-button size="small" type="primary" @click="openAddUnitDialog">
            {{ t('project.architecture.componentTable.addUnit') }}
          </el-button>
        </div>
        <el-table :data="units" :header-cell-style="{ fontWeight: 600, fontSize: '13px' }">
          <el-table-column :label="t('project.architecture.componentTable.editable')" :label-class-name="'v06-col-group-edit'" min-width="150">
            <template #default="{ row }">
              <el-input v-model="row.name" size="small" @blur="handlePatchUnit(row.id, 'name', row.name)" @keyup.enter="($event.target as HTMLInputElement).blur()" />
            </template>
          </el-table-column>
          <el-table-column :label="t('project.architecture.componentTable.colType')" :label-class-name="'v06-col-group-edit'" width="140">
            <template #default="{ row }">
              <el-select :model-value="row.type" size="small" @change="handlePatchUnit(row.id, 'type', $event)">
                <el-option :label="t('project.architecture.typeK8s')" value="k8s_workload" />
                <el-option :label="t('project.architecture.typeDocker')" value="docker" />
                <el-option :label="t('project.architecture.typeVmApp')" value="vm_app" />
                <el-option :label="t('project.architecture.typeHostProcess')" value="host_process" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column :label="t('project.architecture.componentTable.colOwner')" :label-class-name="'v06-col-group-edit'" width="120">
            <template #default="{ row }">
              <el-input v-model="row.owner" size="small" @blur="handlePatchUnit(row.id, 'owner', row.owner || null)" @keyup.enter="($event.target as HTMLInputElement).blur()" />
            </template>
          </el-table-column>
          <el-table-column :label="t('project.architecture.componentTable.colEnv')" :label-class-name="'v06-col-group-edit'" width="120">
            <template #default="{ row }">
              <el-select :model-value="row.environment" size="small" @change="handlePatchUnit(row.id, 'environment', $event)">
                <el-option :label="t('project.architecture.envProd')" value="prod" />
                <el-option :label="t('project.architecture.envStaging')" value="staging" />
                <el-option :label="t('project.architecture.envDev')" value="dev" />
              </el-select>
            </template>
          </el-table-column>
          <!-- Read-only columns -->
          <el-table-column :label="t('project.architecture.componentTable.colInstances')" :label-class-name="'v06-col-group-read'" width="100" align="center" :class-name="'v06-td-read'">
            <template #default="{ row }">
              <span v-if="row.runtime" class="v06-read-cell">
                🔒 {{ row.runtime.instances }}
              </span>
            </template>
          </el-table-column>
          <el-table-column :label="t('project.architecture.componentTable.colHost')" :label-class-name="'v06-col-group-read'" width="120" :class-name="'v06-td-read'">
            <template #default="{ row }">
              <span class="v06-read-cell">{{ hostMap[row.host_id] || row.host_id || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="t('project.architecture.componentTable.colCpu')" :label-class-name="'v06-col-group-read'" width="100" :class-name="'v06-td-read'">
            <template #default="{ row }">
              <span v-if="row.runtime" class="v06-read-cell">{{ t('project.architecture.componentTable.runtimeCore', { count: row.runtime.cpu }) }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="t('project.architecture.componentTable.colMem')" :label-class-name="'v06-col-group-read'" width="100" :class-name="'v06-td-read'">
            <template #default="{ row }">
              <span v-if="row.runtime" class="v06-read-cell">{{ t('project.architecture.componentTable.runtimeMem', { count: row.runtime.mem }) }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="t('project.architecture.componentTable.colActions')" width="160" align="center" fixed="right">
            <template #default="{ row }">
              <div class="v06-action-btns">
                <el-button type="primary" link size="small" @click="openDepsDialog(row)">
                  {{ t('project.architecture.manageDeps') }}
                </el-button>
                <el-popconfirm
                  :title="t('project.architecture.confirmDelete', { name: row.name })"
                  @confirm="handleDeleteUnit(row.id, row.name)"
                >
                  <template #reference>
                    <el-button type="danger" link size="small">
                      {{ t('project.architecture.componentTable.btnDelete') }}
                    </el-button>
                  </template>
                </el-popconfirm>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- Tab 2: Project Billing -->
    <div v-if="activeTab === 'billing' && project">
      <!-- Empty state: billing not enabled -->
      <div v-if="!project.billing_enabled" class="v06-empty-billing">
        <div class="v06-empty-billing-icon">💰</div>
        <h3 style="margin: 0 0 8px; color: var(--neutral-700)">{{ t('project.billing.noBilling') }}</h3>
        <p style="margin: 0; color: var(--neutral-500)">{{ t('project.billing.noBillingDesc') }}</p>
      </div>

      <!-- Billing data loaded -->
      <div v-else-if="bill && billDetail">
        <!-- Status bar -->
        <div class="v06-billing-status">
          <span class="v06-status-item">
            <span class="v06-status-dot"></span>
            {{ t('project.billing.billingMode') }}: {{ t('project.billing.enabled') }}
          </span>
          <span class="v06-status-sep">|</span>
          <span class="v06-status-item">
            {{ t('project.billing.activePolicy') }}:
            <router-link to="/settings/billing-policy" class="v06-policy-link">
              {{ t('project.billing.policyVersion', { version: bill.policy_version }) }}
              ({{ policyModeLabel(billDetail.policy_weight_mode || 'mem') }})
            </router-link>
          </span>
          <span class="v06-status-sep">|</span>
          <span class="v06-status-item">
            {{ t('project.billing.periodRange') }}: {{ periodRange }}
          </span>
        </div>

        <!-- Three summary cards -->
        <div class="v06-metrics">
          <!-- Card 1: Monthly total -->
          <div class="v06-metric-card v06-metric-primary">
            <div class="v06-metric-label">{{ t('project.billing.totalCost') }}</div>
            <div class="v06-metric-value">¥{{ (bill.total_cost || 0).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 }) }}</div>
            <div v-if="costChangePercent !== null" class="v06-metric-change" :class="{ up: costChangePercent > 0, down: costChangePercent < 0 }">
              {{ costChangePercent > 0 ? t('project.billing.up') : t('project.billing.down') }}
              {{ Math.abs(costChangePercent).toFixed(1) }}% {{ t('project.billing.vsLastMonth') }}
            </div>
            <div v-else class="v06-metric-change neutral">{{ t('project.billing.noPrevious') }}</div>
          </div>

          <!-- Card 2: Host cost total -->
          <div class="v06-metric-card">
            <div class="v06-metric-label">{{ t('project.billing.hostCost') }}</div>
            <div class="v06-metric-value">¥{{ billHostCostTotal.toLocaleString() }}</div>
            <div class="v06-metric-hosts">
              <span v-for="h in billDetail.host_details" :key="h.host_id" class="v06-host-chip">
                {{ h.name }}
                <span class="v06-host-chip-cost">¥{{ h.monthly_cost.toLocaleString() }}</span>
              </span>
            </div>
          </div>

          <!-- Card 3: Unallocated bucket -->
          <div class="v06-metric-card">
            <div class="v06-metric-label">{{ t('project.billing.unallocated') }}</div>
            <div class="v06-metric-value">¥{{ (billDetail.bucket_idle || 0).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 }) }}</div>
            <div class="v06-metric-desc">
              {{ billDetail.bucket_idle > 0
                ? t('project.billing.hasIdle', { amount: billDetail.bucket_idle.toLocaleString(undefined, { maximumFractionDigits: 2 }) })
                : t('project.billing.noIdle')
              }}
            </div>
          </div>
        </div>

        <!-- Cost breakdown table -->
        <div class="v06-card v06-billing-table-card">
          <div class="v06-card-head"><h3>{{ t('project.billing.costBreakdown') }}</h3></div>
          <el-table
            :data="billDetail.lines || []"
            :header-cell-style="{ background: '#F8FAFC', color: '#334155', fontWeight: 600, fontSize: '13px' }"
            show-summary
            :summary-method="() => []"
            border
          >
            <!-- Consuming Unit -->
            <el-table-column :label="t('project.billing.colUnit')" min-width="140">
              <template #default="{ row }">
                <span class="v06-bill-unit-name">{{ row.unit_name || unitNameMap[row.unit_id] || row.unit_id }}</span>
              </template>
            </el-table-column>

            <!-- Host -->
            <el-table-column :label="t('project.billing.colHost')" min-width="160">
              <template #default="{ row }">
                <div class="v06-bill-host-cell">
                  <span>{{ row.host_name || hostMap[row.host_id] || '-' }}</span>
                  <el-tag v-if="isHostShared(row.host_id)" size="small" type="warning" class="v06-shared-badge">
                    {{ t('project.billing.sharedNode') }}
                  </el-tag>
                </div>
              </template>
            </el-table-column>

            <!-- Host monthly cost -->
            <el-table-column :label="t('project.billing.colHostCost')" width="130" align="right">
              <template #default="{ row }">
                <span class="v06-mono">¥{{ (row.host_monthly_cost || 0).toLocaleString() }}</span>
              </template>
            </el-table-column>

            <!-- Memory share -->
            <el-table-column :label="t('project.billing.colMemShare')" width="180" align="center">
              <template #default="{ row }">
                <div class="v06-mem-cell">
                  <span class="v06-mono">{{ formatMem(row.mem_request_total || 0) }} / {{ formatMem(row.mem_total || 0) }}</span>
                  <el-progress
                    :percentage="Math.round((row.share || 0) * 100)"
                    :stroke-width="6"
                    :show-text="false"
                    style="width: 80px; margin-top: 2px;"
                  />
                  <span class="v06-mono v06-mem-pct">{{ Math.round((row.share || 0) * 100) }}%</span>
                </div>
              </template>
            </el-table-column>

            <!-- Monthly allocated cost -->
            <el-table-column :label="t('project.billing.colAmount')" width="140" align="right">
              <template #default="{ row }">
                <span class="v06-mono v06-amount">¥{{ (row.amount || 0).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 }) }}</span>
              </template>
            </el-table-column>

            <!-- % of project total -->
            <el-table-column :label="t('project.billing.colPercent')" width="160">
              <template #default="{ row }">
                <div class="v06-pct-cell">
                  <el-progress
                    :percentage="bill.total_cost > 0 ? Math.round((row.amount / bill.total_cost) * 100) : 0"
                    :stroke-width="8"
                    :color="bill.total_cost > 0 && row.amount / bill.total_cost > 0.5 ? '#F59E0B' : '#3B82F6'"
                    style="width: 80px;"
                  />
                </div>
              </template>
            </el-table-column>
          </el-table>

          <!-- Table footer: project total -->
          <div class="v06-billing-table-footer">
            <span class="v06-footer-label">{{ t('project.billing.tableTotal') }}</span>
            <span class="v06-footer-value">¥{{ (bill.total_cost || 0).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 }) }}</span>
          </div>
        </div>

        <!-- Shared host explanation module -->
        <div v-if="sharedHosts.length > 0" class="v06-card v06-share-explain-card">
          <div class="v06-card-head">
            <h3>{{ t('project.billing.shareExplanation') }}</h3>
          </div>
          <div class="v06-card-body">
            <div v-for="sh in sharedHosts" :key="sh.host_id" class="v06-share-block">
              <div class="v06-share-header">
                <strong>{{ sh.name }}</strong>
                <span class="v06-share-cost">{{ t('project.billing.shareFormula', { host: sh.name, cost: sh.monthly_cost.toLocaleString() }) }}</span>
              </div>
              <div class="v06-share-dimension">
                {{ t('project.billing.shareDimension', { dimension: denomLabel(billDetail.policy_denominator || 'allocatable') }) }}
              </div>
              <div class="v06-share-lines">
                <div v-for="line in getHostLines(sh.host_id)" :key="line.unit_id" class="v06-share-line">
                  {{ t('project.billing.shareLine', {
                    unit: line.unit_name,
                    used: formatMem(line.mem_request_total || 0),
                    total: formatMem(line.mem_total || 0),
                    pct: Math.round((line.share || 0) * 100),
                    amount: (line.amount || 0).toLocaleString(undefined, { maximumFractionDigits: 2 }),
                    target: t('project.billing.thisProject'),
                  }) }}
                </div>
              </div>
              <div class="v06-share-conservation">
                {{ sh.idle_share > 0
                  ? t('project.billing.shareIdleAmount', { amount: (sh.monthly_cost * sh.idle_share).toLocaleString(undefined, { maximumFractionDigits: 2 }) })
                  : t('project.billing.shareIdleOk')
                }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- No data state -->
      <div v-else-if="project.billing_enabled" class="v06-empty-billing">
        <div class="v06-empty-billing-icon">📊</div>
        <h3 style="margin: 0 0 8px; color: var(--neutral-700)">{{ t('project.billing.noData') }}</h3>
      </div>
    </div>

    <!-- Manage Dependencies Dialog -->
    <el-dialog
      v-model="showDepsDialog"
      :title="t('project.architecture.manageDeps') + (depsDialogUnit ? ` — ${depsDialogUnit.name}` : '')"
      width="520px"
      :close-on-click-modal="false"
    >
      <div v-if="depsDialogUnit" class="v06-deps-dialog">
        <!-- Existing dependencies -->
        <div class="v06-deps-section">
          <h4>{{ t('project.architecture.existingDeps') }}</h4>
          <div v-if="currentUnitDeps.length === 0" class="v06-deps-empty">
            {{ t('project.architecture.noDeps') }}
          </div>
          <div v-for="dep in currentUnitDeps" :key="dep.id" class="v06-dep-row">
            <span class="v06-dep-arrow">
              {{ depsDialogUnit.name }} → {{ unitNameMap[dep.target] || dep.target }}
            </span>
            <el-tag size="small" class="v06-dep-type-tag">{{ dep.type }}</el-tag>
            <el-button type="danger" link size="small" @click="handleDeleteDep(dep.id)">
              {{ t('project.architecture.componentTable.btnDelete') }}
            </el-button>
          </div>
        </div>

        <el-divider />

        <!-- Add new dependency -->
        <div class="v06-deps-section">
          <h4>{{ t('project.architecture.addDep') }}</h4>
          <el-form label-position="top" :inline="false">
            <el-form-item :label="t('project.architecture.depTarget')">
              <el-select
                v-model="depsForm.target_unit_id"
                :placeholder="t('project.architecture.selectTarget')"
                filterable
                style="width: 100%"
              >
                <el-option
                  v-for="u in availableTargets"
                  :key="u.id"
                  :label="u.name"
                  :value="u.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('project.architecture.depType')">
              <el-select v-model="depsForm.rel_type" style="width: 100%">
                <el-option label="HTTP" value="HTTP" />
                <el-option label="SQL" value="SQL" />
                <el-option label="cache" value="cache" />
                <el-option label="mq" value="mq" />
                <el-option label="depends" value="depends" />
              </el-select>
            </el-form-item>
          </el-form>
        </div>
      </div>
      <template #footer>
        <el-button @click="showDepsDialog = false">{{ t('project.architecture.addUnit.cancel') }}</el-button>
        <el-button
          type="primary"
          :loading="depsSaving"
          :disabled="!depsForm.target_unit_id"
          @click="handleAddDep"
        >
          {{ t('project.architecture.addDep') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- Add Consuming Unit Dialog -->
    <el-dialog v-model="showAddUnitDialog" :title="t('project.architecture.addUnit.title')" width="560px" :close-on-click-modal="false">
      <!-- Step indicator -->
      <el-steps :active="addUnitStep" finish-status="success" style="margin-bottom: 24px">
        <el-step :title="t('project.architecture.addUnit.stepBasic')" />
        <el-step :title="t('project.architecture.addUnit.stepDeploy')" />
      </el-steps>

      <!-- Step 0: Basic Info -->
      <el-form v-if="addUnitStep === 0" label-position="top">
        <el-form-item :label="t('project.architecture.addUnit.name')" required>
          <el-input v-model="addUnitForm.name" :placeholder="t('project.architecture.addUnit.namePlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('project.architecture.addUnit.type')" required>
          <el-select v-model="addUnitForm.type" style="width: 100%">
            <el-option :label="t('project.architecture.typeK8s')" value="k8s_workload" />
            <el-option :label="t('project.architecture.typeDocker')" value="docker" />
            <el-option :label="t('project.architecture.typeVmApp')" value="vm_app" />
            <el-option :label="t('project.architecture.typeHostProcess')" value="host_process" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('project.architecture.addUnit.owner')">
          <el-input v-model="addUnitForm.owner" :placeholder="t('project.architecture.addUnit.ownerPlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('project.architecture.addUnit.environment')">
          <el-select v-model="addUnitForm.environment" style="width: 100%">
            <el-option :label="t('project.architecture.envProd')" value="prod" />
            <el-option :label="t('project.architecture.envStaging')" value="staging" />
            <el-option :label="t('project.architecture.envDev')" value="dev" />
          </el-select>
        </el-form-item>
      </el-form>

      <!-- Step 1: Deployment Config -->
      <el-form v-if="addUnitStep === 1" label-position="top">
        <el-form-item :label="t('project.architecture.addUnit.hostIp')">
          <el-select
            v-model="addDeployForm.host_id"
            filterable
            remote
            :remote-method="onHostSearch"
            :loading="hostSearching"
            :placeholder="t('project.architecture.addUnit.hostIpPlaceholder')"
            style="width: 100%"
            @change="(val: string) => { selectedHost = hostSearchResults.find(h => h.id === val) || null }"
          >
            <el-option
              v-for="h in hostSearchResults"
              :key="h.id"
              :label="`${h.name} (${h.ip_address || '-'})`"
              :value="h.id"
            />
          </el-select>
          <div v-if="selectedHost" class="v06-host-hint">
            {{ t('project.architecture.addUnit.hostHint', { cpu: selectedHost.cpu_total, mem: selectedHost.mem_total }) }}
          </div>
          <div v-if="hostSearchQuery && hostSearchResults.length === 0 && !hostSearching" class="v06-host-hint" style="color: var(--color-danger)">
            {{ t('project.architecture.addUnit.noHost') }}
          </div>
        </el-form-item>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px">
          <el-form-item :label="t('project.architecture.addUnit.cpuRequest')">
            <el-input-number v-model="addDeployForm.cpu_request" :min="0.1" :step="0.5" style="width:100%" />
          </el-form-item>
          <el-form-item :label="t('project.architecture.addUnit.memRequest')">
            <el-input-number v-model="addDeployForm.mem_request" :min="64" :step="64" style="width:100%" />
          </el-form-item>
          <el-form-item :label="t('project.architecture.addUnit.instances')">
            <el-input-number v-model="addDeployForm.instances" :min="1" :max="1000" style="width:100%" />
          </el-form-item>
        </div>
      </el-form>

      <template #footer>
        <el-button v-if="addUnitStep === 1" @click="addUnitStep = 0">上一步</el-button>
        <el-button @click="showAddUnitDialog = false">{{ t('project.architecture.addUnit.cancel') }}</el-button>
        <el-button v-if="addUnitStep === 0" type="primary" :disabled="!addUnitForm.name.trim()" @click="addUnitStep = 1">下一步</el-button>
        <el-button v-if="addUnitStep === 1" type="primary" :loading="addUnitSaving" @click="handleAddUnit">
          {{ t('project.architecture.addUnit.submit') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
/* ── Breadcrumb ── */
.v06-crumb { font-size: 13px; color: var(--neutral-500); margin-bottom: 4px; }
.v06-crumb a { color: var(--neutral-500); text-decoration: none; }
.v06-crumb a:hover { color: var(--color-primary-500); }
.v06-crumb-sep { margin: 0 6px; color: var(--neutral-300); }
.v06-crumb-here { color: var(--neutral-900); font-weight: 500; }

/* ── Project Header Card ── */
.v06-proj-header {
  background: white; border: 1px solid var(--neutral-200); border-radius: 8px;
  padding: 14px 20px; display: flex; align-items: center; gap: 24px; flex-wrap: wrap;
}
.v06-proj-name { font-size: 18px; font-weight: 700; color: var(--neutral-900); }
.v06-proj-sep { width: 1px; height: 28px; background: var(--neutral-200); }
.v06-proj-field .lbl { font-size: 11px; color: var(--neutral-400); font-family: var(--font-mono); text-transform: uppercase; letter-spacing: 0.06em; }
.v06-proj-field .val { color: var(--neutral-900); font-size: 14px; }
.v06-proj-input {
  width: 120px; border: 1px solid transparent; border-radius: 4px;
  padding: 4px 8px; font-size: 13px; background: transparent;
  outline: none; transition: border-color 0.15s, background 0.15s;
}
.v06-proj-input:hover { border-color: var(--neutral-300); background: var(--neutral-50); }
.v06-proj-input:focus { border-color: var(--color-primary-500); background: white; box-shadow: 0 0 0 2px rgba(59,130,246,0.15); }
.v06-billing-on {
  background: var(--color-success-soft); color: #166534; font-size: 12px; font-weight: 600;
  padding: 3px 10px; border-radius: 4px; display: inline-flex; align-items: center; gap: 5px;
}
.v06-billing-on::before { content: ''; width: 7px; height: 7px; border-radius: 50%; background: var(--color-success); }
.v06-billing-off { color: var(--neutral-400); font-size: 12px; }

/* ── Tab Bar ── */
.v06-tab-bar { display: flex; border-bottom: 1px solid var(--neutral-200); margin-bottom: 20px; }
.v06-tab-item {
  padding: 10px 16px; font-size: 14px; color: var(--neutral-500);
  border-bottom: 2px solid transparent; margin-bottom: -1px; cursor: pointer;
  transition: color 0.12s; user-select: none;
}
.v06-tab-item:hover { color: var(--neutral-900); }
.v06-tab-item.active { color: var(--color-primary-500); border-bottom-color: var(--color-primary-500); font-weight: 500; }

/* ── Architecture Grid ── */
.v06-arch-grid { margin-bottom: 24px; }
.v06-topology-card { width: 100%; margin-bottom: 24px; }

/* ── Card (generic) ── */
.v06-card { background: white; border: 1px solid var(--neutral-200); border-radius: 8px; overflow: hidden; }
.v06-card-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 11px 16px; border-bottom: 1px solid var(--neutral-100); background: var(--neutral-50);
}
.v06-card-head h3 { font-size: 13px; font-weight: 600; color: var(--neutral-900); margin: 0; display: flex; align-items: center; gap: 7px; }
.v06-card-body { padding: 16px; }
.v06-card-foot { padding: 9px 16px; border-top: 1px solid var(--neutral-100); background: var(--neutral-50); font-size: 11px; color: var(--neutral-400); font-family: var(--font-mono); display: flex; gap: 16px; }

/* ── Vue Flow Topology ── */
.v06-topology-canvas-wrap {
  height: 420px;
  background: #FAFBFC;
}
.v06-topology-canvas {
  width: 100%;
  height: 100%;
}
.v06-topo-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--neutral-400);
  font-size: 14px;
}

/* ── Component Table ── */
.v06-comp-card { margin-top: 0; }
.v06-comp-card .v06-card-head h3 { font-size: 15px; }
.v06-col-group-edit { background: var(--color-primary-50) !important; color: var(--color-primary-600) !important; font-size: 11px !important; font-weight: 700 !important; letter-spacing: 0.05em; text-transform: uppercase; border-bottom: 1px solid var(--color-primary-200) !important; }
.v06-col-group-read { background: var(--neutral-100) !important; color: var(--neutral-500) !important; font-size: 11px !important; font-weight: 600 !important; letter-spacing: 0.05em; text-transform: uppercase; border-bottom: 1px solid var(--neutral-200) !important; border-left: 2px solid var(--color-primary-200) !important; }
.v06-read-cell { color: var(--neutral-500); display: flex; align-items: center; gap: 4px; font-family: var(--font-mono); font-size: 12px; }
.v06-action-btns { display: flex; gap: 4px; justify-content: center; }

/* ── Manage Dependencies Dialog ── */
.v06-deps-dialog { }
.v06-deps-section h4 { margin: 0 0 10px; font-size: 13px; font-weight: 600; color: var(--neutral-700); }
.v06-deps-empty { color: var(--neutral-400); font-size: 13px; padding: 8px 0; }
.v06-dep-row {
  display: flex; align-items: center; gap: 8px; padding: 6px 0;
  border-bottom: 1px solid var(--neutral-100);
}
.v06-dep-row:last-child { border-bottom: none; }
.v06-dep-arrow { font-size: 13px; font-family: var(--font-mono); color: var(--neutral-700); flex: 1; }
.v06-dep-type-tag { font-size: 11px; }

/* ── Billing Tab ── */
.v06-billing-status {
  display: flex; align-items: center; gap: 12px; padding: 10px 16px;
  background: white; border: 1px solid var(--neutral-200); border-radius: 8px;
  margin-bottom: 20px; font-size: 13px; color: var(--neutral-600); flex-wrap: wrap;
}
.v06-status-item { display: flex; align-items: center; gap: 6px; }
.v06-status-dot { width: 8px; height: 8px; border-radius: 50%; background: #10B981; }
.v06-status-sep { color: var(--neutral-300); }
.v06-policy-link { color: var(--color-primary-600); text-decoration: none; font-weight: 500; }
.v06-policy-link:hover { text-decoration: underline; }

.v06-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px; }
.v06-metric-card { background: white; border: 1px solid var(--neutral-200); border-radius: 8px; padding: 16px 20px; }
.v06-metric-card.v06-metric-primary { border-left: 3px solid var(--color-primary-500); }
.v06-metric-label { font-size: 12px; color: var(--neutral-500); margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.04em; }
.v06-metric-value { font-size: 26px; font-weight: 700; color: var(--neutral-900); font-family: var(--font-mono); line-height: 1; }
.v06-metric-change { font-size: 12px; margin-top: 6px; font-weight: 500; }
.v06-metric-change.up { color: #EF4444; }
.v06-metric-change.down { color: #10B981; }
.v06-metric-change.neutral { color: var(--neutral-400); }
.v06-metric-hosts { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }
.v06-host-chip {
  display: inline-flex; align-items: center; gap: 4px; font-size: 11px;
  background: var(--neutral-100); border-radius: 4px; padding: 2px 8px; color: var(--neutral-700);
}
.v06-host-chip-cost { font-family: var(--font-mono); color: var(--color-primary-700); font-weight: 600; }
.v06-metric-desc { font-size: 11px; color: var(--neutral-500); margin-top: 6px; }

/* Billing table */
.v06-billing-table-card { margin-bottom: 20px; }
.v06-bill-unit-name { font-weight: 600; color: var(--neutral-900); }
.v06-bill-host-cell { display: flex; align-items: center; gap: 6px; }
.v06-shared-badge { font-size: 10px !important; }
.v06-mono { font-family: var(--font-mono); font-size: 12px; }
.v06-amount { font-weight: 600; color: var(--color-primary-700); }
.v06-mem-cell { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.v06-mem-pct { color: var(--neutral-500); font-size: 11px; }
.v06-pct-cell { display: flex; align-items: center; justify-content: center; }

.v06-billing-table-footer {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 16px; background: var(--neutral-50); border-top: 2px solid var(--neutral-200);
  border-radius: 0 0 8px 8px;
}
.v06-footer-label { font-weight: 700; font-size: 13px; color: var(--neutral-900); }
.v06-footer-value { font-family: var(--font-mono); font-weight: 700; font-size: 18px; color: var(--color-primary-700); }

/* Shared host explanation */
.v06-share-explain-card { margin-bottom: 20px; }
.v06-share-block {
  padding: 14px 0; border-bottom: 1px solid var(--neutral-100);
}
.v06-share-block:last-child { border-bottom: none; }
.v06-share-header { display: flex; align-items: center; gap: 12px; margin-bottom: 6px; }
.v06-share-header strong { font-family: var(--font-mono); font-size: 14px; color: var(--neutral-900); }
.v06-share-cost { font-size: 12px; color: var(--neutral-600); }
.v06-share-dimension { font-size: 12px; color: var(--neutral-500); margin-bottom: 8px; }
.v06-share-lines { display: flex; flex-direction: column; gap: 4px; margin-bottom: 8px; }
.v06-share-line { font-size: 12px; font-family: var(--font-mono); color: var(--neutral-700); padding-left: 16px; }
.v06-share-conservation { font-size: 11px; color: #10B981; font-weight: 500; padding-left: 16px; }

.v06-empty-billing {
  text-align: center; padding: 56px 32px; background: white;
  border: 1px solid var(--neutral-200); border-radius: 8px; color: var(--neutral-400);
}
.v06-empty-billing-icon { width: 48px; height: 48px; background: var(--neutral-100); border-radius: 50%; color: var(--neutral-400); margin: 0 auto 16px; display: flex; align-items: center; justify-content: center; font-size: 24px; }

/* ── Add Unit Dialog ── */
.v06-host-hint { font-size: 12px; color: var(--neutral-500); margin-top: 6px; }
</style>
