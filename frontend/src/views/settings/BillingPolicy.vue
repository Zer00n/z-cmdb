<script setup lang="ts">
/**
 * Billing Policy page — /settings/billing-policy
 * 2026 UI Redesign: matches design/Billing Policy.html
 */
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchBillingPolicy, updateBillingPolicy } from '@/api/project'
import type { BillingPolicy, BillingPolicyUpdate } from '@/types/project'

const { t } = useI18n()
const loading = ref(true)
const saving = ref(false)
const policy = ref<BillingPolicy | null>(null)

const form = ref<BillingPolicyUpdate>({
  denominator: 'allocatable',
  weight_mode: 'mem',
  weight_cpu: 0.5,
  weight_mem: 0.5,
  idle_cost: 'unallocated_bucket',
  sampling: 'daily',
})

async function loadPolicy() {
  loading.value = true
  try {
    policy.value = await fetchBillingPolicy()
    form.value = {
      denominator: policy.value.denominator,
      weight_mode: policy.value.weight_mode,
      weight_cpu: policy.value.weight_cpu,
      weight_mem: policy.value.weight_mem,
      idle_cost: policy.value.idle_cost,
      sampling: policy.value.sampling,
    }
  } catch (e: any) {
    ElMessage.error(e?.message || t('project.policy.loadError'))
  } finally {
    loading.value = false
  }
}

function resetForm() {
  if (policy.value) {
    form.value = {
      denominator: policy.value.denominator,
      weight_mode: policy.value.weight_mode,
      weight_cpu: policy.value.weight_cpu,
      weight_mem: policy.value.weight_mem,
      idle_cost: policy.value.idle_cost,
      sampling: policy.value.sampling,
    }
  }
}

function onCpuWeightChange(val: number) {
  form.value.weight_cpu = Math.round(val * 100) / 100
  form.value.weight_mem = Math.round((1 - form.value.weight_cpu) * 100) / 100
}
function onMemWeightChange(val: number) {
  form.value.weight_mem = Math.round(val * 100) / 100
  form.value.weight_cpu = Math.round((1 - form.value.weight_mem) * 100) / 100
}

async function handleSave() {
  try {
    await ElMessageBox.confirm(
      t('project.policy.saveDesc'),
      t('project.policy.save'),
      { confirmButtonText: t('project.policy.save'), cancelButtonText: t('project.cancel'), type: 'warning' },
    )
  } catch { return }
  saving.value = true
  try {
    const res = await updateBillingPolicy(form.value)
    ElMessage.success(t('project.policy.saveSuccess', { version: res.version }))
    await loadPolicy()
  } catch (e: any) {
    ElMessage.error(e?.message || t('project.policy.saveError'))
  } finally {
    saving.value = false
  }
}
onMounted(loadPolicy)
</script>

<template>
  <div class="ui-page" v-loading="loading">
    <!-- Breadcrumb -->
    <div class="v06-crumb">
      <router-link to="/settings">{{ t('layout.sidebar.systemAdmin') }}</router-link>
      <span class="v06-crumb-sep">/</span>
      <span class="v06-crumb-here">{{ t('project.policy.title') }}</span>
    </div>

    <h1 class="ui-page-title">{{ t('project.policy.title') }}</h1>
    <p class="ui-page-subtitle">{{ t('project.policy.description') }}</p>

    <!-- Version Bar -->
    <div v-if="policy" class="v06-version-bar">
      <span class="v06-ver-badge">v{{ policy.version }}</span>
      <span class="v06-ver-meta">{{ t('project.policy.lastModified') }}: <strong>{{ new Date(policy.created_at).toLocaleString() }}</strong></span>
      <span class="v06-scope-note">{{ t('project.policy.scope') }}</span>
    </div>

    <div class="v06-policy-layout">
      <!-- Left: Config -->
      <div class="v06-policy-config">
        <!-- Denominator -->
        <div class="v06-policy-section">
          <h3>{{ t('project.policy.denominator') }}</h3>
          <div class="v06-radio-group">
            <label class="v06-radio-opt" :class="{ selected: form.denominator === 'allocatable' }">
              <input type="radio" v-model="form.denominator" value="allocatable" />
              <div>
                <div class="v06-radio-title">{{ t('project.policy.denominatorAllocatable') }} <span class="v06-recommend">{{ t('project.policy.recommended') }}</span></div>
                <div class="v06-radio-desc">{{ t('project.policy.denominatorAllocatableDesc') }}</div>
              </div>
            </label>
            <label class="v06-radio-opt" :class="{ selected: form.denominator === 'sum_requests' }">
              <input type="radio" v-model="form.denominator" value="sum_requests" />
              <div>
                <div class="v06-radio-title">{{ t('project.policy.denominatorSumRequests') }}</div>
                <div class="v06-radio-desc">{{ t('project.policy.denominatorSumRequestsDesc') }}</div>
              </div>
            </label>
          </div>
        </div>

        <!-- Weight Mode -->
        <div class="v06-policy-section">
          <h3>{{ t('project.policy.weightMode') }}</h3>
          <div class="v06-radio-group">
            <label class="v06-radio-opt" :class="{ selected: form.weight_mode === 'mem' }">
              <input type="radio" v-model="form.weight_mode" value="mem" />
              <div><div class="v06-radio-title">{{ t('project.policy.weightMem') }} <span class="v06-recommend">{{ t('project.policy.recommended') }}</span></div></div>
            </label>
            <label class="v06-radio-opt" :class="{ selected: form.weight_mode === 'cpu' }">
              <input type="radio" v-model="form.weight_mode" value="cpu" />
              <div><div class="v06-radio-title">{{ t('project.policy.weightCpu') }}</div></div>
            </label>
            <label class="v06-radio-opt" :class="{ selected: form.weight_mode === 'weighted' }">
              <input type="radio" v-model="form.weight_mode" value="weighted" />
              <div>
                <div class="v06-radio-title">{{ t('project.policy.weightWeighted') }}</div>
                <div v-if="form.weight_mode === 'weighted'" class="v06-weight-sliders">
                  <div class="v06-slider-row">
                    <span class="v06-slider-label">{{ t('project.policy.cpuWeight') }}</span>
                    <input type="range" :value="form.weight_cpu" min="0" max="1" step="0.01" @input="onCpuWeightChange(+(($event.target as HTMLInputElement).value))" />
                    <span class="v06-slider-val">{{ Math.round(form.weight_cpu * 100) }}%</span>
                  </div>
                  <div class="v06-slider-row">
                    <span class="v06-slider-label">{{ t('project.policy.memWeight') }}</span>
                    <input type="range" :value="form.weight_mem" min="0" max="1" step="0.01" @input="onMemWeightChange(+(($event.target as HTMLInputElement).value))" />
                    <span class="v06-slider-val">{{ Math.round(form.weight_mem * 100) }}%</span>
                  </div>
                </div>
              </div>
            </label>
            <label class="v06-radio-opt" :class="{ selected: form.weight_mode === 'max' }">
              <input type="radio" v-model="form.weight_mode" value="max" />
              <div><div class="v06-radio-title">{{ t('project.policy.weightMax') }}</div></div>
            </label>
          </div>
        </div>

        <!-- Idle Cost -->
        <div class="v06-policy-section">
          <h3>{{ t('project.policy.idleCost') }}</h3>
          <div class="v06-radio-group">
            <label class="v06-radio-opt" :class="{ selected: form.idle_cost === 'unallocated_bucket' }">
              <input type="radio" v-model="form.idle_cost" value="unallocated_bucket" />
              <div>
                <div class="v06-radio-title">{{ t('project.policy.idleBucket') }} <span class="v06-recommend">{{ t('project.policy.recommended') }}</span></div>
                <div class="v06-radio-desc">{{ t('project.policy.idleBucketDesc') }}</div>
              </div>
            </label>
            <label class="v06-radio-opt" :class="{ selected: form.idle_cost === 'force_allocate' }">
              <input type="radio" v-model="form.idle_cost" value="force_allocate" />
              <div>
                <div class="v06-radio-title">{{ t('project.policy.idleForce') }}</div>
                <div class="v06-radio-desc">{{ t('project.policy.idleForceDesc') }}</div>
              </div>
            </label>
          </div>
        </div>

        <!-- Sampling -->
        <div class="v06-policy-section">
          <h3>{{ t('project.policy.sampling') }}</h3>
          <div class="v06-radio-group">
            <label class="v06-radio-opt" :class="{ selected: form.sampling === 'daily' }">
              <input type="radio" v-model="form.sampling" value="daily" />
              <div><div class="v06-radio-title">{{ t('project.policy.samplingDaily') }} <span class="v06-recommend">{{ t('project.policy.recommended') }}</span></div></div>
            </label>
            <label class="v06-radio-opt" :class="{ selected: form.sampling === 'hourly' }">
              <input type="radio" v-model="form.sampling" value="hourly" />
              <div><div class="v06-radio-title">{{ t('project.policy.samplingHourly') }}</div></div>
            </label>
          </div>
        </div>

        <!-- Freeze (read-only) -->
        <div class="v06-policy-section v06-frozen">
          <h3>
            {{ t('project.policy.freeze') }}
            <span class="v06-frozen-badge">{{ t('project.policy.freezeDesc') }}</span>
          </h3>
          <div class="v06-frozen-toggle">
            <span class="v06-toggle-frozen"></span>
          </div>
          <p class="v06-frozen-note">{{ t('project.policy.freezeNote') }}</p>
        </div>

        <!-- Save Bar -->
        <div class="v06-save-bar">
          <p class="v06-save-desc">{{ t('project.policy.saveDesc') }}</p>
          <div class="v06-save-actions">
            <el-button @click="resetForm">{{ t('project.policy.reset') }}</el-button>
            <el-button type="primary" :loading="saving" @click="handleSave">{{ t('project.policy.save') }}</el-button>
          </div>
        </div>
      </div>

      <!-- Right: Help -->
      <div class="v06-help-panel">
        <div class="v06-help-item">
          <div class="v06-help-head"><span class="v06-help-dot"></span><h4>{{ t('project.policy.helpAllocation') }}</h4></div>
          <p>{{ t('project.policy.helpAllocationDesc') }}</p>
        </div>
        <div class="v06-help-item">
          <div class="v06-help-head"><span class="v06-help-dot"></span><h4>{{ t('project.policy.helpUnallocated') }}</h4></div>
          <p>{{ t('project.policy.helpUnallocatedDesc') }}</p>
        </div>
        <div class="v06-help-item">
          <div class="v06-help-head"><span class="v06-help-dot"></span><h4>{{ t('project.policy.helpVersioning') }}</h4></div>
          <p>{{ t('project.policy.helpVersioningDesc') }}</p>
        </div>
        <div class="v06-help-item">
          <div class="v06-help-head"><span class="v06-help-dot"></span><h4>{{ t('project.policy.helpV2') }}</h4></div>
          <p>{{ t('project.policy.helpV2Desc') }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ── Breadcrumb ── */
.v06-crumb { font-size: 13px; color: var(--neutral-500); margin-bottom: 4px; }
.v06-crumb a { color: var(--neutral-500); text-decoration: none; }
.v06-crumb a:hover { color: var(--color-primary-500); }
.v06-crumb-sep { margin: 0 6px; color: var(--neutral-300); }
.v06-crumb-here { color: var(--neutral-900); font-weight: 500; }

/* ── Version Bar ── */
.v06-version-bar {
  background: white; border: 1px solid var(--neutral-200); border-radius: 8px;
  padding: 14px 20px; display: flex; align-items: center; gap: 12px;
}
.v06-ver-badge {
  background: var(--color-primary-50); color: var(--color-primary-700);
  font-size: 12px; font-weight: 600; padding: 4px 12px; border-radius: 4px;
  border: 1px solid var(--color-primary-200); font-family: var(--font-mono);
}
.v06-ver-meta { font-size: 13px; color: var(--neutral-500); }
.v06-ver-meta strong { color: var(--neutral-900); }
.v06-scope-note {
  margin-left: auto; font-size: 12px; color: var(--neutral-500);
  background: var(--neutral-50); border: 1px solid var(--neutral-200);
  border-radius: 4px; padding: 4px 12px;
}

/* ── Layout ── */
.v06-policy-layout { display: grid; grid-template-columns: 640px 1fr; gap: 24px; align-items: start; margin-top: 20px; }
.v06-policy-config { display: flex; flex-direction: column; gap: 0; }

/* ── Policy Section ── */
.v06-policy-section {
  background: white; border: 1px solid var(--neutral-200); border-radius: 8px;
  padding: 20px 24px; margin-bottom: 16px;
}
.v06-policy-section h3 { font-size: 15px; font-weight: 600; color: var(--neutral-900); margin: 0 0 12px; display: flex; align-items: center; gap: 8px; }
.v06-policy-section.v06-frozen { background: var(--neutral-50); }

/* ── Radio Group ── */
.v06-radio-group { display: flex; flex-direction: column; gap: 8px; }
.v06-radio-opt {
  display: flex; align-items: flex-start; gap: 12px;
  padding: 12px 14px; border-radius: 6px;
  border: 1.5px solid var(--neutral-200); cursor: pointer;
  transition: border-color 0.12s, background 0.12s;
}
.v06-radio-opt:hover { border-color: var(--neutral-300); background: var(--neutral-50); }
.v06-radio-opt.selected { border-color: var(--color-primary-500); background: var(--color-primary-50); }
.v06-radio-opt input[type="radio"] { margin-top: 3px; }
.v06-radio-title { font-size: 14px; font-weight: 500; color: var(--neutral-900); display: flex; align-items: center; gap: 6px; }
.v06-radio-desc { font-size: 12px; color: var(--neutral-500); margin-top: 3px; }
.v06-recommend {
  background: var(--color-success-soft); color: #166534;
  font-size: 11px; font-weight: 600; padding: 1px 6px; border-radius: 3px;
}

/* ── Weight Sliders ── */
.v06-weight-sliders { margin-top: 12px; padding: 12px 14px; background: white; border: 1px solid var(--neutral-200); border-radius: 6px; }
.v06-slider-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.v06-slider-row:last-child { margin-bottom: 0; }
.v06-slider-label { width: 80px; font-size: 13px; color: var(--neutral-700); }
.v06-slider-row input[type="range"] { flex: 1; accent-color: var(--color-primary-500); }
.v06-slider-val { width: 40px; text-align: right; font-size: 13px; font-family: var(--font-mono); font-weight: 600; }

/* ── Frozen Toggle ── */
.v06-frozen-toggle { margin: 8px 0; }
.v06-toggle-frozen {
  display: inline-block; width: 36px; height: 20px; background: var(--color-primary-500);
  border-radius: 10px; position: relative; opacity: 0.5; cursor: not-allowed;
}
.v06-toggle-frozen::after {
  content: ''; position: absolute; width: 14px; height: 14px; border-radius: 50%;
  background: white; top: 3px; left: 19px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.1);
}
.v06-frozen-badge {
  background: var(--neutral-200); color: var(--neutral-500);
  font-size: 11px; padding: 2px 8px; border-radius: 3px; font-weight: 400;
}
.v06-frozen-note { font-size: 12px; color: var(--neutral-500); margin: 8px 0 0; }

/* ── Save Bar ── */
.v06-save-bar {
  background: white; border: 1px solid var(--neutral-200); border-radius: 8px;
  padding: 16px 20px; display: flex; align-items: center; justify-content: space-between;
}
.v06-save-desc { font-size: 13px; color: var(--neutral-500); margin: 0; }
.v06-save-actions { display: flex; gap: 8px; }

/* ── Help Panel ── */
.v06-help-panel { background: white; border: 1px solid var(--neutral-200); border-radius: 8px; padding: 20px 24px; }
.v06-help-item { margin-bottom: 20px; }
.v06-help-item:last-child { margin-bottom: 0; }
.v06-help-head { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.v06-help-head h4 { margin: 0; font-size: 14px; color: var(--neutral-900); }
.v06-help-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--color-primary-400); flex-shrink: 0; }
.v06-help-item p { margin: 0; font-size: 13px; color: var(--neutral-500); line-height: 1.6; padding-left: 14px; }
</style>
