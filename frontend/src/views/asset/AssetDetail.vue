<script setup lang="ts">
/**
 * 资产详情页
 * 2026 UI Redesign：升级头部 hero 区与信息卡片，业务逻辑保持不变
 */
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchAsset, decommissionAsset, updateAsset } from '@/api/asset'
import type { Asset } from '@/types/asset'
import AppServiceTable from '@/components/asset/AppServiceTable.vue'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const asset = ref<Asset | null>(null)
const activeTab = ref('basic')
const appCount = ref(0)

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

function zoneClass(zone: string): string {
  const map: Record<string, string> = {
    intranet: 'zone-intranet',
    dmz: 'zone-dmz',
    office: 'zone-office',
    management: 'zone-mgmt',
    other: 'zone-other',
  }
  return map[zone] || 'zone-other'
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
  <div v-loading="loading" class="ui-page">
    <template v-if="asset">
      <!-- Hero 头部 -->
      <div class="hero-card">
        <div class="hero-grad" aria-hidden="true" />
        <div class="hero-main">
          <div class="hero-meta">
            <span class="hero-id">{{ asset.asset_no }}</span>
            <span class="ui-status" :class="'is-' + asset.status">{{ statusLabel(asset.status) }}</span>
          </div>
          <h1 class="hero-title">{{ asset.hostname || asset.ip_address }}</h1>
          <div class="hero-sub">
            <span class="ui-mono">{{ asset.ip_address }}</span>
            <span class="hero-sep" />
            <span>{{ typeLabel(asset.asset_type) }}</span>
            <span class="hero-sep" />
            <span>{{ asset.business_system }}</span>
            <span class="hero-sep" />
            <span>最后扫描 {{ formatTime(asset.last_seen_at) }}</span>
          </div>
        </div>
        <div class="hero-actions">
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
          <div class="ic-label">网络区域</div>
          <div class="ic-value">
            <span class="ui-zone" :class="zoneClass(asset.network_zone)">
              {{ zoneLabel(asset.network_zone) }}
            </span>
          </div>
        </div>
        <div class="info-card">
          <div class="ic-label">重要性</div>
          <div class="ic-value">
            <span class="ui-imp" :class="'is-' + asset.importance">{{ importanceLabel(asset.importance) }}</span>
          </div>
        </div>
        <div class="info-card">
          <div class="ic-label">负责人</div>
          <div class="ic-value">{{ asset.owner }}</div>
        </div>
        <div class="info-card">
          <div class="ic-label">来源</div>
          <div class="ic-value">{{ asset.source === 'scan' ? '扫描导入' : '手动录入' }}</div>
        </div>
      </div>

      <!-- Tab 区域 -->
      <div class="ui-card">
        <el-tabs v-model="activeTab" style="padding: 0 var(--space-6)">
          <el-tab-pane label="基本信息" name="basic">
            <div class="field-grid">
              <div class="field"><span class="lbl">资产编号</span><span class="val ui-mono">{{ asset.asset_no }}</span></div>
              <div class="field"><span class="lbl">IP 地址</span><span class="val ui-mono">{{ asset.ip_address }}</span></div>
              <div class="field"><span class="lbl">MAC 地址</span><span class="val ui-mono">{{ asset.mac_address || '-' }}</span></div>
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
              <div class="field"><span class="lbl">创建时间</span><span class="val ui-mono">{{ formatTime(asset.created_at) }}</span></div>
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
                  <span class="port-chip">{{ row.port_number }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="protocol" label="协议" width="80">
                <template #default="{ row }">
                  <el-tag size="small" effect="plain">{{ row.protocol }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="service_name" label="服务" width="140" />
              <el-table-column prop="service_version" label="版本" show-overflow-tooltip />
              <el-table-column prop="state" label="状态" width="110">
                <template #default="{ row }">
                  <span class="port-state" :class="row.state">
                    <span class="port-dot" />
                    {{ row.state }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column prop="last_seen_at" label="最后发现" width="170">
                <template #default="{ row }">
                  <span class="ui-mono ui-mono-muted">{{ formatTime(row.last_seen_at) }}</span>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <el-tab-pane :label="`应用 (${appCount})`" name="apps">
            <AppServiceTable
              :asset-id="assetId"
              @count-change="(n: number) => appCount = n"
            />
          </el-tab-pane>
        </el-tabs>
      </div>
    </template>
  </div>
</template>

<style scoped>
/* Hero */
.hero-card {
  position: relative;
  background: var(--surface-base);
  border: var(--border-base);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-4);
  overflow: hidden;
  box-shadow: var(--shadow-subtle);
}
.hero-grad {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(420px 280px at 0% 0%, rgba(37, 99, 235, 0.08) 0%, transparent 60%),
    radial-gradient(360px 220px at 100% 0%, rgba(99, 102, 241, 0.06) 0%, transparent 55%);
}
.hero-main {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
}
.hero-meta {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.hero-id {
  font-family: var(--font-mono);
  font-size: 12.5px;
  font-weight: 600;
  color: var(--color-primary-700);
  background: var(--color-primary-50);
  border: 1px solid rgba(37, 99, 235, 0.16);
  padding: 3px 10px;
  border-radius: 999px;
}
.hero-title {
  margin: 0;
  font-size: 28px;
  line-height: 36px;
  font-weight: 700;
  color: var(--neutral-900);
  letter-spacing: -0.02em;
}
.hero-sub {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: var(--neutral-500);
  flex-wrap: wrap;
}
.hero-sep {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--neutral-300);
}
.hero-actions {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}

/* 信息卡片 */
.info-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-4);
}
.info-card {
  background: var(--surface-base);
  border: var(--border-base);
  border-radius: var(--radius-lg);
  padding: var(--space-4) var(--space-6);
  box-shadow: var(--shadow-subtle);
  transition: box-shadow var(--dur-base) var(--ease-out);
}
.info-card:hover {
  box-shadow: var(--shadow-medium);
  border-color: var(--neutral-300);
}
.ic-label {
  font-size: 11px;
  font-family: var(--font-mono);
  color: var(--neutral-400);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 8px;
}
.ic-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--neutral-900);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 24px;
}

/* 字段网格 */
.field-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4) var(--space-8);
  padding: var(--space-2) 0 var(--space-4);
}
.field { display: flex; flex-direction: column; gap: 4px; }
.field .lbl {
  font-size: 11px;
  color: var(--neutral-400);
  font-family: var(--font-mono);
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.field .val {
  font-size: var(--fs-body);
  color: var(--neutral-900);
}

/* 备注 */
.remark-block {
  margin-top: var(--space-4);
  background: var(--surface-sunken);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  padding: var(--space-4);
}
.remark-label {
  font-size: 11px;
  color: var(--neutral-400);
  font-family: var(--font-mono);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: var(--space-2);
}
.remark-content {
  font-size: var(--fs-body);
  color: var(--neutral-700);
  line-height: 22px;
}

/* 端口 chip */
.port-chip {
  display: inline-block;
  padding: 2px 10px;
  background: var(--surface-sunken);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 600;
  color: var(--neutral-900);
}

.port-state { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; }
.port-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--status-online); flex-shrink: 0; }
.port-state.closed .port-dot { background: var(--neutral-400); }
.port-state.filtered .port-dot { background: var(--color-warning); }
</style>
