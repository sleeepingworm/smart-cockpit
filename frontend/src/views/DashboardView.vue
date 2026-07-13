<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { userApi } from '@/api/user'
import { vehicleApi } from '@/api/vehicles'
import { faceApi } from '@/api/faces'
import { alertList, type Alert } from '@/api/alerts'
import { ALERT_LEVEL_OPTIONS, ALERT_STATUS_OPTIONS } from '@/utils/constants'
import { formatDateTime, optionLabel, optionTagType } from '@/utils/format'

const router = useRouter()
const userStore = useUserStore()

const stats = ref({ users: 0, vehicles: 0, faces: 0, pendingAlerts: 0 })
const recentAlerts = ref<Alert[]>([])
const loading = ref(false)

async function fetchDashboard() {
  loading.value = true
  try {
    const [u, v, f, pa, ra] = await Promise.all([
      userApi.getList({ page: 1, size: 1 }),
      vehicleApi.getList({ page: 1, size: 1 }),
      faceApi.getList({ page: 1, size: 1 }),
      alertList({ page: 1, size: 1, status: 'pending' }),
      alertList({ page: 1, size: 5 }),
    ])
    stats.value.users = u.total
    stats.value.vehicles = v.total
    stats.value.faces = f.total
    stats.value.pendingAlerts = pa.total
    recentAlerts.value = ra.data
  } finally {
    loading.value = false
  }
}

onMounted(fetchDashboard)
</script>

<template>
  <div v-loading="loading">
    <!-- 4个统计卡 -->
    <el-row :gutter="16">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat">
            <div class="stat__label">用户总数</div>
            <div class="stat__value">{{ stats.users }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat">
            <div class="stat__label">车辆总数</div>
            <div class="stat__value">{{ stats.vehicles }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat">
            <div class="stat__label">人脸总数</div>
            <div class="stat__value">{{ stats.faces }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat">
            <div class="stat__label">待处理告警</div>
            <div class="stat__value stat__value--danger">{{ stats.pendingAlerts }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 下方：最近告警 + 系统概览 -->
    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="16">
        <el-card shadow="never">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span>最近告警</span>
              <router-link to="/alerts" style="font-size:13px">查看全部 →</router-link>
            </div>
          </template>
          <el-table :data="recentAlerts" size="small">
            <el-table-column prop="alert_type" label="类型" width="120" />
            <el-table-column label="级别" width="80">
              <template #default="{ row }">
                <el-tag :type="optionTagType(ALERT_LEVEL_OPTIONS, row.level) as any">
                  {{ optionLabel(ALERT_LEVEL_OPTIONS, row.level) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="optionTagType(ALERT_STATUS_OPTIONS, row.status) as any">
                  {{ optionLabel(ALERT_STATUS_OPTIONS, row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" show-overflow-tooltip />
            <el-table-column label="时间" width="170">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never" header="系统概览">
          <el-descriptions :column="1" size="small">
            <el-descriptions-item label="当前管理员">
              {{ userStore.user?.full_name || userStore.user?.username }}
            </el-descriptions-item>
            <el-descriptions-item label="邮箱">{{ userStore.user?.email }}</el-descriptions-item>
            <el-descriptions-item label="API 地址">/api</el-descriptions-item>
            <el-descriptions-item label="版本">v1.0.0</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.stat { padding: 8px 4px; }
.stat__label { color: #909399; font-size: 13px; }
.stat__value { font-size: 28px; font-weight: 600; color: #303133; margin-top: 8px; }
.stat__value--danger { color: #f56c6c; }
</style>