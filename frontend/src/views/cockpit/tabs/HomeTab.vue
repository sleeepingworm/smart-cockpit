<template>
  <div class="home-tab">
    <!-- 左：地图 -->
    <div class="col-left">
      <CockpitMap @city-change="onCityChange" />
    </div>

    <!-- 右：天气 + 传感器 -->
    <div class="col-right">
      <WeatherCard :adcode="currentAdcode" />
      <div class="sensors">
        <SensorCard
          icon="🌡"
          label="温度"
          :value="readings?.temperature"
          unit="°C"
          color="#F56C6C"
          :warn-threshold="35"
        />
        <SensorCard
          icon="💧"
          label="湿度"
          :value="readings?.humidity"
          unit="%"
          color="#409EFF"
        />
        <SensorCard
          icon="💡"
          label="光照"
          :value="readings?.light"
          unit="lx"
          color="#E6A23C"
        />
        <SensorCard
          icon="🚨"
          label="烟雾"
          :value="readings?.smoke"
          unit=""
          color="#67C23A"
          :warn-threshold="200"
        />
      </div>
      <div class="footer-info">
        <el-tag size="small" :type="source === 'serial' ? 'success' : 'info'">
          {{ source === 'serial' ? '🟢 硬件在线' : '🔵 模拟数据' }}
        </el-tag>
        <span class="ts" v-if="readings?.timestamp">
          最近更新 {{ formatTime(readings.timestamp) }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useSensor } from '@/composables/useSensor'
import CockpitMap from '@/components/cockpit/CockpitMap.vue'
import WeatherCard from '@/components/cockpit/WeatherCard.vue'
import SensorCard from '@/components/cockpit/SensorCard.vue'

// 当前城市 adcode，由地图定位结果驱动，默认北京
const currentAdcode = ref('110000')

function onCityChange(payload: { adcode: string; city: string }) {
  if (payload.adcode) currentAdcode.value = payload.adcode
}

const { readings, source } = useSensor({ interval: 3000 })

function formatTime(ts: number) {
  return new Date(ts * 1000).toLocaleTimeString('zh-CN', { hour12: false })
}
</script>

<style scoped>
.home-tab {
  display: grid;
  grid-template-columns: 3fr 2fr;
  gap: 16px;
  height: calc(100vh - 56px - 64px - 32px);
  min-height: 480px;
}
.col-left, .col-right {
  min-height: 0;
}
.col-right {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.sensors {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.footer-info {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--ck-text-secondary);
  font-size: 12px;
}
.ts {
  font-family: 'Courier New', monospace;
}

@media (max-width: 900px) {
  .home-tab {
    grid-template-columns: 1fr;
    height: auto;
  }
}
</style>