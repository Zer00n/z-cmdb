<script setup lang="ts">
/**
 * Facility / rack elevation page.
 * Datacenter -> rack strip -> bottom-up rack elevation (U1 at the bottom).
 * Device click opens the connection panel and highlights upstream switches.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  createRack,
  fetchDatacenterRacks,
  fetchDatacenters,
  fetchRackElevation,
  updateRack,
} from '@/api/facility'
import { useAuthStore } from '@/stores/auth'
import type {
  DatacenterSummary,
  DeviceInterface,
  ElevationDevice,
  RackElevation,
  RackSummary,
  UnlocatedAsset,
} from '@/types/facility'

const { t } = useI18n()
const router = useRouter()
const authStore = useAuthStore()

const ROW_H = 18  // px per U

const datacenters = ref<DatacenterSummary[]>([])
const currentDc = ref('')
const racks = ref<RackSummary[]>([])
const unlocated = ref<UnlocatedAsset[]>([])

const selectedRackIds = ref<Set<number>>(new Set())
const elevations = ref<Record<number, RackElevation>>({})

const selectedDeviceId = ref<number | null>(null)

// ── Data loading ────────────────────────────────────────────────

async function loadDatacenters(pick?: string) {
  datacenters.value = await fetchDatacenters()
  const first = pick || datacenters.value[0]?.datacenter || ''
  await switchDc(first)
}

async function switchDc(name: string) {
  currentDc.value = name
  selectedDeviceId.value = null
  elevations.value = {}
  if (!name) {
    racks.value = []
    unlocated.value = []
    selectedRackIds.value = new Set()
    return
  }
  const data = await fetchDatacenterRacks(name)
  racks.value = data.racks
  unlocated.value = data.unlocated
  const preselect =
    racks.value.length <= 6 ? new Set(racks.value.map((r) => r.id))
    : new Set(racks.value.slice(0, 1).map((r) => r.id))
  selectedRackIds.value = preselect
  for (const id of preselect) await loadElevation(id)
}

async function loadElevation(rackId: number) {
  if (elevations.value[rackId]) return
  elevations.value[rackId] = await fetchRackElevation(rackId)
}

async function toggleRack(id: number) {
  const next = new Set(selectedRackIds.value)
  if (next.has(id)) {
    next.delete(id)
  } else {
    next.add(id)
    await loadElevation(id)
  }
  selectedRackIds.value = next
}

// ── Elevation columns in selected order ─────────────────────────

const visibleElevations = computed(() =>
  racks.value
    .filter((r) => selectedRackIds.value.has(r.id))
    .map((r) => elevations.value[r.id])
    .filter((e): e is RackElevation => !!e),
)

const rulerNumbers = (height: number) =>
  Array.from({ length: height }, (_, i) => height - i)

function deviceTop(uHeight: number, device: ElevationDevice): string {
  const start = device.u_start as number
  const height = device.u_height || 1
  return `${(uHeight - (start + height - 1)) * ROW_H}px`
}
function deviceHeight(device: ElevationDevice): string {
  return `${(device.u_height || 1) * ROW_H - 2}px`
}

// ── Device selection / connection panel ─────────────────────────

const selectedDevice = computed<{ elevation: RackElevation; device: ElevationDevice } | null>(() => {
  if (selectedDeviceId.value === null) return null
  for (const el of visibleElevations.value) {
    const device = el.devices.find((d) => d.id === selectedDeviceId.value)
    if (device) return { elevation: el, device }
  }
  return null
})

const upstreamSwitchIds = computed<Set<number>>(() => {
  const result = new Set<number>()
  if (selectedDevice.value) {
    for (const iface of selectedDevice.value.device.interfaces) {
      if (iface.connected_switch) result.add(iface.connected_switch.id)
    }
  }
  return result
})

function selectDevice(id: number) {
  selectedDeviceId.value = selectedDeviceId.value === id ? null : id
}

// ── Styling helpers ─────────────────────────────────────────────

function deviceClasses(device: ElevationDevice): string {
  return [
    'rack-device',
    `is-${device.asset_type}`,
    `imp-${device.importance}`,
    device.status === 'decommissioned' ? 'st-offline' : '',
    device.id === selectedDeviceId.value ? 'is-selected' : '',
    upstreamSwitchIds.value.has(device.id) ? 'is-uplink' : '',
  ].join(' ')
}

function warningType(code: string): 'danger' | 'warning' | 'info' {
  if (code === 'out_of_range') return 'danger'
  if (code === 'overlap') return 'warning'
  return 'info'
}

// ── Rack create / edit dialogs ──────────────────────────────────

const rackDialogVisible = ref(false)
const rackDialogMode = ref<'create' | 'edit'>('create')
const rackDialogEditingId = ref<number | null>(null)
const rackForm = reactive({
  datacenter: '',
  name: '',
  u_height: 42,
  description: '',
})

function openCreateRack() {
  rackDialogMode.value = 'create'
  rackDialogEditingId.value = null
  rackForm.datacenter = currentDc.value
  rackForm.name = ''
  rackForm.u_height = 42
  rackForm.description = ''
  rackDialogVisible.value = true
}

function openEditRack(rack: RackElevation) {
  rackDialogMode.value = 'edit'
  rackDialogEditingId.value = rack.id
  rackForm.datacenter = rack.datacenter || ''
  rackForm.name = rack.name
  rackForm.u_height = rack.u_height
  rackForm.description = rack.description || ''
  rackDialogVisible.value = true
}

async function submitRackDialog() {
  if (!rackForm.name.trim()) {
    ElMessage.warning(t('facility.validation.nameRequired'))
    return
  }
  if (rackDialogMode.value === 'create') {
    await createRack({
      datacenter: rackForm.datacenter || null,
      name: rackForm.name.trim(),
      u_height: rackForm.u_height,
      description: rackForm.description || null,
    })
    ElMessage.success(t('common.success'))
  } else if (rackDialogEditingId.value !== null) {
    await updateRack(rackDialogEditingId.value, {
      datacenter: rackForm.datacenter || null,
      name: rackForm.name.trim(),
      u_height: rackForm.u_height,
      description: rackForm.description || null,
    })
    ElMessage.success(t('common.success'))
  }
  rackDialogVisible.value = false
  await loadDatacenters(rackForm.datacenter || currentDc.value)
}

// ── Misc ────────────────────────────────────────────────────────

function ifaceKey(iface: DeviceInterface, idx: number) {
  return `${iface.id}-${idx}`
}

onMounted(() => loadDatacenters())
</script>

<template>
  <div class="facility-page">
    <!-- ① Datacenter tabs -->
    <div class="dc-tabs">
      <el-button
        v-for="dc in datacenters"
        :key="dc.datacenter"
        :class="['dc-tab', { active: dc.datacenter === currentDc }]"
        @click="switchDc(dc.datacenter)"
      >
        <span class="dc-name">{{ dc.datacenter || t('facility.unassigned') }}</span>
        <span class="dc-meta">{{ dc.rack_count }}{{ t('facility.units.rack') }}
          · {{ dc.device_count }}{{ t('facility.units.device') }}</span>
        <el-tag
          v-if="dc.unlocated_count"
          size="small" type="warning" effect="plain" class="dc-badge"
        >{{ dc.unlocated_count }}</el-tag>
      </el-button>

      <el-button
        v-if="authStore.isAdmin"
        class="dc-tab add-rack-btn"
        @click="openCreateRack"
      >
        <el-icon><Plus /></el-icon> {{ t('facility.actions.addRack') }}
      </el-button>
    </div>

    <!-- ② Rack strip -->
    <div v-if="currentDc" class="rack-strip">
      <el-button
        v-for="rack in racks"
        :key="rack.id"
        size="small"
        :class="['rack-chip', { active: selectedRackIds.has(rack.id) }]"
        @click="toggleRack(rack.id)"
      >
        <span class="rack-chip-name">{{ rack.name }}</span>
        <span class="rack-chip-bar">
          <i :style="{ width: `${Math.min(100, rack.utilization * 100)}%` }" />
        </span>
        <span class="rack-chip-meta">{{ rack.device_count }} ·
          {{ Math.round(rack.utilization * 100) }}%</span>
      </el-button>
      <span v-if="!racks.length" class="empty-hint">{{ t('facility.noRacks') }}</span>
    </div>

    <div class="facility-body">
      <!-- ③ Elevations -->
      <div class="elevations">
        <div v-for="el in visibleElevations" :key="el.id" class="rack-column">
          <!-- Rack header -->
          <div class="rack-head">
            <div class="rack-title">
              <strong>{{ el.name }}</strong>
              <span>{{ el.u_height }}U</span>
            </div>
            <el-icon
              v-if="authStore.isAdmin"
              class="rack-edit"
              @click="openEditRack(el)"
            ><Edit /></el-icon>
          </div>

          <!-- Warnings -->
          <div v-if="el.warnings.length" class="rack-warnings">
            <el-tooltip
              v-for="(w, i) in el.warnings"
              :key="i"
              :content="w.message"
              placement="top"
            >
              <el-icon :color="warningType(w.code) === 'danger' ? 'var(--color-danger)' : 'var(--color-warning)'">
                <WarningFilled />
              </el-icon>
            </el-tooltip>
          </div>

          <!-- Elevation body -->
          <div class="rack-elevation" :style="{ height: `${el.u_height * ROW_H}px` }">
            <!-- U ruler -->
            <div class="u-ruler">
              <span
                v-for="u in rulerNumbers(el.u_height)"
                :key="u"
                class="u-num"
                :style="{ height: `${ROW_H}px` }"
              >{{ u }}</span>
            </div>

            <!-- Device slot area -->
            <div class="slot-area" :style="{ height: `${el.u_height * ROW_H}px` }">
              <el-button
                v-for="device in el.devices.filter((d) => d.u_start != null)"
                :key="device.id"
                :class="deviceClasses(device)"
                :style="{ top: deviceTop(el.u_height, device), height: deviceHeight(device) }"
                @click.stop="selectDevice(device.id)"
              >
                <el-icon class="dev-ico"><component :is="device.asset_type === 'network_device' ? 'Share' : 'Monitor'" /></el-icon>
                <span class="dev-label">{{ device.hostname || device.asset_no }}</span>
              </el-button>
            </div>
          </div>
        </div>

        <span v-if="!visibleElevations.length && currentDc" class="empty-hint">
          {{ t('facility.selectRackHint') }}
        </span>
      </div>

      <!-- Connection panel -->
      <aside class="connection-panel">
        <template v-if="selectedDevice">
          <div class="cp-head">
            <strong>{{ selectedDevice.device.hostname || selectedDevice.device.asset_no }}</strong>
            <el-button link type="primary" @click="router.push(`/assets/${selectedDevice.device.id}`)">
              {{ t('facility.actions.viewDetail') }}
            </el-button>
          </div>
          <div class="cp-sub">{{ selectedDevice.device.asset_no }}
            · {{ selectedDevice.elevation.name }}</div>

          <el-divider style="margin: 10px 0" />

          <div v-if="!selectedDevice.device.interfaces.length" class="empty-hint">
            {{ t('facility.noLinks') }}
          </div>

          <div
            v-for="(iface, idx) in selectedDevice.device.interfaces"
            :key="ifaceKey(iface, idx)"
            class="link-item"
          >
            <div class="link-row">
              <span class="link-local">
                {{ iface.name || '—' }}
                <em v-if="iface.ip_address">{{ iface.ip_address }}</em>
              </span>
              <el-icon><Right /></el-icon>
              <span class="link-peer">
                {{ iface.connected_switch?.hostname || iface.connected_switch?.asset_no || '—' }}
                <em v-if="iface.connected_port">{{ iface.connected_port }}</em>
              </span>
            </div>
            <div class="link-tags">
              <el-tag v-if="iface.source === 'asset'" size="small" effect="plain" type="info">
                {{ t('facility.linkSourceAsset') }}
              </el-tag>
              <el-tag v-if="iface.bond_master" size="small" effect="plain">
                {{ iface.bond_master }}
              </el-tag>
              <el-tag v-if="iface.vlan_id" size="small" effect="plain" type="info">
                VLAN {{ iface.vlan_id }}
              </el-tag>
            </div>
          </div>
        </template>

        <template v-else>
          <div class="cp-placeholder">
            <el-icon size="28"><Aim /></el-icon>
            <p>{{ t('facility.selectDeviceHint') }}</p>
          </div>
        </template>
      </aside>
    </div>

    <!-- Unlocated assets -->
    <div v-if="unlocated.length" class="unlocated-box">
      <div class="unlocated-head">
        <el-icon color="var(--color-warning)"><WarningFilled /></el-icon>
        <strong>{{ t('facility.unlocatedTitle', { count: unlocated.length }) }}</strong>
      </div>
      <div class="unlocated-list">
        <el-button
          v-for="item in unlocated"
          :key="item.id"
          size="small"
          class="unlocated-chip"
          @click="router.push(`/assets/${item.id}/edit`)"
        >
          {{ item.hostname || item.asset_no }}
          <el-tag size="small" effect="plain" type="warning">
            {{ t(`facility.reasons.${item.reason}`) }}
          </el-tag>
        </el-button>
      </div>
    </div>

    <!-- Rack create/edit dialog -->
    <el-dialog
      v-model="rackDialogVisible"
      :title="rackDialogMode === 'create'
        ? t('facility.dialog.createTitle')
        : t('facility.dialog.editTitle')"
      width="440px"
    >
      <el-form label-width="90px">
        <el-form-item :label="t('facility.dialog.datacenter')">
          <el-input v-model="rackForm.datacenter" />
        </el-form-item>
        <el-form-item :label="t('facility.dialog.name')">
          <el-input v-model="rackForm.name" />
        </el-form-item>
        <el-form-item :label="t('facility.dialog.uHeight')">
          <el-input-number v-model="rackForm.u_height" :min="1" :max="52" />
        </el-form-item>
        <el-form-item :label="t('facility.dialog.description')">
          <el-input v-model="rackForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rackDialogVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="submitRackDialog">{{ t('common.confirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.facility-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

/* Datacenter tabs */
.dc-tabs {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.dc-tab {
  display: flex;
  align-items: center;
  gap: 8px;
}
.dc-name {
  font-weight: 600;
}
.dc-meta {
  font-size: 12px;
  color: var(--neutral-400);
}
.dc-tab.active {
  border-color: var(--color-primary-500);
  color: var(--color-primary-700);
  background: var(--color-primary-50);
}
.add-rack-btn {
  border-style: dashed;
}

/* Rack strip */
.rack-strip {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
  align-items: center;
}
.rack-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.rack-chip-name {
  font-weight: 600;
}
.rack-chip-bar {
  width: 48px;
  height: 5px;
  background: var(--neutral-100);
  border-radius: 3px;
  overflow: hidden;
}
.rack-chip-bar i {
  display: block;
  height: 100%;
  background: var(--color-primary-500);
}
.rack-chip-meta {
  font-size: 11px;
  color: var(--neutral-400);
}
.rack-chip.active {
  border-color: var(--color-primary-500);
  background: var(--color-primary-50);
}

/* Body: elevations + connection panel */
.facility-body {
  display: flex;
  gap: var(--space-4);
  align-items: flex-start;
}
.elevations {
  display: flex;
  gap: var(--space-5);
  overflow-x: auto;
  padding-bottom: var(--space-3);
  flex: 1;
}

/* Rack column */
.rack-column {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex-shrink: 0;
}
.rack-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 4px;
}
.rack-title {
  display: flex;
  gap: 8px;
  align-items: baseline;
}
.rack-title strong {
  font-size: 14px;
}
.rack-title span {
  font-size: 11px;
  color: var(--neutral-400);
}
.rack-edit {
  cursor: pointer;
  color: var(--neutral-400);
}
.rack-warnings {
  display: flex;
  gap: 4px;
  padding: 0 4px;
}

/* Elevation */
.rack-elevation {
  display: flex;
  background: var(--neutral-900);
  border-radius: 6px;
  padding: 6px;
}
.u-ruler {
  display: flex;
  flex-direction: column;
  width: 26px;
}
.u-num {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--neutral-500);
  text-align: right;
  padding-right: 5px;
  line-height: 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}
.slot-area {
  position: relative;
  width: 180px;
  border-left: 1px solid rgba(255, 255, 255, 0.12);
  background-image: repeating-linear-gradient(
    to bottom,
    transparent 0,
    transparent 17px,
    rgba(255, 255, 255, 0.06) 17px,
    rgba(255, 255, 255, 0.06) 18px
  );
  border-radius: 3px;
}
.rack-device {
  position: absolute;
  left: 4px;
  right: 4px;
  margin: 0;
  padding: 0 6px;
  border: none;
  border-radius: 3px;
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: #fff;
  cursor: pointer;
  text-align: left;
  background: linear-gradient(180deg, #475569, #334155);
  overflow: hidden;
}
.rack-device.is-network_device {
  background: linear-gradient(180deg, #2563eb, #1d4ed8);
}
.rack-device.is-storage {
  background: linear-gradient(180deg, #7c3aed, #6d28d9);
}
.rack-device.is-security_device {
  background: linear-gradient(180deg, #dc2626, #b91c1c);
}
.rack-device.is-load_balancer {
  background: linear-gradient(180deg, #0891b2, #0e7490);
}
.rack-device.imp-core {
  box-shadow: inset 3px 0 0 var(--color-warning);
}
.rack-device.st-offline {
  filter: grayscale(0.7) opacity(0.7);
}
.rack-device.is-selected {
  outline: 2px solid #fbbf24;
}
.rack-device.is-uplink {
  outline: 2px solid #34d399;
}
.dev-ico {
  flex-shrink: 0;
}
.dev-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Connection panel */
.connection-panel {
  width: 300px;
  flex-shrink: 0;
  background: var(--surface-base);
  border: var(--border-base);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  box-shadow: var(--shadow-subtle);
  position: sticky;
  top: var(--space-4);
}
.cp-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.cp-sub {
  font-size: 12px;
  color: var(--neutral-400);
}
.cp-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  color: var(--neutral-400);
  padding: var(--space-6) 0;
}
.link-item {
  margin-bottom: var(--space-3);
}
.link-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}
.link-local em,
.link-peer em {
  font-style: normal;
  color: var(--neutral-400);
  margin-left: 4px;
  font-family: var(--font-mono);
  font-size: 11px;
}
.link-peer {
  font-weight: 600;
}
.link-tags {
  display: flex;
  gap: 4px;
  margin-top: 4px;
  flex-wrap: wrap;
}

/* Unlocated */
.unlocated-box {
  background: var(--surface-base);
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
}
.unlocated-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: var(--space-3);
}
.unlocated-list {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.unlocated-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.empty-hint {
  color: var(--neutral-400);
  font-size: 13px;
}
</style>
