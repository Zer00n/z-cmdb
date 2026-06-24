<script setup lang="ts">
/**
 * Unclaimed Resources page — /assets/unclaimed
 * 2026 UI Redesign: matches design/Unclaimed Resources.html
 */
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { fetchUnclaimed, claimUnit, fetchProjectList } from '@/api/project'
import type { UnclaimedResponse, ProjectListItem } from '@/types/project'

const { t } = useI18n()
const loading = ref(true)
const data = ref<UnclaimedResponse | null>(null)
const projects = ref<ProjectListItem[]>([])

const showClaimDialog = ref(false)
const claimTarget = ref('')
const claimResourceId = ref('')
const claimResourceName = ref('')
const claiming = ref(false)

async function loadData() {
  loading.value = true
  try {
    const [unclaimed, projectList] = await Promise.all([
      fetchUnclaimed(),
      fetchProjectList({ page_size: 100 }),
    ])
    data.value = unclaimed
    projects.value = projectList.items
  } catch (e: any) {
    ElMessage.error(e?.message || t('project.unclaimed.loadError'))
  } finally {
    loading.value = false
  }
}

function openClaimDialog(id: string, name: string) {
  claimResourceId.value = id
  claimResourceName.value = name
  claimTarget.value = ''
  showClaimDialog.value = true
}

async function handleClaim() {
  if (!claimTarget.value) {
    ElMessage.warning(t('project.unclaimed.claimSelect'))
    return
  }
  claiming.value = true
  try {
    await claimUnit(claimResourceId.value, { project_id: claimTarget.value })
    ElMessage.success(t('project.unclaimed.claimSuccess'))
    showClaimDialog.value = false
    loadData()
  } catch (e: any) {
    ElMessage.error(e?.message || t('project.unclaimed.claimError'))
  } finally {
    claiming.value = false
  }
}

function formatCost(cost: number) {
  return `¥${cost.toLocaleString()}`
}

function getTypeClass(type: string) {
  if (type.includes('k8s')) return 'rtype-k8s'
  if (type.includes('docker')) return 'rtype-docker'
  if (type.includes('vm')) return 'rtype-vm'
  return 'rtype-phys'
}

onMounted(loadData)
</script>

<template>
  <div class="ui-page">
    <!-- Breadcrumb -->
    <div class="v06-crumb">
      <router-link to="/assets">{{ t('layout.sidebar.assetManagement') }}</router-link>
      <span class="v06-crumb-sep">/</span>
      <span class="v06-crumb-here">{{ t('project.unclaimed.title') }}</span>
    </div>

    <!-- Page Header -->
    <div class="ui-page-head">
      <div>
        <h1 class="ui-page-title">{{ t('project.unclaimed.title') }}</h1>
        <p class="ui-page-subtitle">{{ t('project.unclaimed.description') }}</p>
      </div>
    </div>

    <!-- Alert Summary Bar -->
    <div v-if="data" class="v06-alert-bar">
      <div class="v06-alert-icon">⚠️</div>
      <div class="v06-alert-stats">
        <div class="v06-alert-stat">
          <div class="v06-alert-value">{{ data.summary.unclaimed_count }}</div>
          <div class="v06-alert-label">{{ t('project.unclaimed.summaryUnits') }}</div>
        </div>
        <div class="v06-alert-sep"></div>
        <div class="v06-alert-stat">
          <div class="v06-alert-value">{{ data.summary.zombie_count }}</div>
          <div class="v06-alert-label">{{ t('project.unclaimed.summaryZombies') }}</div>
        </div>
        <div class="v06-alert-sep"></div>
        <div class="v06-alert-stat">
          <div class="v06-alert-value cost">{{ formatCost(data.summary.total_monthly_waste) }}</div>
          <div class="v06-alert-label">{{ t('project.unclaimed.summaryWaste') }}</div>
        </div>
      </div>
    </div>

    <div v-loading="loading">
      <!-- Unclaimed Units Section -->
      <div v-if="data && data.unclaimed_units.length > 0" class="v06-section">
        <div class="v06-section-head">
          <h2>{{ t('project.unclaimed.sectionUnits') }}</h2>
          <span class="v06-count-badge">{{ data.unclaimed_units.length }}</span>
        </div>
        <div class="ui-card v06-table-wrap">
          <el-table :data="data.unclaimed_units" :header-cell-style="{ background: '#F8FAFC', color: '#334155', fontWeight: 600, fontSize: '13px' }" :row-class-name="() => 'v06-danger-row'">
            <el-table-column :label="t('project.unclaimed.colResource')" min-width="220">
              <template #default="{ row }">
                <div class="v06-danger-indicator">
                  <span class="v06-danger-dot"></span>
                  <div>
                    <div class="v06-resource-name">{{ row.name }}</div>
                    <div class="v06-resource-id">{{ row.id }}</div>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column :label="t('project.unclaimed.colType')" width="130">
              <template #default="{ row }">
                <span class="v06-rtype" :class="getTypeClass(row.type)">{{ row.type }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="t('project.unclaimed.colDiscovered')" width="130">
              <template #default="{ row }">
                <span class="v06-mono v06-time">{{ new Date(row.created_at).toLocaleDateString() }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="t('project.unclaimed.colActions')" width="140" align="center">
              <template #default="{ row }">
                <button class="v06-btn-claim" @click="openClaimDialog(row.id, row.name)">
                  {{ t('project.unclaimed.claim') }}
                </button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- Zombie Hosts Section -->
      <div v-if="data && data.zombie_hosts.length > 0" class="v06-section">
        <div class="v06-section-head">
          <h2>{{ t('project.unclaimed.sectionZombies') }}</h2>
          <span class="v06-count-badge">{{ data.zombie_hosts.length }}</span>
        </div>
        <div class="ui-card v06-table-wrap">
          <el-table :data="data.zombie_hosts" :header-cell-style="{ background: '#F8FAFC', color: '#334155', fontWeight: 600, fontSize: '13px' }" :row-class-name="() => 'v06-danger-row'">
            <el-table-column :label="t('project.unclaimed.colResource')" min-width="220">
              <template #default="{ row }">
                <div class="v06-danger-indicator">
                  <span class="v06-danger-dot"></span>
                  <div>
                    <div class="v06-resource-name">{{ row.name }}</div>
                    <div class="v06-resource-id">{{ row.id }}</div>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column :label="t('project.unclaimed.colType')" width="130">
              <template #default="{ row }">
                <span class="v06-rtype rtype-phys">{{ row.type }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="t('project.unclaimed.colCost')" width="140" align="right">
              <template #default="{ row }">
                <span class="v06-waste-chip">{{ formatCost(row.monthly_cost) }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="t('project.unclaimed.colActions')" width="140" align="center">
              <template #default="{ row }">
                <button class="v06-btn-claim" @click="openClaimDialog(row.id, row.name)">
                  {{ t('project.unclaimed.claim') }}
                </button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- Empty State -->
      <div v-if="data && data.unclaimed_units.length === 0 && data.zombie_hosts.length === 0 && !loading" class="ui-card v06-empty-state">
        <div class="v06-empty-icon">✅</div>
        <p>{{ t('project.unclaimed.noUnits') }}</p>
      </div>
    </div>

    <!-- Claim Dialog -->
    <el-dialog v-model="showClaimDialog" :title="t('project.unclaimed.claimTitle')" width="480px">
      <div class="v06-claim-preview">
        <strong>{{ claimResourceName }}</strong>
      </div>
      <el-form label-position="top" style="margin-top: 16px">
        <el-form-item :label="t('project.unclaimed.claimSelect')" required>
          <el-select v-model="claimTarget" filterable style="width: 100%">
            <el-option v-for="p in projects" :key="p.id" :label="`${p.name} (${p.id})`" :value="p.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showClaimDialog = false">{{ t('project.cancel') }}</el-button>
        <el-button type="primary" :loading="claiming" @click="handleClaim">
          {{ t('project.unclaimed.claimConfirm') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
/* ── Breadcrumb ── */
.v06-crumb { font-size: 13px; color: var(--neutral-500); }
.v06-crumb a { color: var(--neutral-500); text-decoration: none; }
.v06-crumb a:hover { color: var(--color-primary-500); }
.v06-crumb-sep { margin: 0 6px; color: var(--neutral-300); }
.v06-crumb-here { color: var(--neutral-900); font-weight: 500; }

/* ── Alert Bar ── */
.v06-alert-bar {
  background: var(--color-danger-soft); border: 1px solid #FECACA;
  border-radius: 8px; padding: 14px 20px; display: flex; align-items: center; gap: 24px;
}
.v06-alert-icon { font-size: 28px; }
.v06-alert-stats { display: flex; align-items: center; gap: 24px; flex: 1; }
.v06-alert-stat { text-align: center; }
.v06-alert-value { font-size: 22px; font-weight: 700; color: var(--color-danger); font-family: var(--font-mono); line-height: 1; }
.v06-alert-value.cost { color: #B91C1C; }
.v06-alert-label { font-size: 12px; color: #B91C1C; margin-top: 4px; }
.v06-alert-sep { width: 1px; height: 40px; background: #FECACA; }

/* ── Section ── */
.v06-section { margin-top: 4px; }
.v06-section-head { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.v06-section-head h2 { font-size: 16px; font-weight: 600; color: var(--neutral-900); margin: 0; }
.v06-count-badge {
  background: var(--color-danger); color: white; font-size: 11px; font-weight: 600;
  padding: 1px 7px; border-radius: 9px; font-family: var(--font-mono);
}

/* ── Table ── */
.v06-table-wrap { overflow: hidden; }
:deep(.v06-danger-row td) { background: #FFFAFA !important; }
:deep(.v06-danger-row:hover td) { background: var(--color-danger-soft) !important; }

/* ── Danger Indicator ── */
.v06-danger-indicator { display: inline-flex; align-items: center; gap: 8px; }
.v06-danger-dot {
  width: 8px; height: 8px; border-radius: 50%; background: var(--color-danger);
  box-shadow: 0 0 0 3px rgba(220,38,38,0.18); flex-shrink: 0;
}
.v06-resource-name { font-weight: 600; color: var(--neutral-900); }
.v06-resource-id { font-size: 12px; color: var(--neutral-400); font-family: var(--font-mono); }

/* ── Resource Type Tags ── */
.v06-rtype { font-size: 12px; padding: 2px 8px; border-radius: 4px; font-family: var(--font-mono); }
.rtype-k8s { background: #DBEAFE; color: #1E40AF; }
.rtype-docker { background: #CFFAFE; color: #0E7490; }
.rtype-vm { background: #FEF3C7; color: #92400E; }
.rtype-phys { background: var(--neutral-200); color: var(--neutral-700); }

/* ── Waste Chip ── */
.v06-waste-chip { background: var(--color-danger-soft); color: var(--color-danger); font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 4px; font-family: var(--font-mono); }

/* ── Claim Button ── */
.v06-btn-claim {
  height: 30px; padding: 0 12px; font-size: 13px; border-radius: 6px;
  border: 1px solid var(--color-primary-300); background: var(--color-primary-50);
  color: var(--color-primary-700); cursor: pointer; font-weight: 500;
  transition: all 0.12s ease;
}
.v06-btn-claim:hover { background: var(--color-primary-500); border-color: var(--color-primary-500); color: white; }

/* ── Claim Preview ── */
.v06-claim-preview { padding: 12px; background: var(--neutral-50); border-radius: 6px; }

/* ── Empty State ── */
.v06-empty-state { text-align: center; padding: 48px; color: var(--neutral-500); }
.v06-empty-icon { font-size: 48px; margin-bottom: 12px; }

/* ── Mono / Time ── */
.v06-mono { font-family: var(--font-mono); }
.v06-time { font-size: 12px; color: var(--neutral-500); }
</style>
