<script setup lang="ts">
/**
 * P0 network interface inventory table (multi-NIC / multi-IP).
 * Embedded in the asset detail "Network Interfaces" tab.
 */
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  fetchInterfaces, createInterface, updateInterface, deleteInterface,
  fetchAssetList, fetchAsset,
} from '@/api/asset'
import type { NetworkInterface, NetworkInterfacePayload, AssetListItem } from '@/types/asset'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{ assetId: number }>()

const { t } = useI18n()
const authStore = useAuthStore()

const loading = ref(false)
const interfaces = ref<NetworkInterface[]>([])

/** Device types selectable as an upstream peer */
const PEER_TYPES = new Set([
  'network_device', 'storage', 'security_device', 'load_balancer',
])
const peerDevices = ref<AssetListItem[]>([])

// Dialog state
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const editingId = ref<number | null>(null)
const submitting = ref(false)

const emptyForm = (): NetworkInterfacePayload => ({
  name: '',
  mac_address: '',
  ip_address: '',
  cidr_prefix: null,
  vlan_id: null,
  gateway: '',
  role: 'data',
  bond_master: '',
  is_primary: false,
  status: 'active',
  connected_asset_id: null,
  connected_port: '',
})
const form = reactive<NetworkInterfacePayload>(emptyForm())

async function load() {
  loading.value = true
  try {
    interfaces.value = await fetchInterfaces(props.assetId)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  dialogMode.value = 'create'
  editingId.value = null
  Object.assign(form, emptyForm())
  dialogVisible.value = true
}

function openEdit(row: NetworkInterface) {
  dialogMode.value = 'edit'
  editingId.value = row.id
  Object.assign(form, {
    name: row.name || '',
    mac_address: row.mac_address || '',
    ip_address: row.ip_address || '',
    cidr_prefix: row.cidr_prefix,
    vlan_id: row.vlan_id,
    gateway: row.gateway || '',
    role: row.role,
    bond_master: row.bond_master || '',
    is_primary: row.is_primary,
    status: row.status,
    connected_asset_id: row.connected_asset_id,
    connected_port: row.connected_port || '',
  })
  dialogVisible.value = true
}

async function handleSubmit() {
  submitting.value = true
  try {
    const payload: NetworkInterfacePayload = { ...form }
    if (dialogMode.value === 'create') {
      await createInterface(props.assetId, payload)
      ElMessage.success(t('common.success'))
    } else if (editingId.value !== null) {
      await updateInterface(props.assetId, editingId.value, payload)
      ElMessage.success(t('common.success'))
    }
    dialogVisible.value = false
    await load()
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row: NetworkInterface) {
  await ElMessageBox.confirm(
    t('common.confirmDelete'),
    t('common.delete'),
    { type: 'warning', confirmButtonText: t('common.confirm'), cancelButtonText: t('common.cancel') },
  )
  await deleteInterface(props.assetId, row.id)
  ElMessage.success(t('common.success'))
  load()
}

function roleTagType(role: string): '' | 'success' | 'info' | 'warning' {
  if (role === 'data') return ''
  if (role === 'mgmt') return 'success'
  return 'info'
}

function _normDc(value: string | null | undefined): string | null {
  return (value || '').trim() || null
}

/** Load peer devices (switch/storage/security/LB) in the same datacenter. */
async function loadPeerDevices() {
  const parent = await fetchAsset(props.assetId)
  const parentDc = _normDc(parent.datacenter)
  const res = await fetchAssetList({ page_size: 100000 })
  peerDevices.value = res.items.filter((d) => {
    if (d.id === props.assetId) return false
    if (!PEER_TYPES.has(d.asset_type)) return false
    if (d.status === 'decommissioned') return false
    return _normDc(d.datacenter) === parentDc
  })
}

/** Option label: [type] hostname (ip) */
function peerLabel(d: AssetListItem): string {
  const typeLabel = t(`constants.assetTypes.${d.asset_type}`)
  const name = d.hostname || d.asset_no
  return `[${typeLabel}] ${name} (${d.ip_address})`
}

onMounted(async () => {
  await load()
  try {
    await loadPeerDevices()
  } catch { /* list remains empty; user can still type a port */ }
})
</script>

<template>
  <div class="nic-pane">
    <div class="nic-toolbar">
      <el-button
        v-if="authStore.isAdmin"
        type="primary"
        size="small"
        @click="openCreate"
      >
        <el-icon><Plus /></el-icon>
        {{ t('asset.detail.interfaceColumns.add') }}
      </el-button>
    </div>

    <el-table v-loading="loading" :data="interfaces" stripe style="width: 100%">
      <el-table-column width="64">
        <template #header>{{ t('asset.detail.interfaceColumns.primary') }}</template>
        <template #default="{ row }">
          <el-icon v-if="row.is_primary" color="var(--color-warning)"><StarFilled /></el-icon>
          <span v-else>-</span>
        </template>
      </el-table-column>

      <el-table-column
        prop="name"
        :label="t('asset.detail.interfaceColumns.name')"
        width="120"
      >
        <template #default="{ row }">
          <span class="ui-mono">{{ row.name || '-' }}</span>
        </template>
      </el-table-column>

      <el-table-column
        prop="mac_address"
        :label="t('asset.detail.interfaceColumns.mac')"
        width="160"
      >
        <template #default="{ row }">
          <span class="ui-mono ui-mono-muted">{{ row.mac_address || '-' }}</span>
        </template>
      </el-table-column>

      <el-table-column :label="t('asset.detail.interfaceColumns.ip')" min-width="170">
        <template #default="{ row }">
          <span class="ui-mono">
            {{ row.ip_address || '-' }}<em v-if="row.cidr_prefix != null">/{{ row.cidr_prefix }}</em>
          </span>
        </template>
      </el-table-column>

      <el-table-column
        prop="vlan_id"
        :label="t('asset.detail.interfaceColumns.vlan')"
        width="80"
      >
        <template #default="{ row }">{{ row.vlan_id ?? '-' }}</template>
      </el-table-column>

      <el-table-column
        prop="gateway"
        :label="t('asset.detail.interfaceColumns.gateway')"
        width="140"
      >
        <template #default="{ row }">
          <span class="ui-mono ui-mono-muted">{{ row.gateway || '-' }}</span>
        </template>
      </el-table-column>

      <el-table-column :label="t('asset.detail.interfaceColumns.role')" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="roleTagType(row.role)" effect="plain">
            {{ t(`asset.detail.interfaceColumns.role_${row.role}`) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column
        prop="bond_master"
        :label="t('asset.detail.interfaceColumns.bondMaster')"
        width="100"
      >
        <template #default="{ row }">
          <span class="ui-mono">{{ row.bond_master || '-' }}</span>
        </template>
      </el-table-column>

      <el-table-column
        :label="t('asset.detail.interfaceColumns.actions')"
        width="130"
        fixed="right"
      >
        <template #default="{ row }">
          <template v-if="authStore.isAdmin">
            <el-button link type="primary" size="small" @click="openEdit(row)">
              {{ t('common.edit') }}
            </el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">
              {{ t('common.delete') }}
            </el-button>
          </template>
          <span v-else class="ui-mono-muted">-</span>
        </template>
      </el-table-column>

      <template #empty>
        {{ t('asset.detail.interfaceColumns.empty') }}
      </template>
    </el-table>

    <!-- Add / edit dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create'
        ? t('asset.detail.interfaceColumns.add')
        : t('common.edit')"
      width="560px"
    >
      <el-form :model="form" label-width="110px">
        <el-form-item :label="t('asset.detail.interfaceColumns.name')">
          <el-input v-model="form.name" placeholder="eth0 / bond0 / ens192" style="width: 260px" />
        </el-form-item>
        <el-form-item :label="t('asset.detail.interfaceColumns.mac')">
          <el-input v-model="form.mac_address" style="width: 260px" />
        </el-form-item>
        <el-form-item :label="t('asset.detail.interfaceColumns.ip')">
          <el-input v-model="form.ip_address" style="width: 180px" />
          <el-input-number
            v-model="form.cidr_prefix"
            :min="0"
            :max="128"
            placeholder="/24"
            controls-position="right"
            style="width: 110px; margin-left: 10px"
          />
        </el-form-item>
        <el-form-item :label="t('asset.detail.interfaceColumns.gateway')">
          <el-input v-model="form.gateway" style="width: 260px" />
        </el-form-item>
        <el-form-item label="VLAN">
          <el-input-number v-model="form.vlan_id" :min="1" :max="4094" controls-position="right" />
        </el-form-item>
        <el-form-item :label="t('asset.detail.interfaceColumns.role')">
          <el-radio-group v-model="form.role">
            <el-radio value="data">{{ t('asset.detail.interfaceColumns.roleData') }}</el-radio>
            <el-radio value="mgmt">{{ t('asset.detail.interfaceColumns.roleMgmt') }}</el-radio>
            <el-radio value="other">{{ t('asset.detail.interfaceColumns.roleOther') }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="t('asset.detail.interfaceColumns.bondMaster')">
          <el-input v-model="form.bond_master" placeholder="bond0" style="width: 260px" />
        </el-form-item>
        <el-form-item :label="t('asset.detail.interfaceColumns.upSwitch')">
          <el-select
            v-model="form.connected_asset_id"
            filterable
            clearable
            :placeholder="t('asset.detail.interfaceColumns.upSwitchPlaceholder')"
            style="width: 320px"
          >
            <el-option
              v-for="d in peerDevices"
              :key="d.id"
              :label="peerLabel(d)"
              :value="d.id"
            />
          </el-select>
          <div v-if="!peerDevices.length" class="peer-hint">
            {{ t('asset.detail.interfaceColumns.noPeers') }}
          </div>
        </el-form-item>
        <el-form-item :label="t('asset.detail.interfaceColumns.upPort')">
          <el-input
            v-model="form.connected_port"
            placeholder="GE0/0/12"
            style="width: 260px"
          />
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="form.is_primary">
            {{ t('asset.detail.interfaceColumns.primary') }}
          </el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ t('common.save') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.nic-pane {
  padding-top: var(--space-4);
}
.peer-hint {
  width: 320px;
  margin-top: 4px;
  font-size: 12px;
  line-height: 16px;
  color: var(--color-warning);
}
.nic-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: var(--space-3);
}
.ui-mono em {
  font-style: normal;
  color: var(--neutral-400);
}
</style>
