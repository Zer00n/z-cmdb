<script setup lang="ts">
/**
 * 扫描批次差异确认页
 * 基于 Claude Design 07-scan-confirm.htm.html 实现
 * 三段式：新发现 / 变更 / 消失
 */
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchScanDiff, confirmBatch, rejectBatch } from '@/api/scan'
import type { ScanDiffResponse, DiffNewHost, DiffChangedHost, DiffMissingHost, ScanConfirmRequest } from '@/types/scan'

const route = useRoute()
const router = useRouter()

const batchId = computed(() => Number(route.params.id))
const loading = ref(true)
const submitting = ref(false)
const activeTab = ref('new')

const diffData = ref<ScanDiffResponse | null>(null)

// 新发现资产的补充字段
interface NewAssetForm {
  ip_address: string
  hostname: string | null
  os_info: string | null
  asset_type: string
  location: string
  owner: string
  business_system: string
  importance: string
  network_zone: string
  selected: boolean
}

const newAssetForms = ref<NewAssetForm[]>([])

async function loadDiff() {
  loading.value = true
  try {
    diffData.value = await fetchScanDiff(batchId.value)
    // 初始化新资产表单
    newAssetForms.value = (diffData.value.new_hosts || []).map((h: DiffNewHost) => ({
      ip_address: h.ip_address,
      hostname: h.hostname,
      os_info: h.os_info,
      asset_type: 'virtual',
      location: '',
      owner: '',
      business_system: '',
      importance: 'normal',
      network_zone: 'intranet',
      selected: true,
    }))
  } finally {
    loading.value = false
  }
}

// 确认导入
async function handleConfirm() {
  if (!diffData.value) return

  // 校验选中的新资产必填字段
  const selectedNew = newAssetForms.value.filter(f => f.selected)
  for (const item of selectedNew) {
    if (!item.location || !item.owner || !item.business_system) {
      ElMessage.warning(`新资产 ${item.ip_address} 缺少必填字段（位置/负责人/业务系统）`)
      activeTab.value = 'new'
      return
    }
  }

  await ElMessageBox.confirm(
    `确认导入本批次？将录入 ${selectedNew.length} 个新资产，更新 ${diffData.value.changed_count} 个变更资产。`,
    '确认导入',
    { confirmButtonText: '确认导入', cancelButtonText: '取消', type: 'info' }
  )

  submitting.value = true
  try {
    const req: ScanConfirmRequest = {
      new_assets: selectedNew.map(f => ({
        ip_address: f.ip_address,
        asset_type: f.asset_type,
        location: f.location,
        owner: f.owner,
        business_system: f.business_system,
        importance: f.importance,
        network_zone: f.network_zone,
        hostname: f.hostname || undefined,
        os_info: f.os_info || undefined,
      })),
    }
    await confirmBatch(batchId.value, req)
    ElMessage.success('批次已确认导入')
    router.push('/scans')
  } finally {
    submitting.value = false
  }
}

// 拒绝批次
async function handleReject() {
  await ElMessageBox.confirm(
    '确认拒绝此批次？拒绝后数据不会入库。',
    '拒绝批次',
    { confirmButtonText: '确认拒绝', cancelButtonText: '取消', type: 'warning' }
  )
  submitting.value = true
  try {
    await rejectBatch(batchId.value)
    ElMessage.success('批次已拒绝')
    router.push('/scans')
  } finally {
    submitting.value = false
  }
}

// 全选/取消全选新资产
function toggleAllNew(checked: boolean) {
  newAssetForms.value.forEach(f => { f.selected = checked })
}

const allNewSelected = computed(() => newAssetForms.value.every(f => f.selected))

onMounted(loadDiff)
</script>

<template>
  <div v-loading="loading" class="scan-confirm-page">
    <template v-if="diffData">
      <!-- 页头 -->
      <div class="page-head">
        <div>
          <div class="title-row">
            <h1>扫描批次确认</h1>
            <span class="file-tag">{{ diffData.batch_name }}</span>
            <span class="status-tag">
              <span class="dot" />
              待确认
            </span>
          </div>
        </div>
        <div class="actions">
          <el-button @click="router.push('/scans')">
            <el-icon><ArrowLeft /></el-icon>
            返回列表
          </el-button>
        </div>
      </div>

      <!-- KPI 卡片 -->
      <div class="kpi-row">
        <div class="kpi total">
          <div class="kpi-body">
            <div class="kpi-label">本次扫描主机</div>
            <div class="kpi-num">{{ diffData.total_hosts }}</div>
          </div>
        </div>
        <div class="kpi new">
          <div class="kpi-body">
            <div class="kpi-label">新发现</div>
            <div class="kpi-num">{{ diffData.new_count }}</div>
          </div>
        </div>
        <div class="kpi chg">
          <div class="kpi-body">
            <div class="kpi-label">变更</div>
            <div class="kpi-num">{{ diffData.changed_count }}</div>
          </div>
        </div>
        <div class="kpi miss">
          <div class="kpi-body">
            <div class="kpi-label">消失</div>
            <div class="kpi-num">{{ diffData.missing_count }}</div>
          </div>
        </div>
      </div>

      <!-- Tab 区域 -->
      <div class="tabs-card">
        <el-tabs v-model="activeTab">
          <!-- 新发现 Tab -->
          <el-tab-pane :label="`新发现 (${diffData.new_count})`" name="new">
            <div v-if="newAssetForms.length === 0" class="empty-hint">本次扫描无新发现主机</div>
            <template v-else>
              <div class="tab-toolbar">
                <el-checkbox :model-value="allNewSelected" @change="toggleAllNew">全选</el-checkbox>
                <span class="hint">请为新发现资产补充必填字段后确认导入</span>
              </div>
              <div class="new-host-list">
                <div
                  v-for="(form, idx) in newAssetForms"
                  :key="form.ip_address"
                  class="new-host-card"
                  :class="{ disabled: !form.selected }"
                >
                  <div class="nh-head">
                    <el-checkbox v-model="form.selected" />
                    <span class="nh-ip mono">{{ form.ip_address }}</span>
                    <span v-if="form.hostname" class="nh-hostname">{{ form.hostname }}</span>
                    <span v-if="form.os_info" class="nh-os">{{ form.os_info }}</span>
                    <el-tag size="small" type="info" v-if="diffData.new_hosts[idx]?.ports?.length">
                      {{ diffData.new_hosts[idx].ports.length }} 端口
                    </el-tag>
                  </div>
                  <div v-if="form.selected" class="nh-form">
                    <div class="form-grid">
                      <div class="form-item">
                        <label>资产类型 *</label>
                        <el-select v-model="form.asset_type" size="small" style="width: 100%">
                          <el-option label="物理服务器" value="physical" />
                          <el-option label="虚拟机" value="virtual" />
                          <el-option label="网络设备" value="network_device" />
                          <el-option label="其他" value="other" />
                        </el-select>
                      </div>
                      <div class="form-item">
                        <label>网络区域 *</label>
                        <el-select v-model="form.network_zone" size="small" style="width: 100%">
                          <el-option label="内网" value="intranet" />
                          <el-option label="DMZ" value="dmz" />
                          <el-option label="办公网" value="office" />
                          <el-option label="管理网" value="management" />
                          <el-option label="其他" value="other" />
                        </el-select>
                      </div>
                      <div class="form-item">
                        <label>重要性 *</label>
                        <el-select v-model="form.importance" size="small" style="width: 100%">
                          <el-option label="核心" value="core" />
                          <el-option label="重要" value="important" />
                          <el-option label="普通" value="normal" />
                        </el-select>
                      </div>
                      <div class="form-item">
                        <label>物理位置 *</label>
                        <el-input v-model="form.location" size="small" placeholder="机房-机架-U位" />
                      </div>
                      <div class="form-item">
                        <label>负责人 *</label>
                        <el-input v-model="form.owner" size="small" placeholder="负责人姓名" />
                      </div>
                      <div class="form-item">
                        <label>业务系统 *</label>
                        <el-input v-model="form.business_system" size="small" placeholder="所属业务系统" />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </el-tab-pane>

          <!-- 变更 Tab -->
          <el-tab-pane :label="`变更 (${diffData.changed_count})`" name="changed">
            <div v-if="diffData.changed_hosts.length === 0" class="empty-hint">本次扫描无变更主机</div>
            <div v-else class="changed-list">
              <div
                v-for="host in diffData.changed_hosts"
                :key="host.ip_address"
                class="chg-card"
              >
                <div class="chg-head">
                  <span class="chg-id mono">{{ host.matched_asset_no || '-' }}</span>
                  <span class="chg-ip mono">{{ host.ip_address }}</span>
                  <span v-if="host.hostname" class="chg-hostname">{{ host.hostname }}</span>
                  <div class="chg-pills">
                    <span
                      v-for="pc in host.port_changes"
                      :key="`${pc.port_number}-${pc.protocol}`"
                      class="chg-pill"
                      :class="pc.change_type"
                    >
                      {{ pc.change_type === 'added' ? '+' : pc.change_type === 'removed' ? '−' : '~' }}
                      {{ pc.port_number }}/{{ pc.protocol }}
                      <template v-if="pc.new_service"> {{ pc.new_service }}</template>
                    </span>
                  </div>
                </div>
                <!-- 三栏对比 -->
                <div v-if="host.port_changes.length > 0" class="chg-body">
                  <div class="compare-head">
                    <div class="col-label">字段</div>
                    <div class="col-scan">扫描值</div>
                    <div class="col-current">当前值</div>
                  </div>
                  <div
                    v-for="pc in host.port_changes"
                    :key="`row-${pc.port_number}`"
                    class="compare-row"
                  >
                    <div class="col-label mono">{{ pc.port_number }}/{{ pc.protocol }}</div>
                    <div class="col-scan">
                      <span class="val">{{ pc.new_service || '-' }} {{ pc.new_version || '' }}</span>
                      <span v-if="pc.change_type === 'added'" class="diff-add">新增</span>
                    </div>
                    <div class="col-current">
                      <span class="val">{{ pc.old_service || '-' }} {{ pc.old_version || '' }}</span>
                      <span v-if="pc.change_type === 'removed'" class="diff-del">已关闭</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <!-- 消失 Tab -->
          <el-tab-pane :label="`消失 (${diffData.missing_count})`" name="missing">
            <div v-if="diffData.missing_hosts.length === 0" class="empty-hint">本次扫描无消失主机</div>
            <div v-else>
              <div class="missing-notice">
                <el-icon><InfoFilled /></el-icon>
                消失资产不会立即下线。连续 3 次扫描未发现后才会自动标记为离线（消失保护机制）。
              </div>
              <el-table :data="diffData.missing_hosts" stripe style="width: 100%">
                <el-table-column prop="matched_asset_no" label="资产编号" width="150">
                  <template #default="{ row }">
                    <span class="mono">{{ row.matched_asset_no || '-' }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="ip_address" label="IP 地址" width="140">
                  <template #default="{ row }">
                    <span class="mono">{{ row.ip_address }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="hostname" label="主机名" width="160" />
                <el-table-column prop="missing_count" label="连续未扫到" width="120">
                  <template #default="{ row }">
                    <span :class="{ 'text-warning': row.missing_count >= 2 }">
                      {{ row.missing_count }} 次
                    </span>
                  </template>
                </el-table-column>
                <el-table-column label="状态预测">
                  <template #default="{ row }">
                    <el-tag v-if="row.missing_count >= 2" type="warning" size="small">
                      下次将标记离线
                    </el-tag>
                    <span v-else class="text-muted">保持在线</span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>

      <!-- 底部操作栏 -->
      <div class="action-bar">
        <div class="action-left">
          <span class="summary-item new">新增 <b>{{ newAssetForms.filter(f => f.selected).length }}</b></span>
          <span class="summary-item chg">变更 <b>{{ diffData.changed_count }}</b></span>
          <span class="summary-item miss">消失 <b>{{ diffData.missing_count }}</b></span>
        </div>
        <div class="action-right">
          <el-button :loading="submitting" @click="handleReject">拒绝批次</el-button>
          <el-button type="primary" :loading="submitting" @click="handleConfirm">
            确认导入
          </el-button>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.scan-confirm-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

/* 页头 */
.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}
.title-row {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
  flex-wrap: wrap;
}
.page-head h1 {
  margin: 0;
  font-size: var(--fs-h2);
  color: var(--neutral-900);
  font-weight: 600;
}
.file-tag {
  font-family: var(--font-mono);
  font-size: 13px;
  background: var(--neutral-100);
  color: var(--neutral-700);
  border: 1px solid var(--neutral-200);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
}
.status-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: #FEF3C7;
  color: #92400E;
  font-size: 12px;
  padding: 1px 8px;
  border-radius: var(--radius-sm);
  font-weight: 500;
}
.status-tag .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #F59E0B;
}
.actions { display: flex; gap: var(--space-2); }

/* KPI */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-4);
}
.kpi {
  background: var(--neutral-0);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
}
.kpi-label {
  font-size: 11px;
  color: var(--neutral-500);
  font-family: var(--font-mono);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-bottom: 4px;
}
.kpi-num {
  font-size: 28px;
  font-weight: 600;
  font-family: var(--font-mono);
  color: var(--neutral-900);
}
.kpi.new .kpi-num { color: var(--color-primary-700); }
.kpi.chg .kpi-num { color: #B45309; }

/* Tabs */
.tabs-card {
  background: var(--neutral-0);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-lg);
  padding: var(--space-4) var(--space-6);
}

.empty-hint {
  text-align: center;
  padding: var(--space-8);
  color: var(--neutral-400);
  font-size: var(--fs-body);
}

/* 新发现 Tab */
.tab-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--neutral-200);
}
.tab-toolbar .hint {
  font-size: var(--fs-caption);
  color: var(--neutral-500);
}

.new-host-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.new-host-card {
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  overflow: hidden;
}
.new-host-card.disabled {
  opacity: 0.5;
}
.nh-head {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--neutral-50);
  border-bottom: 1px solid var(--neutral-200);
}
.nh-ip { font-weight: 600; color: var(--neutral-900); }
.nh-hostname { color: var(--neutral-700); }
.nh-os { font-size: var(--fs-caption); color: var(--neutral-500); }

.nh-form {
  padding: var(--space-4);
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
}
.form-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.form-item label {
  font-size: 12px;
  color: var(--neutral-600);
  font-weight: 500;
}

/* 变更 Tab */
.changed-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.chg-card {
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  overflow: hidden;
}
.chg-head {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--neutral-50);
}
.chg-id { color: var(--color-primary-500); font-size: 13px; }
.chg-ip { color: var(--neutral-900); font-weight: 500; }
.chg-hostname { color: var(--neutral-500); font-size: var(--fs-caption); }
.chg-pills { display: flex; gap: 6px; flex-wrap: wrap; margin-left: auto; }
.chg-pill {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 3px;
  font-family: var(--font-mono);
}
.chg-pill.added { background: #DCFCE7; color: #15803D; }
.chg-pill.removed { background: #FEE2E2; color: #B91C1C; }
.chg-pill.modified { background: #FEF3C7; color: #92400E; }

.chg-body {
  padding: var(--space-4);
  border-top: 1px solid var(--neutral-200);
  background: #FBFCFE;
}
.compare-head {
  display: grid;
  grid-template-columns: 140px 1fr 1fr;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
  font-size: 11px;
  color: var(--neutral-500);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.compare-row {
  display: grid;
  grid-template-columns: 140px 1fr 1fr;
  gap: var(--space-3);
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--neutral-100);
  font-size: var(--fs-body);
}
.compare-row:last-child { border-bottom: none; }
.col-label { color: var(--neutral-700); font-weight: 500; }
.col-scan .val { color: var(--neutral-900); }
.col-current .val { color: var(--neutral-500); }
.diff-add {
  font-size: 11px;
  background: #DCFCE7;
  color: #15803D;
  padding: 0 4px;
  border-radius: 3px;
  margin-left: 6px;
}
.diff-del {
  font-size: 11px;
  background: #FEE2E2;
  color: #B91C1C;
  padding: 0 4px;
  border-radius: 3px;
  margin-left: 6px;
}

/* 消失 Tab */
.missing-notice {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  background: var(--neutral-100);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  font-size: var(--fs-caption);
  color: var(--neutral-700);
  margin-bottom: var(--space-4);
}
.text-warning { color: #B45309; font-weight: 500; }
.text-muted { color: var(--neutral-400); font-size: var(--fs-caption); }

/* 底部操作栏 */
.action-bar {
  position: sticky;
  bottom: 0;
  background: var(--neutral-0);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-lg);
  padding: var(--space-3) var(--space-6);
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 -4px 12px -4px rgba(15, 23, 42, 0.04);
}
.action-left {
  display: flex;
  gap: var(--space-3);
}
.summary-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  background: var(--neutral-50);
  border: 1px solid var(--neutral-200);
  font-size: 12px;
  color: var(--neutral-700);
}
.summary-item b { font-family: var(--font-mono); font-weight: 600; }
.summary-item.new b { color: var(--color-primary-700); }
.summary-item.chg b { color: #B45309; }
.action-right { display: flex; gap: var(--space-3); }

.mono { font-family: var(--font-mono); font-size: 13px; }
</style>
