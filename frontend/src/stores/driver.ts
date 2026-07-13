import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User } from '@/api/auth'

const TOKEN_KEY = 'cockpit_driver_token'   // ← 不同的 key
const USER_KEY  = 'cockpit_driver_user'

export const useDriverStore = defineStore('driver', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const savedUser = localStorage.getItem(USER_KEY)
  const user = ref<User | null>(savedUser ? JSON.parse(savedUser) : null)

  const isLoggedIn = computed(() => !!token.value)
  const isDriver   = computed(() => user.value?.role === 'driver')

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

  return { token, user, isLoggedIn, isDriver, setLogin, logout }
})