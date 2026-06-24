<script setup lang="ts">
/**
 * Project List page — /projects
 * 2026 UI Redesign: uses .ui-* utility classes, matches design/Project List.html
 */
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchProjectList, createProject } from '@/api/project'
import type { ProjectListItem, ProjectCreateRequest } from '@/types/project'

const { t } = useI18n()
const router = useRouter()

const loading = ref(true)
const projects = ref<ProjectListItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const search = ref('')
const filterBusinessUnit = ref('')
const filterOwner = ref('')
const filterBillingMode = ref('')

const showCreateDialog = ref(false)
const createForm = ref<ProjectCreateRequest>({ name: '', owner: '', business_unit: '' })
const creating = ref(false)

async function loadData() {
  loading.value = true
  try {
    const res = await fetchProjectList({
      search: search.value || undefined,
      business_unit: filterBusinessUnit.value || undefined,
      owner: filterOwner.value || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    projects.value = res.items
    total.value = res.total
  } catch (e: any) {
    ElMessage.error(e?.message || t('project.list.loadError'))
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  search.value = ''
  filterBusinessUnit.value = ''
  filterOwner.value = ''
  filterBillingMode.value = ''
  page.value = 1
  loadData()
}

function formatCost(cost: number | null) {
  if (cost === null || cost === undefined) return t('project.list.notEnabled')
  return `¥${cost.toLocaleString()}`
}

function getInitial(name: string) {
  return name ? name.charAt(0) : '?'
}

function getAvatarColor(name: string) {
  const colors = [
    { bg: '#DBEAFE', fg: '#1E40AF' },
    { bg: '#DCFCE7', fg: '#166534' },
    { bg: '#FEE2E2', fg: '#991B1B' },
    { bg: '#FEF3C7', fg: '#92400E' },
    { bg: '#EDE9FE', fg: '#5B21B6' },
    { bg: '#CFFAFE', fg: '#0E7490' },
  ]
  let hash = 0
  for (let i = 0; i < (name || '').length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
  return colors[Math.abs(hash) % colors.length]
}

async function handleCreate() {
  if (!createForm.value.name.trim()) {
    ElMessage.warning(t('project.list.createNameRequired'))
    return
  }
  creating.value = true
  try {
    await createProject(createForm.value)
    ElMessage.success(t('project.list.createSuccess'))
    showCreateDialog.value = false
    createForm.value = { name: '', owner: '', business_unit: '' }
    loadData()
  } catch (e: any) {
    ElMessage.error(e?.message || t('project.list.createError'))
  } finally {
    creating.value = false
  }
}

function goToDetail(id: string) {
  router.push(`/projects/${id}`)
}

onMounted(loadData)
</script>

<template>
  <div class="ui-page">
    <!-- Page Header -->
    <div class="ui-page-head">
      <div>
        <h1 class="ui-page-title">
          {{ t('project.list.title') }}
          <span class="ui-page-count">{{ t('project.list.totalProjects', { count: total }) }}</span>
        </h1>
      </div>
      <div class="ui-page-actions">
        <el-button @click="loadData">{{ t('project.list.exportCsv') }}</el-button>
        <el-button type="primary" @click="showCreateDialog = true">
          {{ t('project.list.create') }}
        </el-button>
      </div>
    </div>

    <!-- Filter Bar -->
    <div class="ui-card ui-card-tight v06-filters">
      <el-input
        v-model="search"
        :placeholder="t('project.list.search')"
        prefix-icon="Search"
        clearable
        class="v06-filter-search"
        @keyup.enter="loadData"
      />
      <span class="v06-filter-sep"></span>
      <el-input v-model="filterBusinessUnit" :placeholder="t('project.list.filterBusinessUnit')" clearable size="default" @keyup.enter="loadData" />
      <el-input v-model="filterOwner" :placeholder="t('project.list.filterOwner')" clearable size="default" @keyup.enter="loadData" />
      <el-link type="info" :underline="false" @click="resetFilters">{{ t('project.list.resetFilters') }}</el-link>
    </div>

    <!-- Data Table -->
    <div class="ui-card v06-table-wrap">
      <el-table :data="projects" v-loading="loading" @row-click="(row: ProjectListItem) => goToDetail(row.id)" style="cursor: pointer" :header-cell-style="{ background: '#F8FAFC', color: '#334155', fontWeight: 600, fontSize: '13px' }" :row-style="{ cursor: 'pointer' }">
        <el-table-column :label="t('project.list.colProject')" min-width="200">
          <template #default="{ row }">
            <div class="v06-project-cell">
              <div class="v06-avatar" :style="{ background: getAvatarColor(row.owner || row.name).bg, color: getAvatarColor(row.owner || row.name).fg }">
                {{ getInitial(row.owner || row.name) }}
              </div>
              <div>
                <div class="v06-project-name">{{ row.name }}</div>
                <div class="v06-project-id">{{ row.id }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column :label="t('project.list.colOwner')" prop="owner" width="120" />
        <el-table-column :label="t('project.list.colBusinessUnit')" width="130">
          <template #default="{ row }">
            <span v-if="row.business_unit" class="v06-tag v06-tag-info">{{ row.business_unit }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('project.list.colUnits')" prop="unit_count" width="90" align="center">
          <template #default="{ row }">
            <span class="v06-mono">{{ row.unit_count }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('project.list.colHosts')" prop="host_count" width="90" align="center">
          <template #default="{ row }">
            <span class="v06-mono">{{ row.host_count }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('project.list.colMonthlyCost')" width="140" align="right">
          <template #default="{ row }">
            <span v-if="row.current_month_cost" class="v06-cost">¥{{ row.current_month_cost.toLocaleString() }}</span>
            <span v-else class="v06-cost-disabled">{{ t('project.list.notEnabled') }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('project.list.colBillingMode')" width="100" align="center">
          <template #default="{ row }">
            <span class="v06-toggle" :class="{ on: row.billing_enabled }">
              <span class="v06-toggle-track"></span>
            </span>
          </template>
        </el-table-column>
        <el-table-column :label="t('project.list.colUpdated')" width="120">
          <template #default="{ row }">
            <span class="v06-mono v06-time">{{ new Date(row.updated_at).toLocaleDateString() }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('project.list.colActions')" width="70" align="center">
          <template #default="{ row }">
            <el-link type="primary" :underline="false" @click.stop="goToDetail(row.id)">{{ t('project.list.details') }}</el-link>
          </template>
        </el-table-column>
      </el-table>

      <!-- Pagination Footer -->
      <div v-if="total > pageSize" class="v06-table-footer">
        <span class="v06-table-footer-text">{{ t('project.list.totalProjects', { count: total }) }}</span>
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          small
          @current-change="loadData"
        />
      </div>
    </div>

    <!-- Create Dialog -->
    <el-dialog v-model="showCreateDialog" :title="t('project.list.createTitle')" width="480px">
      <el-form label-position="top">
        <el-form-item :label="t('project.list.createName')" required>
          <el-input v-model="createForm.name" />
        </el-form-item>
        <el-form-item :label="t('project.list.createOwner')">
          <el-input v-model="createForm.owner" />
        </el-form-item>
        <el-form-item :label="t('project.list.createBusinessUnit')">
          <el-input v-model="createForm.business_unit" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">{{ t('project.cancel') }}</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">{{ t('project.confirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
/* ── Filter bar ── */
.v06-filters {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px !important;
  flex-wrap: wrap;
}
.v06-filter-search { width: 240px; }
.v06-filter-sep { width: 1px; height: 20px; background: var(--neutral-200); flex-shrink: 0; }

/* ── Table ── */
.v06-table-wrap { overflow: hidden; }
.v06-table-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-top: 1px solid var(--neutral-200);
  background: white;
  font-size: 13px;
  color: var(--neutral-500);
}
.v06-table-footer-text { font-family: var(--font-mono); }

/* ── Project cell ── */
.v06-project-cell { display: flex; align-items: center; gap: 10px; }
.v06-avatar {
  width: 28px; height: 28px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 600; flex-shrink: 0;
}
.v06-project-name { font-weight: 600; color: var(--neutral-900); }
.v06-project-id { font-size: 12px; color: var(--neutral-400); font-family: var(--font-mono); }

/* ── Tags ── */
.v06-tag { padding: 2px 8px; border-radius: 4px; font-size: 12px; }
.v06-tag-info { background: var(--color-info-soft); color: #0E7490; }

/* ── Cost ── */
.v06-cost { font-family: var(--font-mono); font-size: 13px; font-weight: 600; color: var(--color-primary-700); }
.v06-cost-disabled { font-size: 13px; color: var(--neutral-400); }

/* ── Toggle ── */
.v06-toggle { display: inline-block; width: 34px; height: 18px; position: relative; cursor: default; }
.v06-toggle-track {
  position: absolute; inset: 0; background: var(--neutral-300); border-radius: 9px; transition: background 0.2s;
}
.v06-toggle-track::before {
  content: ''; position: absolute; width: 12px; height: 12px; border-radius: 50%;
  background: white; left: 3px; bottom: 3px; transition: transform 0.2s;
  box-shadow: 0 1px 2px rgba(0,0,0,0.1);
}
.v06-toggle.on .v06-toggle-track { background: var(--color-primary-500); }
.v06-toggle.on .v06-toggle-track::before { transform: translateX(16px); }

/* ── Mono / Time ── */
.v06-mono { font-family: var(--font-mono); font-size: 13px; }
.v06-time { font-size: 12px; color: var(--neutral-500); }
</style>
