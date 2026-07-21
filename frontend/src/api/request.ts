import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { useDriverStore } from '@/stores/driver'
import router from '@/router'

const request = axios.create({
  baseURL: 'http://127.0.0.1:8000',
  timeout: 30000, // 30秒超时，给人脸识别足够的处理时间
})

// 请求拦截：根据当前路由前缀选择 token
request.interceptors.request.use((config) => {
  const isCockpit = window.location.pathname.startsWith('/cockpit')
  const isLoginPage = window.location.pathname === '/cockpit/login' || window.location.pathname === '/login'
  
  // 登录页面不需要携带 token
  if (!isLoginPage) {
    if (isCockpit) {
      const driver = useDriverStore()
      if (driver.token) config.headers.Authorization = `Bearer ${driver.token}`
    } else {
      const admin = useUserStore()
      if (admin.token) config.headers.Authorization = `Bearer ${admin.token}`
    }
  }
  return config
})

// 响应拦截：与之前一致，但 401 时区分跳哪个登录页
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
    const isCockpit = window.location.pathname.startsWith('/cockpit')
    const isLoginPage = window.location.pathname === '/cockpit/login' || window.location.pathname === '/login'
    
    // 登录页面不需要处理 401 跳转和提示
    if (!isLoginPage && err.response?.status === 401) {
      if (isCockpit) {
        useDriverStore().logout()
        ElMessage.error('登录已过期，请重新刷脸')
        router.push('/cockpit/login')
      } else {
        useUserStore().logout()
        ElMessage.error('登录已过期，请重新登录')
        router.push('/login')
      }
    } else if (err.response?.status === 403) {
      ElMessage.error('没有权限执行此操作')
    } else if (err.response?.status >= 500) {
      ElMessage.error('服务器错误，请稍后重试')
    } else if (!err.response) {
      ElMessage.error('网络错误，请检查后端是否启动')
    } else if (!isLoginPage) {
      ElMessage.error(err.response.data?.detail || '请求失败')
    }
    return Promise.reject(err)
  }
)

export default request