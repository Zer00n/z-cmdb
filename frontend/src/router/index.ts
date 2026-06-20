/**
 * Vue Router 路由配置
 * /login 公开，其他路由需要登录
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

// ── 路由守卫：未登录跳转 /login ──────────────────────────────
router.beforeEach((to) => {
  const authStore = useAuthStore()

  if (to.meta.public) {
    // 已登录访问 /login，跳转首页
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
