import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'

// 创建 axios 实例
const instance: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 300000, // 增加到5分钟，用于处理大文件上传和长时间任务
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
instance.interceptors.request.use(
  (config) => {
    // 添加 Token
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
instance.interceptors.response.use(
  (response: AxiosResponse) => {
    return response.data
  },
  (error) => {
    // 处理网络错误（后端未启动或连接失败）
    if (!error.response) {
      const url = error.config?.url || ''
      // 对于认证相关的 API，不显示错误消息（避免干扰路由守卫）
      if (url.includes('/auth/me')) {
        return Promise.reject(error)
      }
      // 处理 IncompleteRead 错误（连接中断）
      if (error.message.includes('IncompleteRead') || error.message.includes('Connection broken')) {
        console.error('Connection interrupted:', url, error.message)
        ElMessage.error('连接中断，请检查网络连接或稍后重试')
        return Promise.reject(error)
      }
      // 其他网络错误，显示提示但不强制跳转
      if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
        console.warn('Request timeout:', url)
        ElMessage.error('请求超时，请稍后重试')
      } else if (error.message.includes('Network Error')) {
        console.warn('Network error - backend may not be running:', url)
        ElMessage.error('网络错误，请检查后端服务是否运行')
      }
      return Promise.reject(error)
    }
    
    const status = error.response?.status
    const url = error.config?.url || ''
    
    // 处理 401 未授权错误
    if (status === 401) {
      // 清除本地存储
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      
      // 如果不是登录页面，跳转到登录页
      if (!window.location.pathname.includes('/login')) {
        ElMessage.error('登录已过期，请重新登录')
        window.location.href = '/login'
      }
      return Promise.reject(error)
    }
    
    // 处理 403 权限不足错误
    if (status === 403) {
      ElMessage.error('权限不足')
      return Promise.reject(error)
    }
    
    // 忽略特定的 404 错误（如 /api/auth/me）
    if (status === 404 && url.includes('/auth/')) {
      return Promise.reject(error)
    }
    
    const message = error.response?.data?.detail || error.message || '请求失败'
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

export default instance

