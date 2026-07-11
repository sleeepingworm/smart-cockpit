<template>
  <div style="padding:20px">
    <h2>🚗 车辆管理</h2>

    <div style="margin-bottom:16px">
      <el-button type="primary" @click="openCreate">+ 新增车辆</el-button>
    </div>

    <el-table :data="vehicleList" v-loading="loading" border stripe>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="plate_number" label="车牌号" />
      <el-table-column prop="brand" label="品牌" />
      <el-table-column prop="model" label="型号" />
      <el-table-column prop="color" label="颜色" />
      <el-table-column prop="owner" label="车主" />
      <el-table-column prop="owner_phone" label="电话" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button type="danger" size="small" @click="handleDelete(row.id, row.plate_number)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div style="margin-top:16px;text-align:right">
      <el-pagination
        :total="total"
        :page-size="pageSize"
        :current-page="page"
        @current-change="onPageChange"
        layout="prev, pager, next, total"
      />
    </div>

    <!-- 新增弹窗 -->
    <el-dialog v-model="dialogVisible" title="新增车辆" width="500px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="车牌号" required>
          <el-input v-model="form.plate_number" placeholder="请输入车牌号" />
        </el-form-item>
        <el-form-item label="品牌" required>
          <el-input v-model="form.brand" placeholder="如：比亚迪" />
        </el-form-item>
        <el-form-item label="型号" required>
          <el-input v-model="form.model" placeholder="如：汉EV" />
        </el-form-item>
        <el-form-item label="颜色">
          <el-input v-model="form.color" placeholder="如：白色" />
        </el-form-item>
        <el-form-item label="车主">
          <el-input v-model="form.owner" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="form.owner_phone" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCreate">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { vehicleApi, type Vehicle, type VehicleCreate } from '../api/vehicles'
import { ElMessage, ElMessageBox } from 'element-plus'

// 数据
const vehicleList = ref<Vehicle[]>([])
const total = ref(0)
const loading = ref(false)
const page = ref(1)
const pageSize = ref(10)

// 弹窗
const dialogVisible = ref(false)
const form = ref<VehicleCreate>({
  plate_number: '',
  brand: '',
  model: '',
  color: '',
  owner: '',
  owner_phone: '',
})

// 查询列表
async function fetchList() {
  loading.value = true
  try {
    const res = await vehicleApi.getList(page.value, pageSize.value)
    vehicleList.value = res.data
    total.value = res.total
  } finally {
    loading.value = false
  }
}

// 新增
function openCreate() {
  form.value = { plate_number: '', brand: '', model: '', color: '', owner: '', owner_phone: '' }
  dialogVisible.value = true
}

async function submitCreate() {
  if (!form.value.plate_number || !form.value.brand || !form.value.model) {
    ElMessage.warning('请填写车牌号、品牌、型号')
    return
  }
  await vehicleApi.create(form.value)
  ElMessage.success('创建成功')
  dialogVisible.value = false
  fetchList()
}

// 删除
async function handleDelete(id: number, plate: string) {
  await ElMessageBox.confirm(`确定删除车辆 ${plate}?`, '提示', { type: 'warning' })
  await vehicleApi.remove(id)
  ElMessage.success('删除成功')
  fetchList()
}

// 分页变化
function onPageChange(p: number) {
  page.value = p
  fetchList()
}

// 页面加载时查询
onMounted(() => {
  fetchList()
})
</script>