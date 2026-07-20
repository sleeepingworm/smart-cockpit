<template>
  <div class="fatigue-tab">
    <!-- 左：摄像头 + canvas 叠加层 -->
    <div class="panel-left">
      <div class="video-wrap" ref="wrapRef">
        <video
          ref="videoRef"
          class="video mirrored"
          autoplay
          playsinline
          muted
        />
        <canvas ref="overlayRef" class="overlay mirrored" />
        <div v-if="!cameraOn" class="mask">
          <div class="mask-icon">🎥</div>
          <div class="mask-text">摄像头未开启</div>
        </div>
      </div>

      <div class="controls">
        <el-button
          v-if="!cameraOn"
          type="primary"
          size="large"
          @click="start"
        >开始检测</el-button>
        <el-button v-else type="danger" size="large" @click="stop">
          停止检测
        </el-button>
      </div>
    </div>

    <!-- 右：状态面板 -->
    <div class="panel-right">
      <div class="badge" :class="badgeClass">
        <div class="badge-icon">{{ badgeIcon }}</div>
        <div class="badge-text">{{ badgeText }}</div>
      </div>

      <el-descriptions
        :column="1"
        border
        size="small"
        class="stats"
      >
        <el-descriptions-item label="PERCLOS">
          <div class="perclos-bar">
            <div
              class="perclos-fill"
              :style="{ width: perclosPct + '%', background: perclosColor }"
            ></div>
            <span class="perclos-text">{{ perclosPct }}%</span>
          </div>
        </el-descriptions-item>
        <el-descriptions-item label="眼睛状态">
          <el-tag :type="stats.eye_state === 'closed' ? 'danger' : 'success'">
            {{ eyeLabel }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="嘴巴状态">
          <el-tag :type="stats.mouth_state === 'open' ? 'warning' : 'info'">
            {{ mouthLabel }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="累计哈欠">
          {{ stats.yawn_count }} 次
        </el-descriptions-item>
        <el-descriptions-item label="单帧延迟">
          {{ stats.latency_ms }} ms
        </el-descriptions-item>
        <el-descriptions-item label="已处理帧">
          {{ stats.frame_index }}
        </el-descriptions-item>
        <el-descriptions-item label="累计告警">
          {{ alertCount }} 次
        </el-descriptions-item>
      </el-descriptions>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'

const WS_URL = 'ws://127.0.0.1:8000/ws/fatigue'
const SEND_INTERVAL_MS = 200

// ============ 摄像头 ============
const videoRef = ref<HTMLVideoElement | null>(null)
const overlayRef = ref<HTMLCanvasElement | null>(null)
const wrapRef = ref<HTMLDivElement | null>(null)
const stream = ref<MediaStream | null>(null)
const cameraOn = ref(false)

// ============ WS + 状态 ============
const ws = ref<WebSocket | null>(null)
let sendTimer: number | null = null
const alertCount = ref(0)
const yawnFlashUntil = ref(0)  // 哈欠提示持续到时间戳

interface Box { type: string; x1: number; y1: number; x2: number; y2: number; confidence: number }

const stats = reactive<{
  eye_state: string
  mouth_state: string
  ear: number
  mar: number
  perclos: number
  yawn_count: number
  latency_ms: number
  frame_index: number
  is_fatigued: boolean
  boxes: Box[]
}>({
  eye_state: 'unknown',
  mouth_state: 'unknown',
  ear: 0,
  mar: 0,
  perclos: 0,
  yawn_count: 0,
  latency_ms: 0,
  frame_index: 0,
  is_fatigued: false,
  boxes: [],
})

// ============ Badge ============
const badgeClass = computed(() => {
  if (stats.is_fatigued) return 'badge-danger'
  if (Date.now() < yawnFlashUntil.value) return 'badge-warning'
  return 'badge-success'
})
const badgeIcon = computed(() => {
  if (stats.is_fatigued) return '🚨'
  if (Date.now() < yawnFlashUntil.value) return '🥱'
  return '🙂'
})
const badgeText = computed(() => {
  if (stats.is_fatigued) return '疲劳预警！请立即靠边休息'
  if (Date.now() < yawnFlashUntil.value) return '检测到哈欠'
  return '正常驾驶中'
})

const eyeLabel = computed(() => (
  { open: '睁开', closed: '闭合', unknown: '未识别' }[stats.eye_state] || '--'
))
const mouthLabel = computed(() => (
  { open: '张开', closed: '闭合', unknown: '未识别' }[stats.mouth_state] || '--'
))
const perclosPct = computed(() => Math.round(stats.perclos * 100))
const perclosColor = computed(() => {
  const p = stats.perclos
  if (p < 0.2) return '#67C23A'
  if (p < 0.3) return '#E6A23C'
  return '#F56C6C'
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
      await videoRef.value.play().catch(() => {})
    }
    cameraOn.value = true

    // 等 metadata 就绪再连 WS
    videoRef.value?.addEventListener('loadedmetadata', () => {
      syncCanvasSize()
      connectWS()
      startSending()
    }, { once: true })
  } catch (e: any) {
    ElMessage.error(`摄像头开启失败：${e?.message || e}`)
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
      if (msg.alert_created) alertCount.value++
      if (msg.has_yawn_alert) yawnFlashUntil.value = Date.now() + 1500
      drawOverlay(msg.boxes || [])
    } catch { /* ignore */ }
  }

  ws.value.onerror = () => {
    ElMessage.error('WebSocket 错误')
  }
  ws.value.onclose = () => {
    // 服务端断开就停止发送
    stopSending()
  }
}

// ============ 定时抓帧发送 ============
function startSending() {
  if (sendTimer !== null) return
  sendTimer = window.setInterval(sendOneFrame, SEND_INTERVAL_MS)
}
function stopSending() {
  if (sendTimer !== null) {
    clearInterval(sendTimer)
    sendTimer = null
  }
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
  ctx.drawImage(v, 0, 0)   // 不镜像，后端要真实方向

  c.toBlob(
    (blob) => {
      if (blob && ws.value?.readyState === WebSocket.OPEN) {
        ws.value.send(blob)
      }
    },
    'image/jpeg',
    0.7,
  )
}

// ============ Canvas 叠加层：画检测框 ============
const COLOR_MAP: Record<string, string> = {
  face:         '#4ade80',   // 绿
  open_eye:     '#409EFF',   // 蓝
  closed_eye:   '#F56C6C',   // 红
  open_mouth:   '#E6A23C',   // 橙
  closed_mouth: '#909399',   // 灰
}
const LABEL_MAP: Record<string, string> = {
  face:         '面部',
  open_eye:     '睁眼',
  closed_eye:   '闭眼',
  open_mouth:   '张嘴',
  closed_mouth: '闭嘴',
}

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

  // 修复镜像文字反转：坐标系变换，负负得正
  ctx.save()
  ctx.setTransform(-1, 0, 0, 1, canvas.width, 0)

  ctx.lineWidth = 2
  ctx.font = '14px system-ui, -apple-system, sans-serif'

  for (const b of boxes) {
    const color = COLOR_MAP[b.type] || '#fff'
    ctx.strokeStyle = color
    ctx.strokeRect(b.x1, b.y1, b.x2 - b.x1, b.y2 - b.y1)

    // 标签背景 + 文字
    const label = `${LABEL_MAP[b.type] || b.type} ${(b.confidence * 100).toFixed(0)}%`
    const textW = ctx.measureText(label).width
    const tagH = 18
    ctx.fillStyle = color
    ctx.fillRect(b.x1, b.y1 - tagH, textW + 8, tagH)
    ctx.fillStyle = '#000'
    ctx.fillText(label, b.x1 + 4, b.y1 - 4)
  }

  ctx.restore()
}

// ============ 清理 ============
onBeforeUnmount(() => {
  stop()
})
</script>

<style scoped>
.fatigue-tab {
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

/* ============ 视频 + 叠加层 ============ */
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
.video.mirrored, .overlay.mirrored {
  transform: scaleX(-1);
}
.mask {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(10, 17, 40, 0.9);
  color: var(--ck-text-secondary);
  gap: 8px;
}
.mask-icon { font-size: 56px; }
.controls {
  margin-top: 12px;
  display: flex;
  gap: 12px;
  justify-content: center;
}

/* ============ 状态面板 ============ */
.panel-right {
  gap: 12px;
}
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

.stats {
  background: var(--ck-bg-panel);
  border-radius: 12px;
}
.stats :deep(.el-descriptions__label),
.stats :deep(.el-descriptions__content) {
  background: var(--ck-bg-panel);
  color: var(--ck-text-primary);
  border-color: var(--ck-border);
}

.perclos-bar {
  position: relative;
  height: 20px;
  background: var(--ck-bg-elevated);
  border-radius: 10px;
  overflow: hidden;
}
.perclos-fill {
  height: 100%;
  transition: width 0.3s, background 0.3s;
}
.perclos-text {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-family: monospace;
  font-size: 12px;
  text-shadow: 0 0 4px rgba(0, 0, 0, 0.6);
}
</style>