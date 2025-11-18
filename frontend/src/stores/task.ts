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
      if (response.success && response.data) {
        tasks.value = response.data
      }
    } catch (error) {
      console.error('获取任务列表失败', error)
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

