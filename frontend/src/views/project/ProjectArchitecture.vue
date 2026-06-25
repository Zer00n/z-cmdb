<script setup lang="ts">
/**
 * Project Architecture page — /projects/:id
 * Contains: topology graph, AI summary, component table, and billing tab.
 */
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  fetchProject, fetchProjectTopology, fetchProjectUnits, fetchProjectBill, fetchProjectSummary,
  regenerateProjectSummary,
  createUnit, createPlacement, searchHosts,
  patchUnit, deleteUnit,
  updateProject,
} from '@/api/project'
import type {
  Project, TopologyResponse, ConsumingUnit, BillSnapshot, ProjectSummary,
  ConsumingUnitPatch, ConsumingUnitCreate, HostSearchResult,
} from '@/types/project'

const { t, locale } = useI18n()
const route = useRoute()
const projectId = computed(() => route.params.id as string)

const loading = ref(true)
const project = ref<Project | null>(null)
const topology = ref<TopologyResponse | null>(null)
const units = ref<ConsumingUnit[]>([])
const bill = ref<BillSnapshot | null>(null)
const summary = ref<ProjectSummary | null>(null)
const summaryLoading = ref(false)
const activeTab = ref('overview')

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

async function loadData() {
  loading.value = true
  try {
    const [proj, topo, unitList] = await Promise.all([
      fetchProject(projectId.value),
      fetchProjectTopology(projectId.value),
      fetchProjectUnits(projectId.value),
    ])
    project.value = proj
    origProjectFields.value = { owner: proj.owner || '', business_unit: proj.business_unit || '' }
    topology.value = topo
    units.value = unitList

    // Load bill if billing enabled
    if (proj.billing_enabled) {
      try {
        bill.value = await fetchProjectBill(projectId.value, currentPeriod.value)
      } catch { /* ignore */ }
    }

    // Load AI summary (cached in DB; passes current locale)
    try {
      const s = await fetchProjectSummary(projectId.value, locale.value)
      if (s && !s.degraded) {
        summary.value = s
      }
    } catch { /* ignore */ }
  } catch (e: any) {
    ElMessage.error(e?.message || t('project.architecture.loadError'))
  } finally {
    loading.value = false
  }
}

async function handlePatchUnit(unitId: string, field: string, value: any) {
  try {
    const patch: ConsumingUnitPatch = { [field]: value }
    await patchUnit(unitId, patch)
    ElMessage.success(t('project.architecture.updated'))
    // Reload units
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
      // Reload bill data after enabling billing
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
  } catch (e: any) {
    ElMessage.error(e?.message || t('project.architecture.deleteError'))
  }
}

async function handleRegenerate() {
  summaryLoading.value = true
  try {
    const s = await regenerateProjectSummary(projectId.value, locale.value)
    if (s && !s.degraded) {
      summary.value = s
    } else {
      summary.value = null
    }
  } catch (e: any) {
    ElMessage.error(e?.message || t('project.architecture.updateError'))
  } finally {
    summaryLoading.value = false
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

function onSelectHost(host: HostSearchResult) {
  selectedHost.value = host
  addDeployForm.value.host_id = host.id
}

async function handleAddUnit() {
  addUnitSaving.value = true
  try {
    // Step 1: Create consuming unit
    const unitData: ConsumingUnitCreate = {
      name: addUnitForm.value.name,
      type: addUnitForm.value.type as any,
      owner: addUnitForm.value.owner || undefined,
      environment: addDeployForm.value.host_id ? addUnitForm.value.environment as any : undefined,
      project_id: projectId.value,
    }
    const unit = await createUnit(unitData)

    // Step 2: Create placement (if host selected)
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
    // Reload units
    units.value = await fetchProjectUnits(projectId.value)
  } catch (e: any) {
    ElMessage.error(e?.message || t('project.architecture.addUnit.error'))
  } finally {
    addUnitSaving.value = false
  }
}

onMounted(loadData)
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
      <div class="v06-arch-grid">
        <!-- Topology Card -->
        <div class="v06-card">
          <div class="v06-card-head">
            <h3>{{ t('project.architecture.topologyTitle') }}</h3>
          </div>
          <div class="v06-card-body" v-if="topology">
            <div v-for="host in topology.hosts" :key="host.id" class="v06-host-group" :class="{ shared: host.shared }">
              <div class="v06-host-label">
                <span class="v06-host-name">{{ host.name }}</span>
                <span v-if="host.ip_address" class="v06-host-ip">{{ host.ip_address }}</span>
                <span class="v06-host-cost">¥{{ host.monthly_cost.toLocaleString() }}</span>
                <el-tag v-if="host.shared" size="small" type="warning">{{ t('project.architecture.shared') }}</el-tag>
              </div>
              <div class="v06-host-units">
                <div v-for="unit in topology.units.filter(u => u.host_id === host.id)" :key="unit.id" class="v06-unit-node">
                  <div class="v06-unit-name">{{ unit.name }}</div>
                  <div class="v06-unit-info">
                    <el-tag size="small">{{ unit.type }}</el-tag>
                    <span v-if="unit.runtime">{{ unit.runtime.instances }}x</span>
                    <span class="v06-unit-owner">{{ unit.owner }}</span>
                  </div>
                </div>
              </div>
              <div v-if="host.shared" class="v06-host-shares">
                <div v-for="share in host.shares" :key="share.project_id">
                  {{ share.project_id }}: {{ Math.round(share.ratio * 100) }}%
                </div>
              </div>
            </div>
            <div v-if="topology.dependencies.length" class="v06-deps-list">
              <h4>{{ t('project.architecture.dependencies') }}</h4>
              <div v-for="dep in topology.dependencies" :key="dep.id" class="v06-dep-item" :class="{ cycle: dep.in_cycle }">
                {{ dep.source }} → {{ dep.target }} ({{ dep.type }})
                <el-tag v-if="dep.in_cycle" size="small" type="warning">{{ t('project.architecture.cycle') }}</el-tag>
              </div>
            </div>
          </div>
          <div class="v06-card-foot">
            <span>{{ t('project.architecture.dataSource') }}</span>
            <span>{{ t('project.architecture.deterministic') }}</span>
          </div>
        </div>

        <!-- AI Summary Card -->
        <div class="v06-ai-card">
          <div class="v06-card-head">
            <h3>{{ t('project.architecture.ai.title') }}</h3>
            <div style="display:flex;align-items:center;gap:8px">
              <span class="v06-ai-badge">{{ t('project.architecture.ai.draft') }}</span>
              <el-button size="small" :loading="summaryLoading" @click="handleRegenerate">
                {{ t('project.architecture.ai.regenerate') }}
              </el-button>
            </div>
          </div>
          <div class="v06-card-body" style="flex:1">
            <div v-if="summary">
              <p class="v06-ai-text">{{ summary.overview }}</p>
              <div v-if="summary.risk" class="v06-ai-risk">
                <strong>{{ t('project.architecture.ai.risk') }}:</strong> {{ summary.risk }}
              </div>
            </div>
            <div v-else class="v06-ai-empty">
              <p>{{ t('project.architecture.ai.unavailable') }}</p>
            </div>
          </div>
          <div class="v06-ai-disclaimer">{{ t('project.architecture.ai.disclaimer') }}</div>
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
          <el-table-column :label="t('project.architecture.componentTable.colActions')" width="80" align="center" fixed="right">
            <template #default="{ row }">
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
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- Tab 2: Project Billing -->
    <div v-if="activeTab === 'billing' && project">
      <div v-if="!project.billing_enabled" class="v06-empty-billing">
        <div class="v06-empty-billing-icon">💰</div>
        <h3 style="margin: 0 0 8px; color: var(--neutral-700)">{{ t('project.billing.noBilling') }}</h3>
        <p style="margin: 0; color: var(--neutral-500)">{{ t('project.billing.noBillingDesc') }}</p>
      </div>
      <div v-else-if="bill">
        <div class="v06-metrics">
          <div class="v06-metric-card">
            <div class="v06-metric-label">{{ t('project.billing.totalCost') }}</div>
            <div class="v06-metric-value">¥{{ (bill.total_cost || 0).toLocaleString() }}</div>
          </div>
          <div class="v06-metric-card">
            <div class="v06-metric-label">{{ t('project.billing.unallocated') }}</div>
            <div class="v06-metric-value">¥{{ ((bill.detail as any)?.bucket_idle || 0).toLocaleString() }}</div>
          </div>
        </div>
        <div class="v06-card">
          <div class="v06-card-head"><h3>{{ t('project.billing.costBreakdown') }}</h3></div>
          <el-table :data="(bill.detail as any)?.lines || []" :header-cell-style="{ background: '#F8FAFC', color: '#334155', fontWeight: 600, fontSize: '13px' }">
            <el-table-column :label="t('project.billing.colUnit')" prop="unit_id" width="150" />
            <el-table-column :label="t('project.billing.colHost')" prop="host_id" width="120" />
            <el-table-column :label="t('project.billing.colAmount')" width="140" align="right">
              <template #default="{ row }">
                <span style="font-family: var(--font-mono); font-weight: 600; color: var(--color-primary-700)">¥{{ row.amount.toLocaleString() }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="t('project.billing.colMemShare')" width="120" align="center">
              <template #default="{ row }">
                <span style="font-family: var(--font-mono)">{{ Math.round(row.share * 100) }}%</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>

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
.v06-arch-grid { display: grid; grid-template-columns: 3fr 2fr; gap: 16px; margin-bottom: 24px; align-items: start; }

/* ── Card (generic) ── */
.v06-card { background: white; border: 1px solid var(--neutral-200); border-radius: 8px; overflow: hidden; }
.v06-card-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 11px 16px; border-bottom: 1px solid var(--neutral-100); background: var(--neutral-50);
}
.v06-card-head h3 { font-size: 13px; font-weight: 600; color: var(--neutral-900); margin: 0; display: flex; align-items: center; gap: 7px; }
.v06-card-body { padding: 16px; }
.v06-card-foot { padding: 9px 16px; border-top: 1px solid var(--neutral-100); background: var(--neutral-50); font-size: 11px; color: var(--neutral-400); font-family: var(--font-mono); display: flex; gap: 16px; }

/* ── AI Card (purple) ── */
.v06-ai-card { background: #FAF8FF; border: 1px solid #DDD6FE; border-radius: 8px; overflow: hidden; display: flex; flex-direction: column; }
.v06-ai-card .v06-card-head { background: #F5F2FF; border-bottom-color: #EDE9FE; }
.v06-ai-badge { background: #EDE9FE; color: #6D28D9; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 3px; }
.v06-ai-text { font-size: 13px; color: var(--neutral-700); line-height: 1.7; }
.v06-ai-risk { background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 6px; padding: 9px 12px; font-size: 12px; color: #92400E; line-height: 1.5; margin-top: 10px; }
.v06-ai-risk strong { color: #78350F; }
.v06-ai-disclaimer { padding: 8px 16px; background: #EDE9FE; border-top: 1px solid #DDD6FE; font-size: 11px; color: #7C3AED; }
.v06-ai-empty { color: var(--neutral-400); text-align: center; padding: 24px; }

/* ── Topology ── */
.v06-host-group { border: 2px dashed var(--neutral-300); border-radius: 8px; padding: 12px; margin-bottom: 12px; background: #EFF6FF; }
.v06-host-group.shared { border-color: #F59E0B; background: #FFFBEB; }
.v06-host-label { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.v06-host-name { font-weight: 700; font-family: var(--font-mono); font-size: 14px; color: var(--neutral-900); }
.v06-host-ip { font-family: var(--font-mono); font-size: 12px; color: var(--neutral-500); }
.v06-host-cost { font-family: var(--font-mono); color: var(--color-primary-700); font-size: 13px; }
.v06-host-units { display: flex; gap: 8px; flex-wrap: wrap; }
.v06-unit-node {
  border: 1px solid var(--neutral-200); border-radius: 6px; padding: 8px 12px;
  background: white; min-width: 140px; box-shadow: var(--shadow-subtle);
}
.v06-unit-name { font-weight: 600; font-size: 13px; color: var(--neutral-900); }
.v06-unit-info { display: flex; align-items: center; gap: 6px; margin-top: 4px; font-size: 11px; }
.v06-unit-owner { color: var(--neutral-500); }
.v06-host-shares { margin-top: 8px; font-size: 12px; color: #92400E; }
.v06-deps-list { margin-top: 16px; border-top: 1px solid var(--neutral-200); padding-top: 12px; }
.v06-deps-list h4 { margin: 0 0 8px; font-size: 13px; color: var(--neutral-700); }
.v06-dep-item { font-size: 13px; font-family: var(--font-mono); padding: 4px 0; color: var(--neutral-700); }
.v06-dep-item.cycle { color: #F59E0B; }

/* ── Component Table ── */
.v06-comp-card { margin-top: 20px; }
.v06-comp-card .v06-card-head h3 { font-size: 15px; }
.v06-col-group-edit { background: var(--color-primary-50) !important; color: var(--color-primary-600) !important; font-size: 11px !important; font-weight: 700 !important; letter-spacing: 0.05em; text-transform: uppercase; border-bottom: 1px solid var(--color-primary-200) !important; }
.v06-col-group-read { background: var(--neutral-100) !important; color: var(--neutral-500) !important; font-size: 11px !important; font-weight: 600 !important; letter-spacing: 0.05em; text-transform: uppercase; border-bottom: 1px solid var(--neutral-200) !important; border-left: 2px solid var(--color-primary-200) !important; }
.v06-read-cell { color: var(--neutral-500); display: flex; align-items: center; gap: 4px; font-family: var(--font-mono); font-size: 12px; }

/* ── Billing Tab ── */
.v06-billing-toggle {
  display: flex; align-items: center; gap: 10px; margin-bottom: 16px;
  padding: 10px 14px; background: var(--neutral-50); border: 1px solid var(--neutral-200); border-radius: 6px; font-size: 13px; color: var(--neutral-500);
}
.v06-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px; }
.v06-metric-card { background: white; border: 1px solid var(--neutral-200); border-radius: 8px; padding: 16px 20px; }
.v06-metric-label { font-size: 12px; color: var(--neutral-500); margin-bottom: 8px; }
.v06-metric-value { font-size: 26px; font-weight: 700; color: var(--neutral-900); font-family: var(--font-mono); line-height: 1; }
.v06-empty-billing {
  text-align: center; padding: 56px 32px; background: white;
  border: 1px solid var(--neutral-200); border-radius: 8px; color: var(--neutral-400);
}
.v06-empty-billing-icon { width: 48px; height: 48px; background: var(--neutral-100); border-radius: 50%; color: var(--neutral-400); margin: 0 auto 16px; display: flex; align-items: center; justify-content: center; font-size: 24px; }

/* ── Add Unit Dialog ── */
.v06-host-hint { font-size: 12px; color: var(--neutral-500); margin-top: 6px; }
</style>
