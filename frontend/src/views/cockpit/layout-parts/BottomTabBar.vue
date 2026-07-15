<template>
  <header class="top-bar">
    <div class="brand">🚗 智慧驾舱 · 车机端</div>
    <div class="right">
      <span class="clock">{{ clock }}</span>
      <el-dropdown v-if="driver.user" @command="onLogout">
        <span class="user">{{ driver.user.full_name || driver.user.username }} ▾</span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useDriverStore } from '@/stores/driver.ts'

const driver = useDriverStore()
const router = useRouter()
const clock = ref('')
let timer: number | null = null

function refresh() {
  const d = new Date()
  clock.value = `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}:${d.getSeconds().toString().padStart(2, '0')}`
}
onMounted(() => {
  refresh()
  timer = window.setInterval(refresh, 1000)
})
onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})

function onLogout() {
  driver.logout()
  router.push('/cockpit/login')
}
</script>

<style scoped>
.top-bar {
  height: 56px;
  padding: 0 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--ck-bg-panel);
  border-bottom: 1px solid var(--ck-border);
}
.brand { font-size: 18px; font-weight: 600; }
.right { display: flex; align-items: center; gap: 20px; }
.clock { color: var(--ck-text-secondary); font-family: monospace; font-size: 14px; }
.user { cursor: pointer; color: var(--ck-text-primary); }
</style>