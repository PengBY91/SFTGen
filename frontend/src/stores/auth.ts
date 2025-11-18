import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'

export interface User {
  user_id: string
  username: string
  email?: string
  role: 'admin' | 'reviewer'
  is_active: boolean
  created_at?: string
  last_login?: string
}

export const useAuthStore = defineStore('auth', () => {
  // 状态
  const token = ref<string | null>(localStorage.getItem('token'))
  // 从 localStorage 恢复用户信息
  let initialUser: User | null = null
  try {
    const savedUser = localStorage.getItem('user')
    if (savedUser) {
      initialUser = JSON.parse(savedUser)
    }
  } catch (error) {
    // JSON 解析失败，清除无效的用户信息
    console.warn('Failed to parse saved user from localStorage:', error)
    localStorage.removeItem('user')
  }
  const user = ref<User | null>(initialUser)
  
  // 计算属性
  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isReviewer = computed(() => user.value?.role === 'reviewer')
  
  // 初始化用户信息
  const initUser = async () => {
    if (!token.value) {
      // 如果没有 token，清除可能存在的用户信息
      if (user.value) {
        clearAuth()
      }
      return
    }
    
    // 检查 localStorage 中是否有保存的用户信息
    const hasSavedUser = !!localStorage.getItem('user')
    
    try {
      const response = await api.auth.getMe()
      if (response.success) {
        user.value = response.data
        localStorage.setItem('user', JSON.stringify(response.data))
      } else {
        // Token 无效，清除
        clearAuth()
      }
    } catch (error) {
      // API 调用失败时，如果 localStorage 中有用户信息，保留它
      // 这样可以避免后端未启动时页面无法访问
      // 如果 localStorage 中没有用户信息，清除认证
      if (!hasSavedUser) {
        clearAuth()
      }
      // 重新抛出错误，让调用者知道初始化失败
      throw error
    }
  }
  
  // 登录
  const login = async (username: string, password: string) => {
    const response = await api.auth.login({ username, password })
    
    if (response.success) {
      token.value = response.data.access_token
      user.value = response.data.user
      localStorage.setItem('token', response.data.access_token)
      localStorage.setItem('user', JSON.stringify(response.data.user))
    } else {
      throw new Error(response.error || '登录失败')
    }
  }
  
  // 登出
  const logout = () => {
    clearAuth()
    window.location.href = '/login'
  }
  
  // 清除认证信息
  const clearAuth = () => {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }
  
  // 更新用户信息
  const updateUser = (newUser: User) => {
    user.value = newUser
    localStorage.setItem('user', JSON.stringify(newUser))
  }
  
  // 修改密码
  const changePassword = async (oldPassword: string, newPassword: string) => {
    const response = await api.auth.changePassword({
      old_password: oldPassword,
      new_password: newPassword
    })
    
    if (!response.success) {
      throw new Error(response.error || '修改密码失败')
    }
    
    return response
  }
  
  return {
    token,
    user,
    isAuthenticated,
    isAdmin,
    isReviewer,
    initUser,
    login,
    logout,
    clearAuth,
    updateUser,
    changePassword
  }
})

