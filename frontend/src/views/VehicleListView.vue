<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { vehicleApi, type Vehicle, type VehicleCreate } from '@/api/vehicles'

// ========== 列表数据 ==========
const loading = ref(false)
const vehicleList = ref<Vehicle[]>([])
const total = ref(0)
const query = reactive<{
  page: number
  size: number
  keyword?: string
  status?: number
}>({
  page: 1, size: 10, keyword: '', status: undefined,
})

// ========== 弹窗相关 ==========
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const form = reactive<VehicleCreate>({
  plate_number: '',
  brand: '',
  model: '',
  color: '',
  owner: '',
  owner_phone: '',
  status: 1,
})

const rules: FormRules = {
  plate_number: [
    { required: true, message: '请输入车牌号', trigger: 'blur' },
    { min: 7, max: 20, message: '车牌号7-20字符', trigger: 'blur' },
  ],
  brand: [
    { required: true, message: '请输入品牌', trigger: 'blur' },
  ],
  model: [
    { required: true, message: '请输入型号', trigger: 'blur' },
  ],
}

const statusOptions = [
  { label: '启用', value: 1 },
  { label: '停用', value: 0 },
]

// ========== 方法 ==========
async function fetchList() {
  loading.value = true
  try {
    const params = { ...query }
    if (!params.keyword) delete params.keyword
    if (params.status === undefined) delete params.status
    const res = await vehicleApi.getList(params)
    vehicleList.value = res.data
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  query.page = 1
  fetchList()
}

function handleReset() {
  query.keyword = ''
  query.status = undefined
  query.page = 1
  fetchList()
}

function openCreate() {
  isEdit.value = false
  editId.value = null
  Object.assign(form, {
    plate_number: '',
    brand: '',
    model: '',
    color: '',
    owner: '',
    owner_phone: '',
    status: 1,
  })
  dialogVisible.value = true
}

async function openEdit(row: Vehicle) {
  isEdit.value = true
  editId.value = row.id
  Object.assign(form, {
    plate_number: row.plate_number,
    brand: row.brand,
    model: row.model,
    color: row.color || '',
    owner: row.owner || '',
    owner_phone: row.owner_phone || '',
    status: row.status,
  })
  dialogVisible.value = true
}

async function submitForm() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    try {
      if (isEdit.value && editId.value) {
        await vehicleApi.update(editId.value, form)
        ElMessage.success('更新成功')
      } else {
        await vehicleApi.create(form)
        ElMessage.success('创建成功')
      }
      dialogVisible.value = false
      fetchList()
    } catch (e) { /* 拦截器已提示 */ }
  })
}

async function handleDelete(row: Vehicle) {
  await ElMessageBox.confirm(`确定删除车辆"${row.plate_number}"？`, '提示', { type: 'warning' })
  await vehicleApi.remove(row.id)
  ElMessage.success('删除成功')
  fetchList()
}

function handleSizeChange(size: number) {
  query.size = size
  query.page = 1
  fetchList()
}

function handlePageChange(page: number) {
  query.page = page
  fetchList()
}

onMounted(fetchList)
</script>

<template>
  <!-- 搜索栏 -->
  <el-form :inline="true" :model="query" class="search-bar">
    <el-form-item label="关键字">
      <el-input v-model="query.keyword" placeholder="车牌号/品牌/车主" clearable style="width:220px" @keyup.enter="handleSearch" />
    </el-form-item>
    <el-form-item label="状态">
      <el-select v-model="query.status" placeholder="全部" clearable style="width:100px">
        <el-option label="启用" :value="1" />
        <el-option label="停用" :value="0" />
      </el-select>
    </el-form-item>
    <el-form-item>
      <el-button type="primary" @click="handleSearch">查询</el-button>
      <el-button @click="handleReset">重置</el-button>
    </el-form-item>
  </el-form>

  <!-- 操作栏 -->
  <div class="toolbar">
    <el-button type="primary" @click="openCreate">+ 新增车辆</el-button>
  </div>

  <!-- 表格 -->
  <el-table :data="vehicleList" v-loading="loading" border stripe>
    <el-table-column prop="id" label="ID" width="70" />
    <el-table-column prop="plate_number" label="车牌号" width="130" />
    <el-table-column prop="brand" label="品牌" width="120" />
    <el-table-column prop="model" label="型号" width="140" />
    <el-table-column prop="color" label="颜色" width="90">
      <template #default="{ row }">{{ row.color || '-' }}</template>
    </el-table-column>
    <el-table-column prop="owner" label="车主" width="100">
      <template #default="{ row }">{{ row.owner || '-' }}</template>
    </el-table-column>
    <el-table-column prop="owner_phone" label="电话" width="130">
      <template #default="{ row }">{{ row.owner_phone || '-' }}</template>
    </el-table-column>
    <el-table-column prop="status" label="状态" width="80">
      <template #default="{ row }">
        <el-tag :type="row.status === 1 ? 'success' : 'info'">{{ row.status === 1 ? '启用' : '停用' }}</el-tag>
      </template>
    </el-table-column>
    <el-table-column label="操作" width="180" fixed="right">
      <template #default="{ row }">
        <el-button size="small" @click="openEdit(row)">编辑</el-button>
        <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
      </template>
    </el-table-column>
  </el-table>

  <!-- 分页 -->
  <div class="pagination">
    <el-pagination
      v-model:current-page="query.page"
      v-model:page-size="query.size"
      :total="total"
      :page-sizes="[10, 20, 50]"
      layout="total, sizes, prev, pager, next, jumper"
      @size-change="handleSizeChange"
      @current-change="handlePageChange"
    />
  </div>

  <!-- 新增/编辑弹窗 -->
  <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑车辆' : '新增车辆'" width="500px" @close="formRef?.resetFields()">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
      <el-form-item label="车牌号" prop="plate_number">
        <el-input v-model="form.plate_number" :disabled="isEdit" placeholder="请输入车牌号" />
      </el-form-item>
      <el-form-item label="品牌" prop="brand">
        <el-input v-model="form.brand" placeholder="如：比亚迪" />
      </el-form-item>
      <el-form-item label="型号" prop="model">
        <el-input v-model="form.model" placeholder="如：汉EV" />
      </el-form-item>
      <el-form-item label="颜色">
        <el-input v-model="form.color" placeholder="如：白色" />
      </el-form-item>
      <el-form-item label="车主">
        <el-input v-model="form.owner" placeholder="请输入车主姓名" />
      </el-form-item>
      <el-form-item label="电话">
        <el-input v-model="form.owner_phone" placeholder="请输入联系电话" />
      </el-form-item>
      <el-form-item label="状态">
        <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="启用" inactive-text="停用" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="submitForm">确定</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.search-bar { margin-bottom: 16px; }
.toolbar { margin-bottom: 16px; }
.pagination { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>