<template>
  <nav class="bottom-tab-bar">
    <button
      v-for="tab in tabs"
      :key="tab.path"
      class="tab-btn"
      :class="{ active: activeTab === tab.path }"
      @click="go(tab.path)"
    >
      <span class="tab-icon">{{ tab.icon }}</span>
      <span class="tab-label">{{ tab.label }}</span>
    </button>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const tabs = [
  { path: '/cockpit/home',     icon: '🏠', label: '首页' },
  { path: '/cockpit/fatigue',  icon: '😴', label: '疲劳检测' },
  { path: '/cockpit/obstacle', icon: '🚧', label: '障碍物检测' },
  { path: '/cockpit/voice',    icon: '🎤', label: '语音助手' },
  { path: '/cockpit/profile',  icon: '👤', label: '个人中心' },
]

const activeTab = computed(() => route.path)

function go(path: string) {
  if (route.path !== path) {
    router.push(path)
  }
}
</script>

<style scoped>
.bottom-tab-bar {
  display: flex;
  align-items: stretch;
  height: 64px;
  background: var(--ck-bg-panel, #131a35);
  border-top: 1px solid var(--ck-border, #2d3556);
  flex-shrink: 0;
}

.tab-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  background: transparent;
  border: none;
  color: var(--ck-text-secondary, #8b95c9);
  cursor: pointer;
  transition: color 0.2s, background 0.2s;
  position: relative;
  padding: 4px 0;
}

.tab-btn:hover {
  color: var(--ck-text-primary, #eef2ff);
  background: rgba(255, 255, 255, 0.03);
}

.tab-btn.active {
  color: var(--ck-accent, #4e7cff);
}

.tab-btn.active::after {
  content: '';
  position: absolute;
  top: 0;
  left: 20%;
  right: 20%;
  height: 2px;
  background: var(--ck-accent, #4e7cff);
  border-radius: 0 0 2px 2px;
}

.tab-icon {
  font-size: 20px;
  line-height: 1;
}

.tab-label {
  font-size: 11px;
  line-height: 1;
}
</style>