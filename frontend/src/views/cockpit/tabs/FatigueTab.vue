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

      <!-- 新增：人脸信息卡片 -->
      <div class="face-info-card">
        <div class="card-title" style="display: flex; align-items: center; justify-content: space-between;">
          <span>👤 驾驶员信息</span>
          <el-button 
            size="small" 
            type="primary" 
            @click="updateFaceInfo"
            :loading="updatingFaceInfo"
            :disabled="!cameraOn"
          >
            立即识别
          </el-button>
        </div>
        <el-descriptions :column="1" border size="small" class="face-stats">
          <el-descriptions-item label="姓名">
            <el-tag type="primary">{{ faceInfo?.name || '未识别' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="年龄">
            {{ faceInfo?.age || '--' }} 岁
          </el-descriptions-item>
          <el-descriptions-item label="性别">
            {{ faceInfo?.gender || '--' }}
          </el-descriptions-item>
          <el-descriptions-item label="识别置信度">
            <div class="confidence-bar" v-if="faceInfo?.confidence !== undefined && faceInfo?.confidence !== null">
              <div
                class="confidence-fill"
                :style="{ width: Math.max(0, Math.min(100, faceInfo!.confidence * 100)) + '%' }"
              ></div>
              <span class="confidence-text">{{ Math.round(Math.max(0, Math.min(100, faceInfo!.confidence * 100))) }}%</span>
            </div>
            <span v-else>--%</span>
          </el-descriptions-item>
          <el-descriptions-item label="活体检测">
            <el-tag :type="faceInfo?.is_live ? 'success' : 'danger'">
              {{ faceInfo?.is_live ? '真实人脸' : '可能是照片' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

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

// 新增：人脸信息
const faceInfo = ref<{
  name?: string
  age?: number
  gender?: string
  confidence?: number
  is_live?: boolean
} | null>(null)
// 新增：人脸信息更新loading状态
const updatingFaceInfo = ref(false)

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

// 新增：获取人脸信息
async function updateFaceInfo(showError: boolean = true) {
  if (!videoRef.value) return
  console.log('🔍 开始更新人脸信息...')
  updatingFaceInfo.value = true
  try {
    // 截取当前帧
    const v = videoRef.value
    const c = document.createElement('canvas')
    c.width = v.videoWidth
    c.height = v.videoHeight
    const ctx = c.getContext('2d')
    if (!ctx) {
      console.error('❌ 获取canvas上下文失败')
      return
    }
    ctx.drawImage(v, 0, 0)
    console.log('✅ 截图成功，准备上传...')

    // 转换为Blob上传
    const blob = await new Promise<Blob | null>((resolve) => {
      c.toBlob(resolve, 'image/jpeg', 0.7)
    })

    if (!blob) {
      console.error('❌ 转换Blob失败')
      return
    }
    console.log(`✅ Blob大小：${Math.round(blob.size / 1024)}KB`)

    const formData = new FormData()
    formData.append('file', blob, 'frame.jpg')

    // 串行调用：两个接口共用同一个 InsightFace 分析器，避免并发推理互相影响
    // /detect 已统一转换年龄、性别、置信度等字段，直接作为属性数据源
    console.log('🚀 开始调用人脸检测接口...')
    let attrRes: { status: 'fulfilled'; value: any } | { status: 'rejected'; reason: unknown }
    try {
      const response = await axios.post('/api/face/detect', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      attrRes = { status: 'fulfilled', value: response }
    } catch (reason) {
      attrRes = { status: 'rejected', reason }
    }

    console.log('🚀 开始调用人脸搜索接口...')
    let searchRes: { status: 'fulfilled'; value: any } | { status: 'rejected'; reason: unknown }
    try {
      const response = await axios.post('/api/face/verify/search', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      searchRes = { status: 'fulfilled', value: response }
    } catch (reason) {
      searchRes = { status: 'rejected', reason }
    }

    console.log('📩 接口返回结果：', { attrRes, searchRes })

    // 处理返回结果
    const info: any = {}
    let attrNoFace = false   // 属性接口正常返回但没检测到人脸

    // ---- 属性接口：补充年龄、性别和检测置信度 ----
    if (attrRes.status === 'fulfilled') {
      const attrData = attrRes.value.data?.data
      const attr = Array.isArray(attrData) ? attrData[0] : attrData
      console.log('✅ 属性接口返回：', attrRes.value.data)
      if (attr) {
        const age = Number(attr.age)
        const confidence = Number(attr.det_score)
        if (Number.isFinite(age) && age > 0) info.age = age
        if (typeof attr.gender === 'string' && attr.gender.trim()) info.gender = attr.gender
        if (Number.isFinite(confidence) && confidence > 0) info.confidence = confidence
        console.log('👤 检测到人脸属性：', {
          age: info.age,
          gender: info.gender,
          confidence: info.confidence
        })
      } else {
        console.log('ℹ️ 属性接口未检测到人脸')
        attrNoFace = true
      }
    } else {
      console.error('❌ 属性接口调用失败：', attrRes.reason)
    }

    // ---- 搜索接口：决定姓名，并为置信度提供兜底 ----
    let matchedName = ''
    if (searchRes.status === 'fulfilled') {
      console.log('✅ 搜索接口返回：', searchRes.value.data)
      const match = searchRes.value.data?.data
      if (match) {
        info.name = match.name || '未识别'
        matchedName = info.name
        if (info.confidence === undefined) {
          const similarity = Number(match.similarity)
          info.confidence = Number.isFinite(similarity) ? similarity : 0
        }
        console.log('🔍 匹配到用户：', info.name)
      } else {
        console.log('ℹ️ 搜索接口未匹配到人脸')
        info.name = '未识别'
      }
    } else {
      console.error('❌ 搜索接口调用失败：', searchRes.reason)
    }

    // 简易活体判断（基于检测置信度，真实场景可调用专门的活体接口）
    info.is_live = (info.confidence || 0) > 0.8

    faceInfo.value = Object.keys(info).length > 0 ? info : null
    console.log('✅ 最终人脸信息：', faceInfo.value)

    // ---- 统一提示：以搜索结果为主结论 ----
    if (showError) {
      if (matchedName) {
        ElMessage.success(`识别成功：${matchedName}`)
      } else if (attrNoFace && !info.name) {
        ElMessage.info('未检测到人脸，请正对摄像头')
      } else if (searchRes.status !== 'fulfilled') {
        ElMessage.error('人脸搜索失败')
      }
    }

  } catch (e) {
    console.error('💥 人脸信息获取失败：', e)
    if (showError) {
      ElMessage.error('识别失败，请重试')
    }
  } finally {
    updatingFaceInfo.value = false
  }
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
    
    // 修复：镜像转换x坐标
    // 原坐标是左->右，翻转后变成右->左，所以x1和x2互换，再用宽度减去
    const x1 = canvas.width - b.x2
    const x2 = canvas.width - b.x1
    const y1 = b.y1
    const y2 = b.y2
    
    // 用转换后的坐标画框
    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1)

    // 标签背景 + 文字（也要用转换后的x坐标）
    const label = `${LABEL_MAP[b.type] || b.type} ${(b.confidence * 100).toFixed(0)}%`
    const textW = ctx.measureText(label).width
    const tagH = 18
    ctx.fillStyle = color
    ctx.fillRect(x1, y1 - tagH, textW + 8, tagH)
    ctx.fillStyle = '#000'
    ctx.fillText(label, x1 + 4, y1 - 4)
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

/* 人脸信息卡片样式 */
.face-info-card {
  background: var(--ck-bg-panel);
  border-radius: 12px;
  border: 1px solid var(--ck-border);
  padding: 12px;
}
.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--ck-text-primary);
  margin-bottom: 12px;
  text-align: center;
}
.face-stats {
  background: transparent;
}
.face-stats :deep(.el-descriptions__label),
.face-stats :deep(.el-descriptions__content) {
  background: var(--ck-bg-panel);
  color: var(--ck-text-primary);
  border-color: var(--ck-border);
}
.confidence-bar {
  position: relative;
  height: 20px;
  background: var(--ck-bg-elevated);
  border-radius: 10px;
  overflow: hidden;
}
.confidence-fill {
  height: 100%;
  background: #67C23A;
  transition: width 0.3s;
}
.confidence-text {
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