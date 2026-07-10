<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

// 侧边栏菜单配置
const menus = [
  { path: '/dashboard', title: '仪表盘', icon: 'Odometer' },
  { path: '/users', title: '用户管理', icon: 'User' },
  { path: '/vehicles', title: '车辆管理', icon: 'Van' },
  { path: '/faces', title: '人脸库', icon: 'Picture' },
  { path: '/alerts', title: '告警管理', icon: 'Bell' },
]

const activeMenu = computed(() => route.path)

function handleLogout() {
  userStore.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<template>
  <el-container class="admin-layout">
    <!-- 侧边栏 -->
    <el-aside width="220px" class="sidebar">
      <div class="logo">🚗 智慧驾舱</div>
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <el-menu-item v-for="m in menus" :key="m.path" :index="m.path">
          <el-icon><component :is="m.icon" /></el-icon>
          <span>{{ m.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主容器 -->
    <el-container>
      <!-- 顶部导航 -->
      <el-header class="header">
        <el-breadcrumb separator="/">
          <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
          <el-breadcrumb-item v-if="route.meta.title">{{ route.meta.title }}</el-breadcrumb-item>
        </el-breadcrumb>
        <div class="header-right">
          <el-dropdown @command="handleLogout">
            <span class="user-info">
              <el-icon><UserFilled /></el-icon>
              {{ userStore.user?.full_name || userStore.user?.username }}
              <el-icon><CaretBottom /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 主内容区 -->
      <el-main class="main-content">
        <div class="page-container">
          <h2 class="page-title">{{ route.meta.title }}</h2>
          <RouterView />
        </div>
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.admin-layout { height: 100vh; }
.sidebar { background-color: #304156; overflow: hidden; }
.logo {
  height: 60px; line-height: 60px; text-align: center;
  color: white; font-size: 18px; font-weight: bold;
  border-bottom: 1px solid #1f2d3d;
}
.sidebar :deep(.el-menu) { border-right: none; }
.header {
  background: white; border-bottom: 1px solid #e6e6e6;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 20px;
}
.header-right .user-info {
  cursor: pointer; display: flex; align-items: center; gap: 6px;
  color: #333;
}
.user-info:hover { color: #409EFF; }
.main-content { background: #f0f2f5; padding: 20px; overflow-y: auto; }
.page-container { background: white; padding: 20px; border-radius: 8px; min-height: calc(100vh - 160px); }
.page-title { margin: 0 0 20px 0; font-size: 20px; color: #303133; border-bottom: 1px solid #eee; padding-bottom: 12px; }
</style>