<template>
  <div class="weather-card">
    <div class="head">
      <div class="city">
        <el-icon><LocationInformation /></el-icon>
        {{ data?.city || '--' }}
      </div>
      <div class="source" v-if="data?.source">
        {{ data.source === 'mock' ? '模拟' : '实时' }}
      </div>
    </div>
    <div class="main">
      <div class="temp">
        <span class="num">{{ data?.temperature ?? '--' }}</span>
        <span class="unit">°C</span>
      </div>
      <div class="right">
        <div class="weather">{{ data?.weather || '--' }}</div>
        <div class="humid">湿度 {{ data?.humidity ?? '--' }}%</div>
        <div class="wind">{{ data?.winddirection }}风 {{ data?.windpower }} 级</div>
      </div>
    </div>
    <div v-if="data?.forecast?.length" class="forecast">
      <div v-for="d in data.forecast.slice(0, 3)" :key="d.date" class="fc-item">
        <div class="fc-date">{{ formatDay(d.date) }}</div>
        <div class="fc-w">{{ d.dayweather }}</div>
        <div class="fc-t">{{ d.nighttemp }}° ~ {{ d.daytemp }}°</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { LocationInformation } from '@element-plus/icons-vue'
import request from '@/api/request'

interface Weather {
  city: string
  temperature: string
  weather: string
  humidity: string
  winddirection: string
  windpower: string
  source: string
  forecast: Array<{ date: string; dayweather: string; daytemp: string; nighttemp: string }>
}

const props = defineProps<{
  adcode: string
}>()

const data = ref<Weather | null>(null)
let timer: number | null = null

async function fetchWeather() {
  try {
    const res: any = await request.get('/weather/current', {
      params: { city: props.adcode || '110000' },
    })
    data.value = res.data
  } catch {
    // 拦截器已经弹过错，不额外处理
  }
}

function formatDay(dateStr: string) {
  const d = new Date(dateStr)
  const now = new Date()
  const days = Math.round((d.getTime() - now.setHours(0, 0, 0, 0)) / 86400000)
  if (days === 0) return '今天'
  if (days === 1) return '明天'
  if (days === 2) return '后天'
  return `${d.getMonth() + 1}/${d.getDate()}`
}

// 城市切换时立即重拉
watch(() => props.adcode, (v) => {
  if (v) fetchWeather()
})

onMounted(() => {
  fetchWeather()
  timer = window.setInterval(fetchWeather, 10 * 60 * 1000)   // 10 分钟
})
onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.weather-card {
  padding: 16px;
  background: var(--ck-bg-panel);
  border: 1px solid var(--ck-border);
  border-radius: 10px;
  height: 100%;
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--ck-text-secondary);
  font-size: 13px;
  margin-bottom: 12px;
}
.city {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--ck-text-primary);
}
.source {
  padding: 2px 8px;
  border-radius: 10px;
  background: var(--ck-bg-elevated);
  font-size: 11px;
}
.main {
  display: flex;
  gap: 20px;
  align-items: center;
  margin-bottom: 12px;
}
.temp .num {
  font-size: 48px;
  font-weight: 700;
  background: linear-gradient(135deg, var(--ck-accent), var(--ck-accent-glow));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  line-height: 1;
}
.temp .unit {
  color: var(--ck-text-secondary);
  font-size: 16px;
  margin-left: 4px;
}
.right {
  color: var(--ck-text-secondary);
  font-size: 13px;
  line-height: 1.9;
}
.right .weather {
  color: var(--ck-text-primary);
  font-size: 16px;
  font-weight: 600;
}
.forecast {
  display: flex;
  gap: 8px;
  border-top: 1px solid var(--ck-border);
  padding-top: 12px;
}
.fc-item {
  flex: 1;
  text-align: center;
  color: var(--ck-text-secondary);
  font-size: 12px;
  line-height: 1.7;
}
.fc-item .fc-date {
  color: var(--ck-text-primary);
  font-weight: 600;
  margin-bottom: 2px;
}
.fc-item .fc-t {
  font-family: 'Courier New', monospace;
}
</style>