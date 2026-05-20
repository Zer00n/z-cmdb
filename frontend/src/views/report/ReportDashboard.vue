<script setup lang="ts">
/**
 * 安全报表 Dashboard
 * 2026 UI Redesign：升级 KPI hero、按区域分布的可视化、配色升级，逻辑保持不变
 */
import { ref, onMounted, computed } from 'vue'
import { fetchPortExposure, fetchDangerousPorts, fetchShadowAssets } from '@/api/report'
import type { PortExposureData, DangerousPortsData, ShadowAssetsData } from '@/types/report'

const loading = ref(true)
const portExposure = ref<PortExposureData | null>(null)
const dangerousPorts = ref<DangerousPortsData | null>(null)
const shadowAssets = ref<ShadowAssetsData | null>(null)

async function loadData() {
  loading.value = true
  try {
    const [pe, dp, sa] = await Promise.all([
      fetchPortExposure(),
      fetchDangerousPorts(),
      fetchShadowAssets(),
    ])
    portExposure.value = pe
    dangerousPorts.value = dp
    shadowAssets.value = sa
  } finally {
    loading.value = false
  }
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

const topPortMax = computed(() => {
  return portExposure.value?.top_ports?.[0]?.count || 1
})

const totalZonePorts = computed(() => {
  return portExposure.value?.zone_stats?.reduce((sum, s) => sum + s.port_count, 0) || 1
})

onMounted(loadData)
</script>

<template>
  <div v-loading="loading" class="ui-page">
    <!-- 页头 -->
    <div class="ui-page-head">
      <div>
        <h1 class="ui-page-title">安全报表</h1>
        <p class="ui-page-subtitle">基于已确认资产数据生成 · 实时计算</p>
      </div>
    </div>

    <!-- KPI hero 网格 -->
    <div class="ui-kpi-grid">
      <div class="ui-kpi is-danger">
        <div class="ui-kpi-head">
          <span class="ui-kpi-label">高危端口告警</span>
          <span class="ui-kpi-icon">
            <el-icon size="16"><Warning /></el-icon>
          </span>
        </div>
        <div class="ui-kpi-num">{{ dangerousPorts?.high_count || 0 }}</div>
        <div class="ui-kpi-foot">
          <el-icon size="12"><CaretTop /></el-icon>
          需立即处置（DMZ / 办公网暴露）
        </div>
      </div>

      <div class="ui-kpi is-warning">
        <div class="ui-kpi-head">
          <span class="ui-kpi-label">中危端口告警</span>
          <span class="ui-kpi-icon">
            <el-icon size="16"><InfoFilled /></el-icon>
          </span>
        </div>
        <div class="ui-kpi-num">{{ dangerousPorts?.medium_count || 0 }}</div>
        <div class="ui-kpi-foot">
          内网区域内的危险端口
        </div>
      </div>

      <div class="ui-kpi is-info">
        <div class="ui-kpi-head">
          <span class="ui-kpi-label">影子资产</span>
          <span class="ui-kpi-icon">
            <el-icon size="16"><View /></el-icon>
          </span>
        </div>
        <div class="ui-kpi-num">{{ shadowAssets?.total || 0 }}</div>
        <div class="ui-kpi-foot">
          缺失字段或长期离线
        </div>
      </div>

      <div class="ui-kpi is-accent">
        <div class="ui-kpi-head">
          <span class="ui-kpi-label">暴露端口类型</span>
          <span class="ui-kpi-icon">
            <el-icon size="16"><Connection /></el-icon>
          </span>
        </div>
        <div class="ui-kpi-num">{{ portExposure?.top_ports?.length || 0 }}</div>
        <div class="ui-kpi-foot">
          全网开放端口去重数
        </div>
      </div>
    </div>

    <!-- 端口暴露面 + 按区域统计 横向布局 -->
    <div class="row-2">
      <!-- 左：Top 10 端口 -->
      <div class="ui-card">
        <div class="ui-card-head">
          <h3 class="ui-card-title">
            <span class="title-dot dot-blue" />
            端口暴露面 Top 10
          </h3>
          <span class="card-meta">按开放数量排序</span>
        </div>
        <div class="port-list">
          <div
            v-for="(item, idx) in portExposure?.top_ports || []"
            :key="item.port"
            class="port-row"
          >
            <span class="port-rank">{{ String(idx + 1).padStart(2, '0') }}</span>
            <span class="port-num">{{ item.port }}</span>
            <div class="port-bar-wrap">
              <div
                class="port-bar"
                :style="{ width: `${(item.count / topPortMax) * 100}%` }"
              />
            </div>
            <span class="port-count">{{ item.count }}</span>
          </div>
          <div v-if="!portExposure?.top_ports?.length" class="ui-empty">
            <div class="ui-empty-title">暂无开放端口数据</div>
            <div class="ui-empty-desc">上传 nmap 扫描后将自动生成</div>
          </div>
        </div>
      </div>

      <!-- 右：按区域统计 -->
      <div class="ui-card">
        <div class="ui-card-head">
          <h3 class="ui-card-title">
            <span class="title-dot dot-purple" />
            按网络区域分布
          </h3>
          <span class="card-meta">所有开放端口</span>
        </div>
        <div class="zone-list">
          <div
            v-for="stat in portExposure?.zone_stats || []"
            :key="stat.zone"
            class="zone-row"
          >
            <span class="ui-zone" :class="zoneClass(stat.zone)">
              {{ zoneLabel(stat.zone) }}
            </span>
            <div class="zone-bar-wrap">
              <div
                class="zone-bar"
                :class="zoneClass(stat.zone)"
                :style="{ width: `${(stat.port_count / totalZonePorts) * 100}%` }"
              />
            </div>
            <span class="zone-count">{{ stat.port_count }}</span>
          </div>
          <div v-if="!portExposure?.zone_stats?.length" class="ui-empty">
            <div class="ui-empty-title">暂无区域数据</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 危险端口告警 -->
    <div v-if="dangerousPorts && dangerousPorts.alerts.length > 0" class="ui-card">
      <div class="ui-card-head">
        <h3 class="ui-card-title">
          <span class="title-dot dot-red" />
          危险端口告警
          <span class="ui-page-count">共 <b>{{ dangerousPorts.total }}</b> 项</span>
        </h3>
        <span class="card-meta">仅显示前 20 条</span>
      </div>
      <el-table :data="dangerousPorts.alerts.slice(0, 20)" stripe style="width: 100%">
        <el-table-column prop="asset_no" label="资产编号" width="160">
          <template #default="{ row }">
            <span class="ui-mono">{{ row.asset_no }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="ip_address" label="IP 地址" width="150">
          <template #default="{ row }">
            <span class="ui-mono">{{ row.ip_address }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="port_number" label="端口" width="90">
          <template #default="{ row }">
            <span class="port-chip">{{ row.port_number }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="service_name" label="服务" width="130" />
        <el-table-column prop="network_zone" label="区域" width="120">
          <template #default="{ row }">
            <span class="ui-zone" :class="zoneClass(row.network_zone)">
              {{ zoneLabel(row.network_zone) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="severity" label="严重性" width="110">
          <template #default="{ row }">
            <span class="ui-badge" :class="row.severity === 'high' ? 'is-danger' : 'is-warning'">
              <span class="ui-badge-dot" />
              {{ row.severity === 'high' ? '高危' : '中危' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="hostname" label="主机名" show-overflow-tooltip />
      </el-table>
    </div>

    <!-- 影子资产 -->
    <div v-if="shadowAssets && shadowAssets.total > 0" class="ui-card">
      <div class="ui-card-head">
        <h3 class="ui-card-title">
          <span class="title-dot dot-cyan" />
          影子资产
          <span class="ui-page-count">共 <b>{{ shadowAssets.total }}</b> 项</span>
        </h3>
      </div>
      <div style="padding: var(--space-2) var(--space-6) var(--space-4)">
        <div v-if="shadowAssets.incomplete_assets.length" style="margin-bottom: var(--space-4)">
          <h4 class="sub-title">缺少关键字段（{{ shadowAssets.incomplete_assets.length }}）</h4>
          <el-table :data="shadowAssets.incomplete_assets" stripe style="width: 100%">
            <el-table-column prop="asset_no" label="资产编号" width="160">
              <template #default="{ row }"><span class="ui-mono">{{ row.asset_no }}</span></template>
            </el-table-column>
            <el-table-column prop="ip_address" label="IP" width="150">
              <template #default="{ row }"><span class="ui-mono">{{ row.ip_address }}</span></template>
            </el-table-column>
            <el-table-column prop="hostname" label="主机名" width="180" />
            <el-table-column prop="reason" label="原因" />
          </el-table>
        </div>
        <div v-if="shadowAssets.long_offline_assets.length">
          <h4 class="sub-title">长期离线（{{ shadowAssets.long_offline_assets.length }}）</h4>
          <el-table :data="shadowAssets.long_offline_assets" stripe style="width: 100%">
            <el-table-column prop="asset_no" label="资产编号" width="160">
              <template #default="{ row }"><span class="ui-mono">{{ row.asset_no }}</span></template>
            </el-table-column>
            <el-table-column prop="ip_address" label="IP" width="150">
              <template #default="{ row }"><span class="ui-mono">{{ row.ip_address }}</span></template>
            </el-table-column>
            <el-table-column prop="hostname" label="主机名" width="180" />
            <el-table-column prop="missing_count" label="连续未扫到次数" width="160">
              <template #default="{ row }">
                <span class="ui-badge is-warning"><span class="ui-badge-dot" />{{ row.missing_count }}</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.row-2 {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: var(--space-4);
}

/* 卡片细节 */
.title-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dot-blue   { background: linear-gradient(135deg, #2563EB, #6366F1); }
.dot-purple { background: linear-gradient(135deg, #6366F1, #8B5CF6); }
.dot-red    { background: linear-gradient(135deg, #DC2626, #EA580C); }
.dot-cyan   { background: linear-gradient(135deg, #0891B2, #06B6D4); }

.card-meta {
  font-size: 12px;
  color: var(--neutral-500);
  font-family: var(--font-mono);
}

/* 端口列表 */
.port-list {
  padding: var(--space-3) var(--space-6) var(--space-4);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.port-row {
  display: grid;
  grid-template-columns: 28px 64px 1fr 60px;
  align-items: center;
  gap: var(--space-3);
  padding: 6px 0;
}
.port-rank {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--neutral-400);
  letter-spacing: 0.05em;
}
.port-num {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 600;
  color: var(--neutral-900);
}
.port-bar-wrap {
  height: 6px;
  background: var(--surface-sunken);
  border-radius: 6px;
  overflow: hidden;
}
.port-bar {
  height: 100%;
  background: linear-gradient(90deg, #2563EB 0%, #6366F1 100%);
  border-radius: 6px;
  box-shadow: 0 0 8px -1px rgba(37, 99, 235, 0.5);
  transition: width 360ms var(--ease-out);
}
.port-count {
  text-align: right;
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 600;
  color: var(--neutral-900);
}

/* 区域列表 */
.zone-list {
  padding: var(--space-3) var(--space-6) var(--space-4);
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.zone-row {
  display: grid;
  grid-template-columns: 90px 1fr 60px;
  align-items: center;
  gap: var(--space-3);
}
.zone-bar-wrap {
  height: 8px;
  background: var(--surface-sunken);
  border-radius: 8px;
  overflow: hidden;
}
.zone-bar {
  height: 100%;
  border-radius: 8px;
  transition: width 360ms var(--ease-out);
}
.zone-bar.zone-intranet { background: linear-gradient(90deg, #2563EB, #5A82F4); }
.zone-bar.zone-dmz      { background: linear-gradient(90deg, #B45309, #F59E0B); }
.zone-bar.zone-office   { background: linear-gradient(90deg, #0E7490, #06B6D4); }
.zone-bar.zone-mgmt     { background: linear-gradient(90deg, #6D28D9, #8B5CF6); }
.zone-bar.zone-other    { background: linear-gradient(90deg, #94A3B8, #CBD5E1); }

.zone-count {
  text-align: right;
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 600;
  color: var(--neutral-900);
}

/* 端口数字 chip */
.port-chip {
  display: inline-block;
  padding: 1px 8px;
  background: var(--surface-sunken);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 12.5px;
  font-weight: 600;
  color: var(--neutral-900);
}

.sub-title {
  margin: 0 0 var(--space-2);
  font-size: 13px;
  font-weight: 600;
  color: var(--neutral-700);
  letter-spacing: 0.02em;
}
</style>
