<script setup lang="ts">
/**
 * UnitNode — Vue Flow custom node for a consuming unit card.
 * Shows unit name, type tag, instances, owner, with a colored left bar.
 */
import { Handle, Position } from '@vue-flow/core'

defineProps<{
  data: {
    unit: {
      id: string
      name: string
      type: string
      owner: string | null
      environment: string | null
      runtime: {
        instances: number
        cpu: number
        mem: number
        source: string
        observed_at: string
      } | null
    }
    color: string
  }
}>()

function typeLabel(type: string): string {
  const map: Record<string, string> = {
    k8s_workload: 'K8S',
    docker: 'Docker',
    vm_app: 'VM',
    host_process: 'Process',
  }
  return map[type] || type
}
</script>

<template>
  <div class="unit-node" :style="{ '--bar-color': data.color }">
    <Handle type="target" :position="Position.Left" />
    <div class="unit-content">
      <div class="unit-top">
        <span class="unit-name">{{ data.unit.name }}</span>
        <el-tag size="small" :style="{ fontSize: '10px' }">{{ typeLabel(data.unit.type) }}</el-tag>
      </div>
      <div class="unit-bottom">
        <span v-if="data.unit.runtime" class="unit-runtime">
          {{ data.unit.runtime.instances }}x · {{ data.unit.runtime.cpu }}c · {{ data.unit.runtime.mem }}MB
        </span>
        <span v-if="data.unit.owner" class="unit-owner">{{ data.unit.owner }}</span>
      </div>
    </div>
    <Handle type="source" :position="Position.Right" />
  </div>
</template>

<style scoped>
.unit-node {
  width: 100%;
  height: 100%;
  border: 1px solid var(--neutral-200);
  border-radius: 6px;
  background: white;
  display: flex;
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  transition: box-shadow 0.15s;
  box-sizing: border-box;
}
.unit-node:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
.unit-node::before {
  content: '';
  display: block;
  width: 4px;
  flex-shrink: 0;
  background: var(--bar-color, #94A3B8);
}
.unit-content {
  flex: 1;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
  min-width: 0;
}
.unit-top {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}
.unit-name {
  font-weight: 600;
  font-size: 13px;
  color: var(--neutral-900);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.unit-bottom {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: var(--neutral-500);
}
.unit-runtime {
  font-family: var(--font-mono);
  color: var(--neutral-600);
}
.unit-owner {
  color: var(--neutral-400);
}
</style>
