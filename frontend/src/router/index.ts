/**
 * Vue Router configuration
 * /login and /unlock are public; all other routes require authentication
 * When vault is LOCKED, all non-public routes redirect to /unlock
 */
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getLockStatus } from '@/api/vault'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/Login.vue'),
      meta: { public: true },
    },
    {
      path: '/unlock',
      name: 'VaultUnlock',
      component: () => import('@/views/Vault.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('@/layouts/MainLayout.vue'),
      children: [
        {
          path: '',
          redirect: '/dashboard',
        },
        {
          path: 'dashboard',
          name: 'Dashboard',
          component: () => import('@/views/dashboard/Dashboard.vue'),
          meta: { title: 'router.dashboard' },
        },
        {
          path: 'assets',
          name: 'AssetList',
          component: () => import('@/views/asset/AssetList.vue'),
          meta: { title: 'router.assetList' },
        },
        {
          path: 'assets/create',
          name: 'AssetCreate',
          component: () => import('@/views/asset/AssetForm.vue'),
          meta: { title: 'router.assetCreate' },
        },
        {
          path: 'assets/:id',
          name: 'AssetDetail',
          component: () => import('@/views/asset/AssetDetail.vue'),
          meta: { title: 'router.assetDetail' },
        },
        {
          path: 'assets/:id/edit',
          name: 'AssetEdit',
          component: () => import('@/views/asset/AssetForm.vue'),
          meta: { title: 'router.assetEdit' },
        },
        {
          path: 'scans',
          name: 'ScanList',
          component: () => import('@/views/scan/ScanList.vue'),
          meta: { title: 'router.scanBatches' },
        },
        {
          path: 'scans/:id/confirm',
          name: 'ScanConfirm',
          component: () => import('@/views/scan/ScanConfirm.vue'),
          meta: { title: 'router.scanConfirm' },
        },
        {
          path: 'import-presets',
          name: 'ImportPresets',
          component: () => import('@/views/ImportPresetSettings.vue'),
          meta: { title: 'router.importPresets' },
        },
        {
          path: 'topology',
          name: 'TopologyEditor',
          component: () => import('@/views/topology/TopologyEditor.vue'),
          meta: { title: 'router.topology' },
        },
        {
          path: 'reports',
          name: 'ReportDashboard',
          component: () => import('@/views/report/ReportDashboard.vue'),
          meta: { title: 'router.reports' },
        },
        // V0.4 Cost accounting routes
        {
          path: 'cost/overview',
          name: 'CostOverview',
          component: () => import('@/views/cost/CostOverview.vue'),
          meta: { title: 'router.costOverview' },
        },
        {
          path: 'cost/billing',
          name: 'DeptBilling',
          component: () => import('@/views/cost/DeptBilling.vue'),
          meta: { title: 'router.deptBilling' },
        },
        {
          path: 'cost/rates',
          name: 'CostRates',
          component: () => import('@/views/cost/CostRates.vue'),
          meta: { title: 'router.costRates', roles: ['super_admin'] },
        },
        {
          path: 'audit',
          name: 'AuditLog',
          component: () => import('@/views/audit/AuditLog.vue'),
          meta: { title: 'router.audit' },
        },
        {
          path: 'users',
          name: 'UserList',
          component: () => import('@/views/user/UserList.vue'),
          meta: { title: 'router.users', roles: ['super_admin'] },
        },
        {
          path: 'settings',
          name: 'Settings',
          component: () => import('@/views/settings/Settings.vue'),
          meta: { title: 'router.settings', roles: ['super_admin'] },
        },
        {
          path: 'departments',
          name: 'DepartmentManage',
          component: () => import('@/views/settings/DepartmentManage.vue'),
          meta: { title: 'router.departmentManage', roles: ['super_admin'] },
        },
        {
          path: 'help',
          name: 'Help',
          component: () => import('@/views/Help.vue'),
          meta: { title: 'router.help' },
        },
        // V0.6 project-perspective routes
        {
          path: 'projects',
          name: 'ProjectList',
          component: () => import('@/views/project/ProjectList.vue'),
          meta: { title: 'router.projectList' },
        },
        {
          path: 'projects/billing/departments',
          name: 'DeptCostSummary',
          component: () => import('@/views/project/DeptCostSummary.vue'),
          meta: { title: 'router.deptCostSummary' },
        },
        {
          path: 'projects/:id',
          name: 'ProjectArchitecture',
          component: () => import('@/views/project/ProjectArchitecture.vue'),
          meta: { title: 'router.projectArchitecture' },
        },
        {
          path: 'settings/billing-policy',
          name: 'BillingPolicy',
          component: () => import('@/views/settings/BillingPolicy.vue'),
          meta: { title: 'router.billingPolicy', roles: ['super_admin'] },
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

// ── Route guard: check vault lock status, then auth ─────────────────────
router.beforeEach(async (to) => {
  const authStore = useAuthStore()

  // Public routes: /login and /unlock are always accessible
  if (to.meta.public) {
    if (authStore.isLoggedIn && to.path === '/login') {
      return { path: '/' }
    }
    return true
  }

  // ── Vault lock-status check (cached in sessionStorage) ──
  let lockInfo: { state: string; needs_setup: boolean } | null = null
  const cached = sessionStorage.getItem('lock_status')
  if (cached) {
    try {
      lockInfo = JSON.parse(cached)
    } catch {
      sessionStorage.removeItem('lock_status')
    }
  }
  if (!lockInfo) {
    try {
      const status = await getLockStatus()
      lockInfo = status
      sessionStorage.setItem('lock_status', JSON.stringify(status))
    } catch {
      // lock-status unreachable — let through to normal auth flow
    }
  }
  if (lockInfo && (lockInfo.needs_setup || lockInfo.state === 'LOCKED')) {
    return { path: '/unlock' }
  }

  // ── Auth check ──
  if (!authStore.isLoggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  return true
})

export default router
