<script setup lang="ts">
/**
 * 安全报表 Dashboard
 * 基于 Claude Design 09-report-dashboard.html 实现
 */
import { ref, onMounted } from 'vue'
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

onMounted(loadData)
</script>

<template>
  <div v-loading="loading" class="report-page">
    <div class="page-head">
      <h1>安全报表</h1>
    </div>

    <!-- KPI 卡片 -->
    <div class="kpi-row">
      <div class="kpi danger">
        <div class="kpi-num">{{ dangerousPorts?.high_count || 0 }}</div>
        <div class="kpi-label">高危端口告警</div>
      </div>
      <div class="kpi warning">
        <div class="kpi-num">{{ dangerousPorts?.medium_count || 0 }}</div>
        <div class="kpi-label">中危端口告警</div>
      </div>
      <div class="kpi info">
        <div class="kpi-num">{{ shadowAssets?.total || 0 }}</div>
        <div class="kpi-label">影子资产</div>
      </div>
      <div class="kpi neutral">
        <div class="kpi-num">{{ portExposure?.top_ports?.length || 0 }}</div>
        <div class="kpi-label">暴露端口类型</div>
      </div>
    </div>

    <!-- 端口暴露面 Top 10 -->
    <div class="section-card">
      <h3>端口暴露面 Top 10</h3>
      <el-table :data="portExposure?.top_ports || []" stripe style="width: 100%">
        <el-table-column prop="port" label="端口" width="120">
          <template #default="{ row }">
            <span class="mono" style="font-weight: 600">{{ row.port }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="count" label="开放数量" width="120" />
        <el-table-column label="占比">
          <template #default="{ row }">
            <el-progress
              :percentage="portExposure?.top_ports?.[0]?.count ? Math.round(row.count / portExposure.top_ports[0].count * 100) : 0"
              :show-text="false"
              :stroke-width="8"
            />
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 按区域统计 -->
    <div class="section-card" v-if="portExposure?.zone_stats?.length">
      <h3>按网络区域统计</h3>
      <div class="zone-grid">
        <div v-for="stat in portExposure.zone_stats" :key="stat.zone" class="zone-item">
          <span class="zone-name">{{ zoneLabel(stat.zone) }}</span>
          <span class="zone-count mono">{{ stat.port_count }} 个开放端口</span>
        </div>
      </div>
    </div>

    <!-- 危险端口告警 -->
    <div class="section-card" v-if="dangerousPorts && dangerousPorts.alerts.length > 0">
      <h3>危险端口告警 ({{ dangerousPorts.total }})</h3>
      <el-table :data="dangerousPorts.alerts.slice(0, 20)" stripe style="width: 100%">
        <el-table-column prop="asset_no" label="资产编号" width="150">
          <template #default="{ row }">
            <span class="mono">{{ row.asset_no }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="ip_address" label="IP" width="140">
          <template #default="{ row }">
            <span class="mono">{{ row.ip_address }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="port_number" label="端口" width="80">
          <template #default="{ row }">
            <span class="mono" style="font-weight: 600">{{ row.port_number }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="service_name" label="服务" width="120" />
        <el-table-column prop="network_zone" label="区域" width="100">
          <template #default="{ row }">
            {{ zoneLabel(row.network_zone) }}
          </template>
        </el-table-column>
        <el-table-column prop="severity" label="严重性" width="100">
          <template #default="{ row }">
            <el-tag :type="row.severity === 'high' ? 'danger' : 'warning'" size="small">
              {{ row.severity === 'high' ? '高危' : '中危' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 影子资产 -->
    <div class="section-card" v-if="shadowAssets && shadowAssets.total > 0">
      <h3>影子资产 ({{ shadowAssets.total }})</h3>
      <div v-if="shadowAssets.incomplete_assets.length" style="margin-bottom: var(--space-4)">
        <h4 style="font-size: var(--fs-body); color: var(--neutral-700); margin-bottom: var(--space-2)">缺少关键字段</h4>
        <el-table :data="shadowAssets.incomplete_assets" stripe style="width: 100%">
          <el-table-column prop="asset_no" label="资产编号" width="150" />
          <el-table-column prop="ip_address" label="IP" width="140" />
          <el-table-column prop="hostname" label="主机名" width="160" />
          <el-table-column prop="reason" label="原因" />
        </el-table>
      </div>
      <div v-if="shadowAssets.long_offline_assets.length">
        <h4 style="font-size: var(--fs-body); color: var(--neutral-700); margin-bottom: var(--space-2)">长期离线</h4>
        <el-table :data="shadowAssets.long_offline_assets" stripe style="width: 100%">
          <el-table-column prop="asset_no" label="资产编号" width="150" />
          <el-table-column prop="ip_address" label="IP" width="140" />
          <el-table-column prop="hostname" label="主机名" width="160" />
          <el-table-column prop="missing_count" label="连续未扫到次数" width="140" />
        </el-table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.report-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.page-head h1 {
  margin: 0;
  font-size: var(--fs-h2);
  color: var(--neutral-900);
  font-weight: 600;
}

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
.kpi-num {
  font-size: 28px;
  font-weight: 600;
  font-family: var(--font-mono);
  color: var(--neutral-900);
}
.kpi-label {
  font-size: var(--fs-caption);
  color: var(--neutral-500);
  margin-top: var(--space-1);
}
.kpi.danger .kpi-num { color: var(--color-danger); }
.kpi.warning .kpi-num { color: var(--color-warning); }
.kpi.info .kpi-num { color: var(--color-info); }

/* 区块卡片 */
.section-card {
  background: var(--neutral-0);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
}
.section-card h3 {
  margin: 0 0 var(--space-4);
  font-size: var(--fs-h4);
  color: var(--neutral-900);
  font-weight: 600;
}

.zone-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
}
.zone-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3);
  background: var(--neutral-50);
  border-radius: var(--radius-md);
}
.zone-name { font-size: var(--fs-body); color: var(--neutral-700); }
.zone-count { font-size: 13px; color: var(--neutral-500); }

.mono { font-family: var(--font-mono); font-size: 13px; }
</style>
