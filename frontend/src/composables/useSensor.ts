// frontend/src/composables/useSensor.ts
import { ref, onScopeDispose } from 'vue'
import request from '@/api/request'

export interface SensorReadings {
  temperature: number | null
  humidity: number | null
  light: number | null
  smoke: number | null
  potentiometer?: number | null
  card_id?: string | null
  connected: boolean
  source: 'serial' | 'mock' | 'none'
  timestamp: number
}

interface UseSensorOptions {
  /** true=WebSocket 模式；false=HTTP 轮询（默认） */
  useWebSocket?: boolean
  /** HTTP 轮询间隔 ms，默认 3000 */
  interval?: number
}

const WS_URL = 'ws://127.0.0.1:8000/ws/sensor'

export function useSensor(opts: UseSensorOptions = {}) {
  const { useWebSocket = false, interval = 3000 } = opts

  const readings = ref<SensorReadings | null>(null)
  const connected = ref(false)
  const source = ref<string>('none')
  const error = ref<string | null>(null)

  let timer: number | null = null
  let ws: WebSocket | null = null

  // ============ HTTP 轮询 ============
  async function pollOnce() {
    try {
      const res: any = await request.get('/sensor/latest')
      readings.value = res.data
      source.value = res.data.source
      connected.value = res.data.connected
      error.value = null
    } catch (e: any) {
      error.value = e.message
      // 降级：本地生成 mock 保证 UI 有数据
      readings.value = _localMock()
      source.value = 'mock'
      connected.value = false
    }
  }

  function startPolling() {
    pollOnce()   // 立即请求一次
    timer = window.setInterval(pollOnce, interval)
  }

  // ============ WebSocket 模式 ============
  function startWebSocket() {
    try {
      ws = new WebSocket(WS_URL)
      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data)
          readings.value = data
          source.value = data.source
          connected.value = data.connected
          error.value = null
        } catch {}
      }
      ws.onerror = () => {
        error.value = 'WebSocket 错误，降级为轮询'
        stopWebSocket()
        startPolling()   // 降级
      }
      ws.onclose = () => {
        // 意外关闭时降级
        if (readings.value === null) {
          startPolling()
        }
      }
    } catch {
      startPolling()
    }
  }

  function stopWebSocket() {
    if (ws) {
      ws.onmessage = null
      ws.onerror = null
      ws.onclose = null
      ws.close()
      ws = null
    }
  }

  function stop() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
    stopWebSocket()
  }

  // ============ 启动 ============
  if (useWebSocket) startWebSocket()
  else startPolling()

  // ⭐ 关键：组件卸载自动清理
  onScopeDispose(stop)

  return { readings, connected, source, error, stop }
}

// 兼容别名（旧代码里可能用了 useSensorMock）
export const useSensorMock = (intervalMs = 3000) =>
  useSensor({ interval: intervalMs })

// 本地兜底 mock
function _localMock(): SensorReadings {
  return {
    temperature: +(22 + Math.random() * 3 - 1.5).toFixed(1),
    humidity: +(45 + Math.random() * 10 - 5).toFixed(1),
    light: Math.round(500 + Math.random() * 200 - 100),
    smoke: Math.round(Math.random() * 30),
    connected: false,
    source: 'mock',
    timestamp: Date.now() / 1000,
  }
}