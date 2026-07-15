<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { faceApi, type Face } from '@/api/faces'
import { userApi, type User } from '@/api/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

// ========== 列表数据 ==========
const loading = ref(false)
const faceList = ref<Face[]>([])
const total = ref(0)
const query = reactive({
  page: 1,
  size: 10,
  keyword: '',
})

// ========== 弹窗 ==========
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref<number | null>(null)

const form = reactive({
  user_id: undefined as number | undefined,
  name: '',
  employee_id: '',
  image_url: '',
})
const uploadUrl = ref('')
const uploadFileName = ref('')

// ========== 驾驶员选项 ==========
const driverOptions = ref<User[]>([])

async function fetchDrivers() {
  const res = await userApi.getList({ role: 'driver', size: 100 })
  driverOptions.value = res.data
}

// ========== 查询列表 ==========
async function fetchList() {
  loading.value = true
  try {
    const params: any = { page: query.page, size: query.size }
    const res = await faceApi.getList(params)
    faceList.value = res.data
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
  query.page = 1
  fetchList()
}

// ========== 上传 ==========
function beforeUpload(file: File) {
  const isImage = ['image/jpeg', 'image/png', 'image/bmp', 'image/webp'].includes(file.type)
  const isLt5M = file.size / 1024 / 1024 < 5
  if (!isImage) { ElMessage.error('只能上传图片'); return false }
  if (!isLt5M) { ElMessage.error('图片不能超过5MB'); return false }
  return true
}

async function customUpload(options: any) {
  try {
    const res = await faceApi.upload(options.file)
    uploadUrl.value = res.data.url
    uploadFileName.value = res.data.filename
    form.image_url = res.data.url
    ElMessage.success('图片上传成功')
    options.onSuccess(res)
  } catch (e) {
    options.onError(e)
  }
}

function handlePreview() {
  if (uploadUrl.value) window.open(uploadUrl.value)
}

function handleRemove() {
  uploadUrl.value = ''
  uploadFileName.value = ''
  form.image_url = ''
}

// ========== 新增/编辑 ==========
function openCreate() {
  isEdit.value = false
  editId.value = null
  form.user_id = undefined
  form.name = ''
  form.employee_id = ''
  form.image_url = ''
  uploadUrl.value = ''
  uploadFileName.value = ''
  dialogVisible.value = true
}

async function openEdit(row: Face) {
  isEdit.value = true
  editId.value = row.id
  form.user_id = row.user_id
  form.name = row.name
  form.employee_id = row.employee_id || ''
  form.image_url = row.image_url
  uploadUrl.value = row.image_url
  dialogVisible.value = true
}

async function submitForm() {
  if (!form.user_id) { ElMessage.warning('请选择驾驶员'); return }
  if (!form.name) { ElMessage.warning('请输入姓名'); return }
  if (!form.image_url) { ElMessage.warning('请上传人脸图片'); return }

  try {
    if (isEdit.value && editId.value) {
      await faceApi.create({
        user_id: form.user_id,
        name: form.name,
        employee_id: form.employee_id || undefined,
        image_url: form.image_url,
      })
      ElMessage.success('更新成功')
    } else {
      await faceApi.create({
        user_id: form.user_id,
        name: form.name,
        employee_id: form.employee_id || undefined,
        image_url: form.image_url,
      })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchList()
  } catch { /* 拦截器已提示 */ }
}

// ========== 删除 ==========
async function handleDelete(row: Face) {
  await ElMessageBox.confirm(`确定删除"${row.name}"的人脸记录？`, '提示', { type: 'warning' })
  await faceApi.remove(row.id)
  ElMessage.success('删除成功')
  fetchList()
}

// ========== 图片完整地址 ==========
function fullUrl(url: string) {
  if (!url) return ''
  return url.startsWith('http') ? url : `http://localhost:8000${url}`
}

// ========== 分页 ==========
function handleSizeChange(size: number) {
  query.size = size
  query.page = 1
  fetchList()
}

function handlePageChange(page: number) {
  query.page = page
  fetchList()
}

onMounted(() => {
  fetchDrivers()
  fetchList()
})
</script>

<template>
  <!-- 搜索栏 -->
  <el-form :inline="true" :model="query" class="search-bar">
    <el-form-item label="关键字">
      <el-input v-model="query.keyword" placeholder="驾驶员姓名" clearable style="width:200px" @keyup.enter="handleSearch" />
    </el-form-item>
    <el-form-item>
      <el-button type="primary" @click="handleSearch">查询</el-button>
      <el-button @click="handleReset">重置</el-button>
    </el-form-item>
  </el-form>

  <!-- 操作栏 -->
  <div class="toolbar">
    <el-button type="primary" @click="openCreate">+ 录入人脸</el-button>
  </div>

  <!-- 表格 -->
  <el-table :data="faceList" v-loading="loading" border stripe>
    <el-table-column prop="id" label="ID" width="70" />
    <el-table-column label="人脸照片" width="100">
      <template #default="{ row }">
        <el-image
          :src="fullUrl(row.image_url)"
          :preview-src-list="[fullUrl(row.image_url)]"
          fit="cover"
          style="width:60px;height:60px;border-radius:4px;cursor:pointer"
        />
      </template>
    </el-table-column>
    <el-table-column prop="name" label="姓名" />
    <el-table-column prop="employee_id" label="工号">
      <template #default="{ row }">{{ row.employee_id || '-' }}</template>
    </el-table-column>
    <el-table-column prop="user_id" label="关联驾驶员ID" width="120" />
    <el-table-column prop="is_active" label="状态" width="80">
      <template #default="{ row }">
        <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '启用' : '禁用' }}</el-tag>
      </template>
    </el-table-column>
    <el-table-column label="操作" width="160" fixed="right">
      <template #default="{ row }">
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

  <!-- 新增弹窗 -->
  <el-dialog v-model="dialogVisible" title="录入人脸" width="500px">
    <el-form :model="form" label-width="100px">
      <el-form-item label="驾驶员" required>
        <el-select v-model="form.user_id" placeholder="请选择驾驶员" style="width:100%" filterable>
          <el-option
            v-for="d in driverOptions"
            :key="d.id"
            :label="`${d.full_name || d.username}（ID:${d.id}）`"
            :value="d.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="姓名" required>
        <el-input v-model="form.name" placeholder="请输入驾驶员姓名" />
      </el-form-item>
      <el-form-item label="工号">
        <el-input v-model="form.employee_id" placeholder="请输入工号（可选）" />
      </el-form-item>
      <el-form-item label="人脸照片" required>
        <el-upload
          :action="''"
          :auto-upload="true"
          :http-request="customUpload"
          :before-upload="beforeUpload"
          :on-preview="handlePreview"
          :on-remove="handleRemove"
          :limit="1"
          :file-list="uploadUrl ? [{ name: uploadFileName, url: uploadUrl }] : []"
          list-type="picture-card"
          accept="image/jpeg,image/png,image/bmp,image/webp"
        >
          <el-icon><Plus /></el-icon>
        </el-upload>
        <div style="color:#999;font-size:12px;margin-top:4px">支持 JPG/PNG/BMP/WebP，不超过 5MB</div>
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