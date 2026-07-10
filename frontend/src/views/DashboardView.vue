<script setup lang="ts">
import { useUserStore } from '@/stores/user'
const userStore = useUserStore()
</script>

<template>
  <div style="padding:20px">
    <h2>欢迎，{{ userStore.user?.full_name || userStore.user?.username }}！</h2>
    <p>这是仪表盘，登录后才能看到。</p>
    <el-button type="danger" @click="userStore.logout(); router.push('/login')">退出登录</el-button>
  </div>
</template>