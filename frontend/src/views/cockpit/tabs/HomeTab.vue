<!-- HomeTab.vue -->
<template>
  <el-card>
    <h2>欢迎，{{ driver.user?.full_name }}</h2>
    <p>今天是 {{ dateStr }}，祝您驾驶愉快 🚗</p>
    <p class="tips">Day 10 起：地图 · 天气 · 传感器将在此展示</p>
  </el-card>
</template>

<script setup lang="ts">
import { useDriverStore } from '@/stores/driver'
const driver = useDriverStore()
const dateStr = new Date().toLocaleDateString('zh-CN', {
  year: 'numeric', month: 'long', day: 'numeric', weekday: 'long',
})
</script>

<style scoped>
.tips { color: var(--ck-text-secondary); margin-top: 12px; }
</style>