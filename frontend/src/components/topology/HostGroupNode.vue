<script setup lang="ts">
/**
 * HostGroupNode — Vue Flow custom node for a host group container.
 * Renders host header (name/IP, cost, shared badge).
 * Child unit nodes are rendered inside by Vue Flow via parentId.
 */
import { Handle, Position } from '@vue-flow/core'

defineProps<{
  data: {
    host: {
      id: string
      name: string
      ip_address: string | null
      monthly_cost: number
      shared: boolean
      shares: { project_id: string; ratio: number }[]
    }
    unitCount: number
  }
}>()
</script>

<template>
  <div class="host-group-node" :class="{ shared: data.host.shared }">
    <div class="host-header">
      <div class="host-identity">
        <span class="host-name">{{ data.host.name }}</span>
        <span v-if="data.host.ip_address" class="host-ip">({{ data.host.ip_address }})</span>
      </div>
      <div class="host-meta">
        <span v-if="data.host.monthly_cost" class="host-cost">¥{{ data.host.monthly_cost.toLocaleString() }}</span>
        <el-tag v-if="data.host.shared" size="small" type="warning" class="shared-tag">
          多项目共享
        </el-tag>
      </div>
    </div>
    <div v-if="data.host.shared && data.host.shares.length" class="host-shares">
      <span v-for="share in data.host.shares" :key="share.project_id" class="share-item">
        {{ share.project_id.slice(0, 8) }}: {{ Math.round(share.ratio * 100) }}%
      </span>
    </div>
    <!-- Unit nodes are rendered here by Vue Flow (parentId nesting) -->
    <Handle type="target" :position="Position.Left" style="visibility: hidden" />
    <Handle type="source" :position="Position.Right" style="visibility: hidden" />
  </div>
</template>

<style scoped>
.host-group-node {
  width: 100%;
  height: 100%;
  border: 2px solid var(--neutral-300);
  border-radius: 10px;
  background: #EFF6FF;
  overflow: visible;
  box-sizing: border-box;
}
.host-group-node.shared {
  border-color: #F59E0B;
  background: #FFFBEB;
}
.host-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px 6px;
  gap: 8px;
}
.host-identity {
  display: flex;
  align-items: baseline;
  gap: 4px;
  min-width: 0;
}
.host-name {
  font-weight: 700;
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--neutral-900);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.host-ip {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--neutral-500);
  white-space: nowrap;
}
.host-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
.host-cost {
  font-family: var(--font-mono);
  color: var(--color-primary-700);
  font-size: 12px;
  font-weight: 600;
}
.shared-tag {
  font-size: 10px;
}
.host-shares {
  display: flex;
  gap: 8px;
  padding: 0 14px 6px;
  flex-wrap: wrap;
}
.share-item {
  font-size: 10px;
  color: #92400E;
  font-family: var(--font-mono);
  background: #FEF3C7;
  padding: 1px 6px;
  border-radius: 3px;
}
</style>
