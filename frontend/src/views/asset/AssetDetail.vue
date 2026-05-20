<script setup lang="ts">
/**
 * 资产详情页
 * 基于 Claude Design 05-asset-detail.html 实现
 */
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchAsset, decommissionAsset, updateAsset } from '@/api/asset'
import type { Asset } from '@/types/asset'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const asset = ref<Asset | null>(null)
const activeTab = ref('basic')

const assetId = computed(() => Number(route.params.id))

async function loadAsset() {
  loading.value = true
  try {
    asset.value = await fetchAsset(assetId.value)
  } finally {
    loading.value = false
  }
}

async function handleDecommission() {
  if (!asset.value) return
  await ElMessageBox.confirm(
    `确认将资产 ${asset.value.asset_no} 标记为下线？`,
    '下线确认',
    { confirmButtonText: '确认下线', cancelButtonText: '取消', type: 'warning' }
  )
  await decommissionAsset(assetId.value)
  ElMessage.success('资产已下线')
  loadAsset()
}

async function handleRestore() {
  if (!asset.value) return
  await ElMessageBox.confirm(
    `确认将资产 ${asset.value.asset_no} 恢复为在线状态？`,
    '恢复上线',
    { confirmButtonText: '确认恢复', cancelButtonText: '取消', type: 'info' }
  )
  await updateAsset(assetId.value, { status: 'online' })
  ElMessage.success('资产已恢复上线')
  loadAsset()
}

function formatTime(t: string | null): string {
  if (!t) return '-'
  return dayjs(t).format('YYYY-MM-DD HH:mm')
}

function zoneLabel(zone: string): string {
  const map: Record<string, string> = {
    intranet: '内网', dmz: 'DMZ', office: '办公网', management: '管理网', other: '其他',
  }
  return map[zone] || zone
}

function typeLabel(t: string): string {
  const map: Record<string, string> = {
    physical: '物理服务器', virtual: '虚拟机', network_device: '网络设备', other: '其他',
  }
  return map[t] || t
}

function importanceLabel(imp: string): string {
  const map: Record<string, string> = { core: '核心', important: '重要', normal: '普通' }
  return map[imp] || imp
}

function statusLabel(s: string): string {
  const map: Record<string, string> = { online: '在线', offline: '离线', decommissioned: '已下线' }
  return map[s] || s
}

onMounted(loadAsset)
</script>

<template>
  <div v-loading="loading" class="asset-detail-page">
    <template v-if="asset">
      <!-- 页头 -->
      <div class="page-head">
        <div>
          <div class="title-row">
            <span class="id-tag">{{ asset.asset_no }}</span>
            <h1>{{ asset.hostname || asset.ip_address }}</h1>
          </div>
          <div class="sub-info">
            <span>{{ typeLabel(asset.asset_type) }}</span>
            <span class="sep">·</span>
            <span>{{ asset.business_system }}</span>
            <span class="sep">·</span>
            <span>最后扫描 {{ formatTime(asset.last_seen_at) }}</span>
          </div>
        </div>
        <div class="actions">
          <el-button @click="router.push('/assets')">
            <el-icon><ArrowLeft /></el-icon>
            返回列表
          </el-button>
          <el-button @click="router.push(`/assets/${asset.id}/edit`)">
            <el-icon><Edit /></el-icon>
            编辑
          </el-button>
          <el-button
            v-if="asset.status !== 'decommissioned'"
            type="danger"
            plain
            @click="handleDecommission"
          >
            下线
          </el-button>
          <el-button
            v-if="asset.status === 'decommissioned' || asset.status === 'offline'"
            type="success"
            plain
            @click="handleRestore"
          >
            恢复上线
          </el-button>
        </div>
      </div>

      <!-- 信息卡片 -->
      <div class="info-cards">
        <div class="info-card">
          <div class="ic-label">状态</div>
          <div class="ic-value">
            <span class="status-cell" :class="asset.status">
              <span class="status-dot" />
              {{ statusLabel(asset.status) }}
            </span>
          </div>
        </div>
        <div class="info-card">
          <div class="ic-label">网络区域 / IP</div>
          <div class="ic-value">
            <span class="zone-tag" :class="'zone-' + asset.network_zone.replace('management','mgmt')">
              {{ zoneLabel(asset.network_zone) }}
            </span>
            <span class="mono">{{ asset.ip_address }}</span>
          </div>
        </div>
        <div class="info-card">
          <div class="ic-label">重要性</div>
          <div class="ic-value">
            <span class="imp" :class="asset.importance">{{ importanceLabel(asset.importance) }}</span>
          </div>
        </div>
        <div class="info-card">
          <div class="ic-label">负责人</div>
          <div class="ic-value">{{ asset.owner }}</div>
        </div>
      </div>

      <!-- Tab 区域 -->
      <div class="tabs-card">
        <el-tabs v-model="activeTab">
          <el-tab-pane label="基本信息" name="basic">
            <div class="field-grid">
              <div class="field"><span class="lbl">资产编号</span><span class="val mono">{{ asset.asset_no }}</span></div>
              <div class="field"><span class="lbl">IP 地址</span><span class="val mono">{{ asset.ip_address }}</span></div>
              <div class="field"><span class="lbl">MAC 地址</span><span class="val mono">{{ asset.mac_address || '-' }}</span></div>
              <div class="field"><span class="lbl">主机名</span><span class="val">{{ asset.hostname || '-' }}</span></div>
              <div class="field"><span class="lbl">操作系统</span><span class="val">{{ asset.os_info || '-' }}</span></div>
              <div class="field"><span class="lbl">资产类型</span><span class="val">{{ typeLabel(asset.asset_type) }}</span></div>
              <div class="field"><span class="lbl">物理位置</span><span class="val">{{ asset.location }}</span></div>
              <div class="field"><span class="lbl">业务系统</span><span class="val">{{ asset.business_system }}</span></div>
              <div class="field"><span class="lbl">来源</span><span class="val">{{ asset.source === 'scan' ? '扫描导入' : '手动录入' }}</span></div>
              <div class="field"><span class="lbl">CPU</span><span class="val">{{ asset.cpu || '-' }}</span></div>
              <div class="field"><span class="lbl">内存</span><span class="val">{{ asset.memory_gb ? asset.memory_gb + ' GB' : '-' }}</span></div>
              <div class="field"><span class="lbl">磁盘</span><span class="val">{{ asset.disk_gb ? asset.disk_gb + ' GB' : '-' }}</span></div>
              <div class="field"><span class="lbl">采购日期</span><span class="val">{{ asset.purchase_date || '-' }}</span></div>
              <div class="field"><span class="lbl">保修到期</span><span class="val">{{ asset.warranty_expiry || '-' }}</span></div>
              <div class="field"><span class="lbl">创建时间</span><span class="val mono">{{ formatTime(asset.created_at) }}</span></div>
            </div>
            <div v-if="asset.remark" class="remark-block">
              <div class="remark-label">备注</div>
              <div class="remark-content">{{ asset.remark }}</div>
            </div>
          </el-tab-pane>

          <el-tab-pane :label="`端口 (${asset.ports.length})`" name="ports">
            <el-table :data="asset.ports" stripe style="width: 100%">
              <el-table-column prop="port_number" label="端口" width="100">
                <template #default="{ row }">
                  <span class="mono" style="font-weight: 600">{{ row.port_number }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="protocol" label="协议" width="80">
                <template #default="{ row }">
                  <el-tag size="small" effect="plain">{{ row.protocol }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="service_name" label="服务" width="140" />
              <el-table-column prop="service_version" label="版本" show-overflow-tooltip />
              <el-table-column prop="state" label="状态" width="100">
                <template #default="{ row }">
                  <span class="port-state" :class="row.state">
                    <span class="port-dot" />
                    {{ row.state }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column prop="last_seen_at" label="最后发现" width="160">
                <template #default="{ row }">
                  <span class="mono" style="font-size: 12px">{{ formatTime(row.last_seen_at) }}</span>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </div>
    </template>
  </div>
</template>

<style scoped>
.asset-detail-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

/* 页头 */
.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}
.title-row {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
}
.id-tag {
  font-family: var(--font-mono);
  font-size: 13px;
  background: var(--neutral-100);
  color: var(--neutral-700);
  border: 1px solid var(--neutral-200);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
}
.page-head h1 {
  margin: 0;
  font-size: var(--fs-h2);
  line-height: var(--lh-h2);
  color: var(--neutral-900);
  font-weight: 600;
}
.sub-info {
  margin-top: 6px;
  font-size: var(--fs-caption);
  color: var(--neutral-500);
  display: flex;
  gap: var(--space-3);
  align-items: center;
}
.sep { color: var(--neutral-300); }
.actions { display: flex; align-items: center; gap: var(--space-2); }

/* 信息卡片 */
.info-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-4);
}
.info-card {
  background: var(--neutral-0);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
}
.ic-label {
  font-size: 11px;
  font-family: var(--font-mono);
  color: var(--neutral-400);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-bottom: 6px;
}
.ic-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--neutral-900);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

/* 状态 */
.status-cell { display: inline-flex; align-items: center; gap: 6px; font-size: 14px; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; }
.status-cell.online .status-dot { background: var(--status-online); box-shadow: 0 0 0 3px rgba(22,163,74,0.16); }
.status-cell.offline .status-dot { background: var(--status-offline); }
.status-cell.decommissioned .status-dot { background: var(--status-decommissioned); }

/* 区域 */
.zone-tag { font-size: 13px; padding: 2px 8px; border-radius: var(--radius-sm); }
.zone-intranet { background: #DBE5FE; color: #1E40AF; }
.zone-dmz { background: #FEF3C7; color: #92400E; }
.zone-office { background: #CFFAFE; color: #0E7490; }
.zone-mgmt { background: #EDE9FE; color: #5B21B6; }

/* 重要性 */
.imp { font-size: 14px; }
.imp.core { color: var(--color-danger); }
.imp.important { color: var(--color-warning); }
.imp.normal { color: var(--neutral-500); }

.mono { font-family: var(--font-mono); font-size: 13px; }

/* Tab 卡片 */
.tabs-card {
  background: var(--neutral-0);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-lg);
  padding: var(--space-4) var(--space-6);
}

/* 字段网格 */
.field-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4) var(--space-8);
}
.field { display: flex; flex-direction: column; gap: 4px; }
.field .lbl { font-size: var(--fs-caption); color: var(--neutral-500); }
.field .val { font-size: var(--fs-body); color: var(--neutral-900); }

/* 备注 */
.remark-block {
  margin-top: var(--space-6);
  background: var(--neutral-50);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  padding: var(--space-4);
}
.remark-label { font-size: var(--fs-caption); color: var(--neutral-500); margin-bottom: var(--space-2); }
.remark-content { font-size: var(--fs-body); color: var(--neutral-700); line-height: 22px; }

/* 端口状态 */
.port-state { display: inline-flex; align-items: center; gap: 5px; font-size: 13px; }
.port-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--status-online); }
.port-state.closed .port-dot { background: var(--neutral-400); }
.port-state.filtered .port-dot { background: var(--color-warning); }
</style>
