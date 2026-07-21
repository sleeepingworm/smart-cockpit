import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useDriverStore } from '@/stores/driver'  // ← 稍后创建
import { ElMessage } from 'element-plus'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    // ============ 管理后台 ============
    {
      path: '/login',
      name: 'AdminLogin',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true, title: '管理员登录' },
    },
    {
      path: '/',
      component: () => import('@/layouts/AdminLayout.vue'),
      redirect: '/dashboard',
      meta: { requireAdmin: true },
      children: [
        { path: 'dashboard', component: () => import('@/views/DashboardView.vue'), meta: { title: '仪表盘' } },
        { path: 'users',     component: () => import('@/views/UserListView.vue'),  meta: { title: '用户管理' } },
        { path: 'vehicles',  component: () => import('@/views/VehicleListView.vue'), meta: { title: '车辆管理' } },
        { path: 'faces',     component: () => import('@/views/FaceListView.vue'),      meta: { title: '人脸库' } },
        { path: 'alerts',    component: () => import('@/views/AlertListView.vue'),     meta: { title: '告警管理' } },
      ],
    },

    // ============ 车机端 ============
    {
      path: '/cockpit/login',
      name: 'CockpitLogin',
      component: () => import('@/views/cockpit/FaceLoginView.vue'),
      meta: { public: true, title: '驾驶员登录' },
    },
    {
      path: '/cockpit',
      component: () => import('@/views/cockpit/CockpitLayout.vue'),
      redirect: '/cockpit/home',
      meta: { requireDriver: true },
      children: [
        { path: 'home',     name: 'CockpitHome',     component: () => import('@/views/cockpit/tabs/HomeTab.vue'),     meta: { title: '首页' } },
        { path: 'fatigue',  name: 'CockpitFatigue',  component: () => import('@/views/cockpit/tabs/FatigueTab.vue'), meta: { title: '疲劳检测' } },
        { path: 'obstacle', name: 'CockpitObstacle', component: () => import('@/views/cockpit/tabs/ObstacleTab.vue'), meta: { title: '障碍物检测' } },
        { path: 'voice',    name: 'CockpitVoice',    component: () => import('@/views/cockpit/tabs/VoiceTab.vue'), meta: { title: '语音助手' } },
        { path: 'profile',  name: 'CockpitProfile',  component: () => import('@/views/cockpit/tabs/PlaceholderTab.vue'), meta: { title: '个人中心' } },
      ],
    },

    // 兜底
    { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
  ],
})

// ============ 路由守卫 ============
router.beforeEach((to, _from) => {
  const userStore = useUserStore()
  const driverStore = useDriverStore()

  // 公开页
  if (to.meta.public) {
    if (to.path === '/login' && userStore.isLoggedIn) return '/dashboard'
    if (to.path === '/cockpit/login' && driverStore.isLoggedIn) return '/cockpit/home'
    return true
  }

  // 管理端页面
  if (to.meta.requireAdmin) {
    if (!userStore.isLoggedIn) {
      ElMessage.warning('请先登录')
      return '/login'
    }
    return true
  }

  // 车机端页面
  if (to.meta.requireDriver) {
    if (!driverStore.isLoggedIn) {
      ElMessage.warning('请先刷脸登录')
      return '/cockpit/login'
    }
    return true
  }

  return true
})

router.afterEach((to) => {
  document.title = `${to.meta.title || ''} - 智慧驾舱`
})

export default router