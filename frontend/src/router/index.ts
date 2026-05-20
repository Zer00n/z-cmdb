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
          redirect: '/assets',
        },
        {
          path: 'assets',
          name: 'AssetList',
          component: () => import('@/views/asset/AssetList.vue'),
          meta: { title: '资产管理' },
        },
        {
          path: 'assets/create',
          name: 'AssetCreate',
          component: () => import('@/views/asset/AssetForm.vue'),
          meta: { title: '新增资产' },
        },
        {
          path: 'assets/:id',
          name: 'AssetDetail',
          component: () => import('@/views/asset/AssetDetail.vue'),
          meta: { title: '资产详情' },
        },
        {
          path: 'assets/:id/edit',
          name: 'AssetEdit',
          component: () => import('@/views/asset/AssetForm.vue'),
          meta: { title: '编辑资产' },
        },
        {
          path: 'scans',
          name: 'ScanList',
          component: () => import('@/views/scan/ScanList.vue'),
          meta: { title: '扫描批次' },
        },
        {
          path: 'scans/:id/confirm',
          name: 'ScanConfirm',
          component: () => import('@/views/scan/ScanConfirm.vue'),
          meta: { title: '批次确认' },
        },
        {
          path: 'topology',
          name: 'TopologyEditor',
          component: () => import('@/views/topology/TopologyEditor.vue'),
          meta: { title: '拓扑图' },
        },
        {
          path: 'reports',
          name: 'ReportDashboard',
          component: () => import('@/views/report/ReportDashboard.vue'),
          meta: { title: '安全报表' },
        },
        {
          path: 'audit',
          name: 'AuditLog',
          component: () => import('@/views/audit/AuditLog.vue'),
          meta: { title: '审计日志' },
        },
        {
          path: 'users',
          name: 'UserList',
          component: () => import('@/views/user/UserList.vue'),
          meta: { title: '用户管理', roles: ['super_admin'] },
        },
        {
          path: 'settings',
          name: 'Settings',
          component: () => import('@/views/settings/Settings.vue'),
          meta: { title: '系统配置', roles: ['super_admin'] },
        },
        {
          path: 'help',
          name: 'Help',
          component: () => import('@/views/Help.vue'),
          meta: { title: '帮助' },
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
