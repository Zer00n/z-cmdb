/**
 * Vue Router configuration
 * /login is public; all other routes require authentication
 */
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

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
          path: 'help',
          name: 'Help',
          component: () => import('@/views/Help.vue'),
          meta: { title: 'router.help' },
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

// ── Route guard: redirect to /login if not authenticated ──────────────────────────────
router.beforeEach((to) => {
  const authStore = useAuthStore()

  if (to.meta.public) {
    // Already logged in visiting /login, redirect to home
    if (authStore.isLoggedIn && to.path === '/login') {
      return { path: '/' }
    }
    return true
  }

  if (!authStore.isLoggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  return true
})

export default router
