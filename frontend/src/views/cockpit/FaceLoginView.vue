<template>
  <div class="cockpit-root face-login">
    <!-- 左：摄像头预览 -->
    <div class="camera-panel">
      <div class="camera-frame">
        <video
          ref="videoRef"
          class="video"
          :class="{ mirrored: true }"
          autoplay
          playsinline
          muted
        />
        <div v-if="!cameraOn" class="camera-mask">
          <div class="mask-text">🎥 摄像头未开启</div>
        </div>
      </div>
    </div>

    <!-- 右：状态与操作 -->
    <div class="status-panel">
      <h1 class="title">智慧驾舱 · 驾驶员刷脸登录</h1>
      <p class="subtitle">请将面部对准摄像头</p>

      <div class="state-box" :class="stateClass">
        <div class="state-icon">{{ stateIcon }}</div>
        <div class="state-text">{{ stateText }}</div>
      </div>

      <div class="actions">
        <el-button v-if="!cameraOn" type="primary" size="large" @click="openCamera">
          开启摄像头
        </el-button>
        <el-button v-else type="primary" size="large" :loading="verifying" @click="captureAndVerify">
          人脸识别
        </el-button>
        <el-button size="large" @click="showPwdDialog = true">账号密码登录</el-button>
      </div>
    </div>

    <!-- 兜底：账号密码登录 -->
    <el-dialog v-model="showPwdDialog" title="账号密码登录" width="420px">
      <el-form :model="pwdForm" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="pwdForm.username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="pwdForm.password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPwdDialog = false">取消</el-button>
        <el-button type="primary" :loading="pwdSubmitting" @click="submitPwd">登录</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onBeforeUnmount, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '@/api/request'
import { useDriverStore } from '@/stores/driver'

const router = useRouter()
const driver = useDriverStore()

const videoRef = ref<HTMLVideoElement | null>(null)
const stream = ref<MediaStream | null>(null)
const cameraOn = ref(false)
const verifying = ref(false)

// ========== 状态显示 ==========
const state = ref<'idle' | 'camera' | 'verifying' | 'success' | 'fail'>('idle')
const stateIcon = computed(() => ({
  idle:      '📷',
  camera:    '🎥',
  verifying: '🔍',
  success:   '✅',
  fail:      '❌',
}[state.value]))
const stateText = computed(() => ({
  idle:      '待开启摄像头',
  camera:    '摄像头已就绪，请点击"人脸识别"',
  verifying: '识别中，请稍候...',
  success:   '识别成功，正在进入驾舱',
  fail:      '识别失败，请重试',
}[state.value]))
const stateClass = computed(() => `state-${state.value}`)

// ========== 摄像头 ==========
async function openCamera() {
  try {
    stream.value = await navigator.mediaDevices.getUserMedia({
      video: { width: 720, height: 540, facingMode: 'user' },
      audio: false,
    })
    if (videoRef.value) {
      videoRef.value.srcObject = stream.value
    }
    cameraOn.value = true
    state.value = 'camera'
  } catch (e: any) {
    ElMessage.error(`摄像头开启失败：${e.message}`)
    state.value = 'fail'
  }
}

function closeCamera() {
  stream.value?.getTracks().forEach(t => t.stop())
  stream.value = null
  cameraOn.value = false
}

onBeforeUnmount(() => {
  closeCamera()
})

// ========== 抓帧 + 提交 ==========
async function captureAndVerify() {
  if (!videoRef.value || !cameraOn.value) return

  const canvas = document.createElement('canvas')
  canvas.width  = videoRef.value.videoWidth
  canvas.height = videoRef.value.videoHeight
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  // ⚠️ 前端是镜像显示，但抓帧不需要镜像（后端拿真实方向）
  ctx.drawImage(videoRef.value, 0, 0)

  canvas.toBlob(async (blob) => {
    if (!blob) {
      ElMessage.error('抓帧失败，请重试')
      return
    }

    verifying.value = true
    state.value = 'verifying'
    try {
      const formData = new FormData()
      formData.append('file', blob, 'face.jpg')

      const res: any = await request.post('/auth/face-login', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })

      // 登录成功
      driver.setLogin(res.data.access_token, res.data.user)
      state.value = 'success'
      ElMessage.success(res.message)
      closeCamera()

      setTimeout(() => router.push('/cockpit/home'), 800)
    } catch (e: any) {
      state.value = 'fail'
      // 拦截器已经弹过 ElMessage 了
    } finally {
      verifying.value = false
    }
  }, 'image/jpeg', 0.85)
}

// ========== 账密兜底 ==========
const showPwdDialog = ref(false)
const pwdSubmitting = ref(false)
const pwdForm = reactive({ username: '', password: '' })

async function submitPwd() {
  if (!pwdForm.username || !pwdForm.password) {
    ElMessage.warning('请填写用户名和密码')
    return
  }
  pwdSubmitting.value = true
  try {
    const res: any = await request.post('/auth/login', pwdForm)
    if (res.data.user.role !== 'driver') {
      ElMessage.error('该账号不是驾驶员，请使用管理端登录')
      return
    }
    driver.setLogin(res.data.access_token, res.data.user)
    ElMessage.success('登录成功')
    closeCamera()
    router.push('/cockpit/home')
  } finally {
    pwdSubmitting.value = false
  }
}
</script>

<style scoped>
.face-login {
  display: flex;
  height: 100vh;
  padding: 32px;
  gap: 32px;
}

.camera-panel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
.camera-frame {
  position: relative;
  width: 720px;
  height: 540px;
  border: 2px solid var(--ck-border);
  border-radius: 16px;
  overflow: hidden;
  background: #000;
}
.video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.video.mirrored { transform: scaleX(-1); }
.camera-mask {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(10, 17, 40, 0.9);
}
.mask-text { font-size: 20px; color: var(--ck-text-secondary); }

.status-panel {
  width: 380px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 20px;
}
.title {
  font-size: 28px;
  font-weight: 700;
  background: linear-gradient(135deg, var(--ck-accent), var(--ck-accent-glow));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.subtitle { color: var(--ck-text-secondary); }

.state-box {
  padding: 24px;
  border-radius: 12px;
  background: var(--ck-bg-panel);
  border: 1px solid var(--ck-border);
  text-align: center;
  transition: all .3s;
}
.state-box.state-verifying { border-color: var(--ck-accent); }
.state-box.state-success   { border-color: var(--ck-success); }
.state-box.state-fail      { border-color: var(--ck-danger); }

.state-icon { font-size: 48px; margin-bottom: 12px; }
.state-text { color: var(--ck-text-primary); font-size: 15px; }

.actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
</style>