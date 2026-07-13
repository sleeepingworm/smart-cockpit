<template>
  <div class="cockpit-root cockpit-shell">
    <TopStatusBar />
    <main class="cockpit-content">
      <router-view />
    </main>
    <BottomTabBar />
  </div>
</template>

<script setup lang="ts">
import TopStatusBar from './layout-parts/TopStatusBar.vue'
import BottomTabBar from './layout-parts/BottomTabBar.vue'
</script>

<style scoped>
.cockpit-shell {
  display: flex;
  flex-direction: column;
  height: 100vh;
}
.cockpit-content {
  flex: 1;
  overflow: auto;
  padding: 16px;
}
</style>