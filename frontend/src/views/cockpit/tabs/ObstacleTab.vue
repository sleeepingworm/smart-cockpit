<template>
  <div class="obstacle-tab">
    <!-- 左：摄像头 + canvas 叠加层 -->
    <div class="panel-left">
      <div class="video-wrap">
        <video ref="videoRef" class="video mirrored" autoplay playsinline muted />
        <canvas ref="overlayRef" class="overlay mirrored" />
        <div v-if="!cameraOn" class="mask">
          <div class="mask-icon">🚧</div>
          <div class="mask-text">摄像头未开启</div>
        </div>
      </div>

      <div class="controls">
        <el-button v-if="!cameraOn" type="primary" size="large" @click="start">
          开始检测
        </el-button>
        <el-button v-else type="danger" size="large" @click="stop">
          停止检测
        </el-button>
      </div>
    </div>

    <!-- 右：状态面板 -->
    <div class="panel-right">
      <!-- 风险 badge -->
      <div class="badge" :class="badgeClass">
        <div class="badge-icon">{{ badgeIcon }}</div>
        <div class="badge-text">{{ badgeText }}</div>
      </div>

      <!-- 类别计数 -->
      <div class="cls-list" v-if="Object.keys(stats.class_counts).length">
        <div class="cls-title">当前画面</div>
        <div class="cls-grid">
          <div
            v-for="(count, name) in stats.class_counts"
            :key="name"
            class="cls-chip"
            :style="{ borderColor: colorOf(name), color: colorOf(name) }"
          >
            {{ labelOf(name) }} × {{ count }}
          </div>
        </div>
      </div>

      <el-descriptions :column="1" border size="small" class="stats">
        <el-descriptions-item label="总检测数">
          <span class="mono">{{ stats.count }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="平均置信度">
          <span class="mono">{{ (stats.avg_confidence * 100).toFixed(1) }}%</span>
        </el-descriptions-item>
        <el-descriptions-item label="单帧延迟">
          <span class="mono">{{ stats.latency_ms }} ms</span>
        </el-descriptions-item>
        <el-descriptions-item label="已处理帧">
          <span class="mono">{{ stats.frame_index }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="累计告警">{{ alertCount }} 次</el-descriptions-item>
      </el-descriptions>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/api/request'

const WS_URL = 'ws://127.0.0.1:8000/ws/obstacle'
const SEND_INTERVAL_MS = 200 // 5fps

// ============ 类型 ============
interface Box {
  x1: number; y1: number; x2: number; y2: number
  confidence: number; cls: number; cls_name: string
}

// ============ 摄像头 + WS ============
const videoRef = ref<HTMLVideoElement | null>(null)
const overlayRef = ref<HTMLCanvasElement | null>(null)
const stream = ref<MediaStream | null>(null)
const cameraOn = ref(false)
const ws = ref<WebSocket | null>(null)
let sendTimer: number | null = null
const alertCount = ref(0)
const dangerFlashUntil = ref(0)  // danger 级告警红光持续到

// ============ 统计数据 ============
const stats = reactive<{
  count: number
  class_counts: Record<string, number>
  avg_confidence: number
  latency_ms: number
  frame_index: number
  boxes: Box[]
  last_alert_level: string
}>({
  count: 0,
  class_counts: {},
  avg_confidence: 0,
  latency_ms: 0,
  frame_index: 0,
  boxes: [],
  last_alert_level: '',
})

// ============ 动态调色板（从后端 /obstacle/info 加载）============
const colorMap = ref<Record<string, string>>({})
const labelMap: Record<string, string> = {
  person: '行人',
  bicycle: '自行车',
  motorcycle: '摩托车',
  car: '汽车',
  bus: '公交车',
  truck: '卡车',
  'traffic light': '交通灯',
  'stop sign': '停止标志',
}

function pickColor(cls_name: string): string {
  if (cls_name === 'person') return '#F56C6C'
  if (['bicycle', 'motorcycle'].includes(cls_name)) return '#E6A23C'
  if (['car', 'bus', 'truck'].includes(cls_name)) return '#409EFF'
  if (['traffic light', 'stop sign'].includes(cls_name)) return '#E6C244'
  return '#909399'
}
const colorOf = (cls_name: string) => colorMap.value[cls_name] || '#909399'
const labelOf = (cls_name: string) => labelMap[cls_name] || cls_name

async function loadModelInfo() {
  try {
    const res: any = await request.get('/obstacle/info')
    const names: Record<string, string> = res.data.class_names || {}
    // 兼容 dict 键是 str/int
    for (const [_id, name] of Object.entries(names)) {
      colorMap.value[name] = pickColor(name)
    }
  } catch {
    // 拉不到时前端也能靠 pickColor 兜底
  }
}

// ============ Badge ============
const badgeClass = computed(() => {
  if (Date.now() < dangerFlashUntil.value) return 'badge-danger'
  if (stats.count > 0) return 'badge-warning'
  return 'badge-success'
})
const badgeIcon = computed(() => {
  if (Date.now() < dangerFlashUntil.value) return '🚨'
  if (stats.count > 0) return '⚠️'
  return '🟢'
})
const badgeText = computed(() => {
  if (Date.now() < dangerFlashUntil.value) return '注意前方有行人！'
  if (stats.count > 0) return `检测到 ${stats.count} 个障碍物`
  return '前方通畅'
})

// ============ 摄像头启停 ============
async function start() {
  try {
    stream.value = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480, facingMode: 'user' },
      audio: false,
    })
    if (videoRef.value) {
      videoRef.value.srcObject = stream.value
      try { await videoRef.value.play() } catch {}
    }
    cameraOn.value = true

    videoRef.value?.addEventListener('loadedmetadata', () => {
      syncCanvasSize()
      connectWS()
      startSending()
    }, { once: true })
  } catch (e: any) {
    let msg = '摄像头开启失败'
    if (e?.name === 'NotAllowedError') msg = '摄像头权限被拒绝'
    else if (e?.name === 'NotFoundError') msg = '未检测到摄像头设备'
    ElMessage.error(msg)
  }
}

function stop() {
  stopSending()
  ws.value?.close()
  ws.value = null
  stream.value?.getTracks().forEach(t => t.stop())
  stream.value = null
  cameraOn.value = false
  clearOverlay()
}

function syncCanvasSize() {
  if (!videoRef.value || !overlayRef.value) return
  overlayRef.value.width = videoRef.value.videoWidth
  overlayRef.value.height = videoRef.value.videoHeight
}

// ============ WebSocket ============
function connectWS() {
  ws.value = new WebSocket(WS_URL)
  ws.value.binaryType = 'blob'

  ws.value.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data)
      Object.assign(stats, msg)
      if (msg.alert_created) {
        alertCount.value++
        stats.last_alert_level = msg.alert?.level || ''
        if (msg.alert?.level === 'danger') {
          dangerFlashUntil.value = Date.now() + 3000  // 危险级红光 3s
        }
      }
      drawOverlay(msg.boxes || [])
    } catch { /* ignore */ }
  }

  ws.value.onerror = () => ElMessage.error('WebSocket 错误')
  ws.value.onclose = () => stopSending()
}

// ============ 定时抓帧 ============
function startSending() {
  if (sendTimer !== null) return
  sendTimer = window.setInterval(sendOneFrame, SEND_INTERVAL_MS)
}
function stopSending() {
  if (sendTimer !== null) { clearInterval(sendTimer); sendTimer = null }
}

function sendOneFrame() {
  if (!videoRef.value || !ws.value || ws.value.readyState !== WebSocket.OPEN) return
  const v = videoRef.value
  if (!v.videoWidth || !v.videoHeight) return

  const c = document.createElement('canvas')
  c.width = v.videoWidth
  c.height = v.videoHeight
  const ctx = c.getContext('2d')
  if (!ctx) return
  ctx.drawImage(v, 0, 0)   // 不镜像

  c.toBlob(
    (blob) => {
      if (blob && ws.value?.readyState === WebSocket.OPEN) ws.value.send(blob)
    },
    'image/jpeg',
    0.7,
  )
}

// ============ Canvas 叠加层 ============
function clearOverlay() {
  if (!overlayRef.value) return
  const ctx = overlayRef.value.getContext('2d')
  ctx?.clearRect(0, 0, overlayRef.value.width, overlayRef.value.height)
}

function drawOverlay(boxes: Box[]) {
  const canvas = overlayRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  ctx.lineWidth = 2
  ctx.font = '14px system-ui, -apple-system, sans-serif'

  for (const b of boxes) {
    const color = colorOf(b.cls_name)
    ctx.strokeStyle = color
    ctx.strokeRect(b.x1, b.y1, b.x2 - b.x1, b.y2 - b.y1)

    const label = `${labelOf(b.cls_name)} ${(b.confidence * 100).toFixed(0)}%`
    const textW = ctx.measureText(label).width
    const tagH = 18
    ctx.fillStyle = color
    ctx.fillRect(b.x1, b.y1 - tagH, textW + 8, tagH)
    ctx.fillStyle = '#000'
    ctx.fillText(label, b.x1 + 4, b.y1 - 4)
  }
}

onMounted(() => {
  loadModelInfo()
})
onBeforeUnmount(() => {
  stop()
})
</script>

<style scoped>
.obstacle-tab {
  display: grid;
  grid-template-columns: 3fr 2fr;
  gap: 16px;
  height: calc(100vh - 56px - 64px - 32px);
  min-height: 480px;
}
.panel-left, .panel-right {
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.video-wrap {
  flex: 1;
  position: relative;
  background: #000;
  border: 1px solid var(--ck-border);
  border-radius: 12px;
  overflow: hidden;
}
.video, .overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.video.mirrored, .overlay.mirrored { transform: scaleX(-1); }
.mask {
  position: absolute; inset: 0;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  background: rgba(10, 17, 40, 0.9);
  color: var(--ck-text-secondary);
  gap: 8px;
}
.mask-icon { font-size: 56px; }
.controls {
  margin-top: 12px;
  display: flex; gap: 12px; justify-content: center;
}

/* Badge */
.panel-right { gap: 12px; }
.badge {
  padding: 20px;
  border-radius: 12px;
  border: 1px solid var(--ck-border);
  background: var(--ck-bg-panel);
  text-align: center;
  transition: all 0.3s;
}
.badge-icon { font-size: 48px; line-height: 1; margin-bottom: 8px; }
.badge-text { color: var(--ck-text-primary); font-size: 16px; }
.badge-success { border-color: var(--ck-success); }
.badge-warning { border-color: #E6A23C; box-shadow: 0 0 24px rgba(230, 162, 60, 0.25); }
.badge-danger {
  border-color: var(--ck-danger);
  animation: pulse 1.4s ease-in-out infinite;
  box-shadow: 0 0 40px rgba(255, 107, 107, 0.4);
}
@keyframes pulse {
  0%, 100% { transform: scale(1);   opacity: 1; }
  50%      { transform: scale(1.02); opacity: 0.9; }
}

/* 类别 chip 列表 */
.cls-list {
  padding: 12px 16px;
  background: var(--ck-bg-panel);
  border: 1px solid var(--ck-border);
  border-radius: 10px;
}
.cls-title {
  color: var(--ck-text-secondary);
  font-size: 12px;
  margin-bottom: 8px;
}
.cls-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.cls-chip {
  padding: 4px 10px;
  border-radius: 12px;
  border: 1px solid;
  font-size: 12px;
  background: var(--ck-bg-elevated);
}

/* Stats */
.stats {
  background: var(--ck-bg-panel);
  border-radius: 12px;
}
.stats :deep(.el-descriptions__label),
.stats :deep(.el-descriptions__content) {
  background: var(--ck-bg-panel) !important;
  color: var(--ck-text-primary);
  border-color: var(--ck-border);
}
.mono {
  font-family: 'Courier New', Consolas, monospace;
  color: var(--ck-text-primary);
}

@media (max-width: 900px) {
  .obstacle-tab { grid-template-columns: 1fr; height: auto; }
}
</style>