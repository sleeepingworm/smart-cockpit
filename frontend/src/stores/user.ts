import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User } from '@/api/auth'

const TOKEN_KEY = 'cockpit_admin_token'
const USER_KEY = 'cockpit_admin_user'

export const useUserStore = defineStore('user', () => {
  // state：响应式数据
  // token初始化：从localStorage读取（刷新页面保持登录）
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))

  // user初始化：从localStorage读取JSON并解析
  const savedUser = localStorage.getItem(USER_KEY)
  const user = ref<User | null>(savedUser ? JSON.parse(savedUser) : null)

  // getter：计算属性
  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  // action：操作state的方法
  function setLogin(newToken: string, newUser: User) {
    token.value = newToken
    user.value = newUser
    localStorage.setItem(TOKEN_KEY, newToken)
    localStorage.setItem(USER_KEY, JSON.stringify(newUser))
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  return { token, user, isLoggedIn, isAdmin, setLogin, logout }
})