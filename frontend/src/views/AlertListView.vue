<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { alertList, alertHandle, type Alert } from '@/api/alerts'
import { ALERT_LEVEL_OPTIONS, ALERT_STATUS_OPTIONS, ALERT_TYPE_OPTIONS } from '@/utils/constants'
import { formatDateTime, optionLabel, optionTagType } from '@/utils/format'

// ========== 列表数据 ==========
const loading = ref(false)
const list = ref<Alert[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(10)

const filters = reactive({
  alert_type: '',
  level: '' as '' | 'info' | 'warning' | 'danger',
  status: '' as '' | 'pending' | 'handled' | 'ignored',
  dateRange: [] as string[],
})

// 日期范围：前端在当前页数据上过滤（后端暂不支持跨页）
const filtered = computed(() => {
  if (!filters.dateRange || filters.dateRange.length !== 2) return list.value
  const [start, end] = filters.dateRange
  const startTs = new Date(start).getTime()
  const endTs = new Date(end).getTime() + 86400000 // 加一天到当天结束
  return list.value.filter(a => {
    const t = new Date(a.created_at).getTime()
    return t >= startTs && t <= endTs
  })
})

async function fetchList() {
  loading.value = true
  try {
    const params: any = { page: page.value, size: size.value }
    if (filters.alert_type) params.alert_type = filters.alert_type
    if (filters.level) params.level = filters.level
    if (filters.status) params.status = filters.status
    const res = await alertList(params)
    list.value = res.data
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function onSearch() { page.value = 1; fetchList() }
function onReset() {
  filters.alert_type = ''; filters.level = ''; filters.status = ''
  filters.dateRange = []; page.value = 1; fetchList()
}
function onPageChange(p: number) { page.value = p; fetchList() }
function onSizeChange(s: number) { size.value = s; page.value = 1; fetchList() }

// ========== 处理/忽略告警 ==========
async function onHandle(row: Alert, target: 'handled' | 'ignored') {
  const verb = target === 'handled' ? '标记为已处理' : '忽略'
  try {
    await ElMessageBox.confirm(`确定${verb}这条告警吗？`, '提示', { type: 'warning' })
  } catch { return }
  try {
    await alertHandle(row.id, target)
    ElMessage.success('操作成功')
    await fetchList()
  } catch { /* 拦截器已弹错 */ }
}

// ========== 详情弹窗 ==========
const detailVisible = ref(false)
const detail = ref<Alert | null>(null)
function openDetail(row: Alert) {
  detail.value = row
  detailVisible.value = true
}

onMounted(fetchList)
</script>

<template>
  <div>
    <!-- 搜索栏 -->
    <div class="filter-bar">
      <el-select v-model="filters.alert_type" placeholder="类型" clearable style="width:140px">
        <el-option v-for="o in ALERT_TYPE_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
      </el-select>
      <el-select v-model="filters.level" placeholder="级别" clearable style="width:120px">
        <el-option v-for="o in ALERT_LEVEL_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
      </el-select>
      <el-select v-model="filters.status" placeholder="状态" clearable style="width:120px">
        <el-option v-for="o in ALERT_STATUS_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
      </el-select>
      <el-date-picker
        v-model="filters.dateRange" type="daterange"
        range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期"
        value-format="YYYY-MM-DD" style="width:280px"
      />
      <el-button type="primary" @click="onSearch">查询</el-button>
      <el-button @click="onReset">重置</el-button>
    </div>

    <!-- 表格 -->
    <el-table v-loading="loading" :data="filtered" border stripe style="margin-top:12px">
      <el-table-column prop="id" label="ID" width="70" />
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
      <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
      <el-table-column prop="vehicle_id" label="车辆" width="120" />
      <el-table-column prop="driver_name" label="司机" width="100" />
      <el-table-column label="告警时间" width="170">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="230" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="openDetail(row)">查看</el-button>
          <template v-if="row.status === 'pending'">
            <el-button size="small" type="success" @click="onHandle(row, 'handled')">已处理</el-button>
            <el-button size="small" type="info" @click="onHandle(row, 'ignored')">忽略</el-button>
          </template>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <el-pagination
      style="margin-top:12px;display:flex;justify-content:flex-end"
      :current-page="page" :page-size="size" :total="total"
      :page-sizes="[10,20,50]"
      layout="total, sizes, prev, pager, next, jumper"
      @current-change="onPageChange" @size-change="onSizeChange"
    />

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="告警详情" width="520px">
      <el-descriptions v-if="detail" :column="1" border>
        <el-descriptions-item label="ID">{{ detail.id }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ detail.alert_type }}</el-descriptions-item>
        <el-descriptions-item label="级别">
          <el-tag :type="optionTagType(ALERT_LEVEL_OPTIONS, detail.level) as any">
            {{ optionLabel(ALERT_LEVEL_OPTIONS, detail.level) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="optionTagType(ALERT_STATUS_OPTIONS, detail.status) as any">
            {{ optionLabel(ALERT_STATUS_OPTIONS, detail.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="描述">{{ detail.description || '-' }}</el-descriptions-item>
        <el-descriptions-item label="车辆">{{ detail.vehicle_id || '-' }}</el-descriptions-item>
        <el-descriptions-item label="司机">{{ detail.driver_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="告警时间">{{ formatDateTime(detail.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="处理时间">{{ formatDateTime(detail.handled_at) }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button type="primary" @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.filter-bar { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
</style>