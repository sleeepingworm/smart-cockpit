<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { userApi, type User, type UserCreate } from '@/api/user'

// ========== 列表数据 ==========
const loading = ref(false)
const userList = ref<User[]>([])
const total = ref(0)
const query = reactive<{
  page: number
  size: number
  keyword?: string
  role?: string
  is_active?: number
}>({
  page: 1, size: 10, keyword: '', role: '', is_active: undefined,
})

// ========== 弹窗相关 ==========
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const form = reactive<UserCreate & { is_active?: boolean }>({
  username: '', email: '', password: '',
  full_name: '', phone: '', role: 'driver', is_active: true,
})

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名3-20字符', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' },
  ],
}

const roleOptions = [
  { label: '管理员', value: 'admin' },
  { label: '驾驶员', value: 'driver' },
]

// ========== 方法 ==========
async function fetchList() {
  loading.value = true
  try {
    const params = { ...query }
    if (!params.keyword) delete params.keyword
    if (!params.role) delete params.role
    if (params.is_active === undefined) delete params.is_active
    const res = await userApi.getList(params)
    userList.value = res.data
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
  query.role = ''
  query.is_active = undefined
  query.page = 1
  fetchList()
}

function openCreate() {
  isEdit.value = false
  editId.value = null
  Object.assign(form, {
    username: '', email: '', password: '',
    full_name: '', phone: '', role: 'driver', is_active: true,
  })
  dialogVisible.value = true
}

async function openEdit(row: User) {
  isEdit.value = true
  editId.value = row.id
  Object.assign(form, {
    username: row.username,
    email: row.email,
    password: '',    // 编辑时不回填密码
    full_name: row.full_name || '',
    phone: row.phone || '',
    role: row.role,
    is_active: row.is_active,
  })
  dialogVisible.value = true
}

async function submitForm() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    try {
      if (isEdit.value && editId.value) {
        // 编辑时如果密码为空，不更新密码
        const data = { ...form }
        if (!data.password) delete data.password
        await userApi.update(editId.value, data)
        ElMessage.success('更新成功')
      } else {
        await userApi.create(form)
        ElMessage.success('创建成功')
      }
      dialogVisible.value = false
      fetchList()
    } catch (e) { /* 拦截器已提示 */ }
  })
}

async function handleDelete(row: User) {
  await ElMessageBox.confirm(`确定删除用户"${row.username}"？`, '提示', { type: 'warning' })
  await userApi.remove(row.id)
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
      <el-input v-model="query.keyword" placeholder="用户名/邮箱/姓名" clearable style="width:200px" @keyup.enter="handleSearch" />
    </el-form-item>
    <el-form-item label="角色">
      <el-select v-model="query.role" placeholder="全部" clearable style="width:120px">
        <el-option v-for="o in roleOptions" :key="o.value" :label="o.label" :value="o.value" />
      </el-select>
    </el-form-item>
    <el-form-item label="状态">
      <el-select v-model="query.is_active" placeholder="全部" clearable style="width:100px">
        <el-option label="启用" :value="1" />
        <el-option label="禁用" :value="0" />
      </el-select>
    </el-form-item>
    <el-form-item>
      <el-button type="primary" @click="handleSearch">查询</el-button>
      <el-button @click="handleReset">重置</el-button>
    </el-form-item>
  </el-form>

  <!-- 操作栏 -->
  <div class="toolbar">
    <el-button type="primary" @click="openCreate">+ 新增用户</el-button>
  </div>

  <!-- 表格 -->
  <el-table :data="userList" v-loading="loading" border stripe>
    <el-table-column prop="id" label="ID" width="70" />
    <el-table-column prop="username" label="用户名" />
    <el-table-column prop="email" label="邮箱" />
    <el-table-column prop="full_name" label="姓名">
      <template #default="{ row }">{{ row.full_name || '-' }}</template>
    </el-table-column>
    <el-table-column prop="phone" label="电话">
      <template #default="{ row }">{{ row.phone || '-' }}</template>
    </el-table-column>
    <el-table-column prop="role" label="角色" width="100">
      <template #default="{ row }">
        <el-tag :type="row.role === 'admin' ? 'danger' : ''">{{ row.role === 'admin' ? '管理员' : '驾驶员' }}</el-tag>
      </template>
    </el-table-column>
    <el-table-column prop="is_active" label="状态" width="80">
      <template #default="{ row }">
        <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '启用' : '禁用' }}</el-tag>
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
  <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑用户' : '新增用户'" width="500px" @close="formRef?.resetFields()">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
      <el-form-item label="用户名" prop="username">
        <el-input v-model="form.username" :disabled="isEdit" placeholder="请输入用户名" />
      </el-form-item>
      <el-form-item label="邮箱" prop="email">
        <el-input v-model="form.email" placeholder="请输入邮箱" />
      </el-form-item>
      <el-form-item label="密码" prop="password">
        <el-input v-model="form.password" type="password" :placeholder="isEdit ? '留空则不修改' : '请输入密码'" show-password />
      </el-form-item>
      <el-form-item label="姓名">
        <el-input v-model="form.full_name" placeholder="请输入真实姓名" />
      </el-form-item>
      <el-form-item label="电话">
        <el-input v-model="form.phone" placeholder="请输入手机号" />
      </el-form-item>
      <el-form-item label="角色">
        <el-radio-group v-model="form.role">
          <el-radio value="admin">管理员</el-radio>
          <el-radio value="driver">驾驶员</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="状态" v-if="isEdit">
        <el-switch v-model="form.is_active" active-text="启用" inactive-text="禁用" />
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