import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { TaskInfo } from '@/api/types'
import api from '@/api'

export const useTaskStore = defineStore('task', () => {
  const tasks = ref<TaskInfo[]>([])
  const currentTask = ref<TaskInfo | null>(null)
  const loading = ref(false)

  // 获取所有任务
  const fetchTasks = async () => {
    loading.value = true
    try {
      const response = await api.getAllTasks()
      if (response?.success) {
        // 确保 data 是数组
        if (Array.isArray(response.data)) {
          tasks.value = response.data
        } else if (response.data) {
          // 如果 data 不是数组，尝试包装
          tasks.value = [response.data]
        } else {
          tasks.value = []
        }
      } else {
        // 如果 success 为 false，清空列表
        tasks.value = []
        console.warn('获取任务列表失败:', response?.error || response?.message)
      }
    } catch (error: any) {
      console.error('获取任务列表失败', error)
      tasks.value = []
      // 抛出错误以便上层处理
      throw error
    } finally {
      loading.value = false
    }
  }

  // 获取单个任务
  const fetchTask = async (taskId: string) => {
    loading.value = true
    try {
      const response = await api.getTask(taskId)
      if (response.success && response.data) {
        currentTask.value = response.data
        return response.data
      }
    } catch (error) {
      console.error('获取任务详情失败', error)
    } finally {
      loading.value = false
    }
  }

  // 删除任务
  const deleteTask = async (taskId: string) => {
    try {
      const response = await api.deleteTask(taskId)
      if (response.success) {
        await fetchTasks()
        return true
      }
      return false
    } catch (error) {
      console.error('删除任务失败', error)
      return false
    }
  }

  // 自动刷新任务列表
  const startAutoRefresh = (interval = 3000) => {
    const timer = setInterval(() => {
      fetchTasks()
    }, interval)
    return timer
  }

  return {
    tasks,
    currentTask,
    loading,
    fetchTasks,
    fetchTask,
    deleteTask,
    startAutoRefresh
  }
})

