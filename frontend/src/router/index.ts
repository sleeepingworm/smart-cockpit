import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/LoginView.vue'),
      meta: { public: true, title: '管理员登录' },   // public=true表示不需要登录
    },
    {
      path: '/',
      redirect: '/dashboard',
    },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('../views/DashboardView.vue'),
      meta: { title: '仪表盘' },
    },
    {
      path: '/vehicles',
      name: 'Vehicles',
      component: () => import('../views/VehicleListView.vue'),
      meta: { title: '车辆管理' },
    },
    { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
  ],
})

// 路由守卫：每次路由切换前执行
router.beforeEach((to, _from, next) => {
  const userStore = useUserStore()

  // 公开页面直接放行
  if (to.meta.public) {
    // 已登录用户访问登录页→直接跳首页
    if (to.path === '/login' && userStore.isLoggedIn) {
      return next('/dashboard')
    }
    return next()
  }

  // 需要登录的页面：检查token
  if (!userStore.isLoggedIn) {
    ElMessage.warning('请先登录')
    return next('/login')
  }

  next()
})

// 页面标题
router.afterEach((to) => {
  document.title = `${to.meta.title || ''} - 智慧驾舱管理后台`
})

export default router