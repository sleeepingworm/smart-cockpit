import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { useUserStore } from '@/stores/user'
const request = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 10000,
})

// 请求拦截器：自动加Authorization头
request.interceptors.request.use((config) => {
  const userStore = useUserStore()
  if (userStore.token) {
    config.headers.Authorization = `Bearer ${userStore.token}`
  }
  return config
})

// 响应拦截器：统一处理错误
request.interceptors.response.use(
  (res) => {
    const body = res.data
    if (body.code !== 200) {
      ElMessage.error(body.message || '请求失败')
      return Promise.reject(new Error(body.message))
    }
    return body
  },
  (err) => {
    // HTTP状态码错误（网络错误/401/403/404/500等）
    if (err.response?.status === 401) {
      // token失效/未登录：清除登录态，跳登录页
      const userStore = useUserStore()
      userStore.logout()
      ElMessage.error('登录已过期，请重新登录')
      router.push('/login')
    } else if (err.response?.status === 403) {
      ElMessage.error('没有权限执行此操作')
    } else if (err.response?.status >= 500) {
      ElMessage.error('服务器错误，请稍后重试')
    } else if (!err.response) {
      ElMessage.error('网络错误，请检查后端是否启动')
    } else {
      ElMessage.error(err.response.data?.detail || '请求失败')
    }
    return Promise.reject(err)
  }
)

export default request