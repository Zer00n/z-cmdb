<script setup lang="ts">
/**
 * 侧边栏导航组件
 * 2026 UI Redesign：升级视觉（active 高亮渐变 + tooltip 优化），逻辑保持不变
 */
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { UserRole } from '@/types/auth'

interface NavItem {
  title: string
  route: string
  icon: string
  requiredRoles?: UserRole[]
  badge?: number
}

interface NavGroup {
  title: string
  requiredRoles?: UserRole[]
  items: NavItem[]
}

const props = defineProps<{
  collapsed: boolean
}>()

const route = useRoute()
const authStore = useAuthStore()

const navGroups: NavGroup[] = [
  {
    title: '资产管理',
    items: [
      { title: '资产列表', route: '/assets', icon: 'Monitor' },
    ],
  },
  {
    title: '扫描导入',
    items: [
      { title: '扫描批次', route: '/scans', icon: 'Upload' },
    ],
  },
  {
    title: '拓扑图',
    items: [
      { title: '拓扑图', route: '/topology', icon: 'Share' },
    ],
  },
  {
    title: '安全报表',
    items: [
      { title: '安全报表', route: '/reports', icon: 'DataAnalysis' },
    ],
  },
  {
    title: '审计',
    requiredRoles: ['super_admin', 'auditor'],
    items: [
      { title: '审计日志', route: '/audit', icon: 'Document', requiredRoles: ['super_admin', 'auditor'] },
    ],
  },
  {
    title: '系统管理',
    requiredRoles: ['super_admin'],
    items: [
      { title: '用户管理', route: '/users', icon: 'User', requiredRoles: ['super_admin'] },
      { title: '系统配置', route: '/settings', icon: 'Setting', requiredRoles: ['super_admin'] },
    ],
  },
]

const visibleGroups = computed(() => {
  const role = authStore.role
  if (!role) return []

  return navGroups
    .filter((g) => !g.requiredRoles || g.requiredRoles.includes(role))
    .map((g) => ({
      ...g,
      items: g.items.filter((item) => !item.requiredRoles || item.requiredRoles.includes(role)),
    }))
    .filter((g) => g.items.length > 0)
})

function isActive(itemRoute: string) {
  return route.path === itemRoute || route.path.startsWith(itemRoute + '/')
}
</script>

<template>
  <aside class="sidebar" :class="{ collapsed: props.collapsed }">
    <div class="sidebar-scroll">
      <div
        v-for="group in visibleGroups"
        :key="group.title"
        class="nav-group"
      >
        <div v-if="!props.collapsed" class="nav-group-head">
          {{ group.title }}
        </div>

        <router-link
          v-for="item in group.items"
          :key="item.route"
          :to="item.route"
          class="nav-item"
          :class="{ active: isActive(item.route) }"
        >
          <span class="nav-ico">
            <el-icon size="16">
              <component :is="item.icon" />
            </el-icon>
          </span>
          <span v-if="!props.collapsed" class="nav-label">{{ item.title }}</span>
          <span v-if="props.collapsed" class="nav-tip">{{ item.title }}</span>
        </router-link>
      </div>
    </div>

    <!-- 底部版权区 -->
    <div v-if="!props.collapsed" class="sidebar-foot">
      <span class="foot-line">CMDB Lite</span>
      <span class="foot-meta">v0.1.0 · 中小团队 · 准确性优先</span>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 220px;
  background: var(--surface-base);
  border-right: 1px solid rgba(15, 23, 42, 0.06);
  position: sticky;
  top: var(--topbar-h);
  align-self: start;
  height: calc(100vh - var(--topbar-h));
  display: flex;
  flex-direction: column;
  transition: width var(--dur-base) var(--ease-out);
  overflow: hidden;
}
.sidebar.collapsed {
  width: 60px;
}

.sidebar-scroll {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4) 0 var(--space-6);
}
.sidebar-scroll::-webkit-scrollbar { width: 4px; }
.sidebar-scroll::-webkit-scrollbar-thumb {
  background: var(--neutral-200);
  border-radius: 2px;
}

.nav-group + .nav-group {
  margin-top: var(--space-3);
}

.nav-group-head {
  padding: var(--space-3) var(--space-4) 6px;
  font-size: 10.5px;
  font-family: var(--font-mono);
  letter-spacing: 0.1em;
  color: var(--neutral-400);
  text-transform: uppercase;
  font-weight: 500;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: 36px;
  margin: 1px var(--space-2);
  padding: 0 10px;
  border-radius: var(--radius-md);
  color: var(--neutral-700);
  font-size: var(--fs-body);
  cursor: pointer;
  text-decoration: none;
  transition:
    background-color var(--dur-fast) var(--ease-out),
    color var(--dur-fast) var(--ease-out);
  white-space: nowrap;
}
.nav-item:hover {
  background: var(--color-primary-50);
  color: var(--neutral-900);
}
.nav-item:hover .nav-ico {
  color: var(--color-primary-500);
}
.nav-item.active {
  background: linear-gradient(90deg, rgba(37, 99, 235, 0.10) 0%, rgba(99, 102, 241, 0.06) 100%);
  color: var(--color-primary-700);
  font-weight: 600;
}
.nav-item.active .nav-ico {
  color: var(--color-primary-500);
}
.nav-item.active::before {
  content: '';
  position: absolute;
  left: -8px;
  top: 6px;
  bottom: 6px;
  width: 3px;
  background: var(--accent-gradient);
  border-radius: 0 2px 2px 0;
  box-shadow: 0 0 8px -1px rgba(37, 99, 235, 0.5);
}

.nav-ico {
  width: 18px;
  height: 18px;
  color: var(--neutral-400);
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: color var(--dur-fast) var(--ease-out);
}

.nav-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  letter-spacing: -0.005em;
}

/* 折叠态 */
.sidebar.collapsed .nav-item {
  justify-content: center;
  padding: 0;
  margin: 1px 8px;
}
.sidebar.collapsed .nav-item.active::before {
  top: 8px;
  bottom: 8px;
}

/* Tooltip */
.nav-tip {
  position: absolute;
  left: calc(100% + 10px);
  top: 50%;
  transform: translateY(-50%) translateX(-4px);
  background: var(--neutral-900);
  color: var(--neutral-0);
  font-size: 12px;
  line-height: 18px;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  white-space: nowrap;
  opacity: 0;
  pointer-events: none;
  transition:
    opacity var(--dur-fast) var(--ease-out),
    transform var(--dur-fast) var(--ease-out);
  z-index: 50;
  box-shadow: var(--shadow-floating);
}
.sidebar.collapsed .nav-item:hover .nav-tip {
  opacity: 1;
  transform: translateY(-50%) translateX(0);
}

/* 底部 */
.sidebar-foot {
  padding: var(--space-4);
  border-top: 1px solid var(--neutral-200);
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.foot-line {
  font-size: 12px;
  font-weight: 600;
  color: var(--neutral-700);
}
.foot-meta {
  font-size: 11px;
  color: var(--neutral-400);
  font-family: var(--font-mono);
  letter-spacing: 0.02em;
}
</style>
