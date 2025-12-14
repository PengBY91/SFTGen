import request from './request'
import type {
  TaskConfig,
  TaskInfo,
  TaskResponse,
  TaskStats,
  DataItem,
  ReviewRequest,
  BatchReviewRequest,
  AutoReviewRequest,
  ReviewStats
} from './types'

export const api = {
  // 健康检查
  healthCheck() {
    return request.get('/health')
  },

  // 测试 API 连接
  testConnection(data: { base_url: string; api_key: string; model_name: string }) {
    return request.post<TaskResponse>('/test-connection', data)
  },

  // 上传文件
  uploadFile(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    return request.post<TaskResponse>('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },

  // 获取所有任务
  getAllTasks() {
    return request.get<TaskResponse<TaskInfo[]>>('/tasks')
  },

  // 获取单个任务
  getTask(taskId: string) {
    return request.get<TaskResponse<TaskInfo>>(`/tasks/${taskId}`)
  },

  // 创建任务
  createTask(task_name: string, filenames: string[], filepaths: string[], task_description?: string, task_type: string = 'sft') {
    return request.post<TaskResponse>('/tasks', {
      task_name,
      filenames,
      filepaths,
      task_description,
      task_type
    })
  },

  // 启动任务
  startTask(taskId: string, config: TaskConfig) {
    return request.post<TaskResponse>(`/tasks/${taskId}/start`, config)
  },

  // 恢复任务
  resumeTask(taskId: string, config: TaskConfig) {
    return request.post<TaskResponse>(`/tasks/${taskId}/resume`, config)
  },

  // 添加文件到任务
  addFilesToTask(taskId: string, filepaths: string[]) {
    return request.post<TaskResponse>(`/tasks/${taskId}/files`, { filepaths })
  },

  // 从任务中删除文件
  removeFileFromTask(taskId: string, fileIndex: number) {
    return request.delete<TaskResponse>(`/tasks/${taskId}/files/${fileIndex}`)
  },

  // 删除任务
  deleteTask(taskId: string) {
    return request.delete<TaskResponse>(`/tasks/${taskId}`)
  },

  // 获取任务原始文件内容
  getTaskSource(taskId: string, fileIndex: number = 0) {
    return request.get<TaskResponse>(`/tasks/${taskId}/source`, {
      params: { file_index: fileIndex }
    })
  },

  // 下载任务输出
  downloadTask(taskId: string, format: 'json' | 'csv' = 'json', optionalFields: string[] = []) {
    return request.get(`/tasks/${taskId}/download`, {
      params: {
        format,
        optional_fields: optionalFields.join(',')
      },
      responseType: 'blob'
    })
  },

  // 获取任务统计
  getTaskStats() {
    return request.get<TaskResponse<TaskStats>>('/tasks/stats/summary')
  },

  // 保存配置
  saveConfig(config: TaskConfig) {
    return request.post<TaskResponse>('/config/save', config)
  },

  // 加载配置
  loadConfig() {
    return request.get<TaskResponse<TaskConfig>>('/config/load')
  },

  // ==================== 审核相关 ====================

  // 获取任务的审核数据
  getReviewData(taskId: string) {
    return request.get<TaskResponse<DataItem[]>>(`/reviews/${taskId}/data`)
  },

  // 获取审核统计
  getReviewStats(taskId: string) {
    return request.get<TaskResponse<ReviewStats>>(`/reviews/${taskId}/stats`)
  },

  // 审核单个数据项
  reviewItem(data: ReviewRequest) {
    return request.post<TaskResponse>('/reviews/review', data)
  },

  // 批量审核
  batchReview(data: BatchReviewRequest) {
    return request.post<TaskResponse>('/reviews/batch-review', data)
  },

  // 自动审核
  autoReview(data: AutoReviewRequest) {
    return request.post<TaskResponse>('/reviews/auto-review', data)
  },

  // 导出审核后的数据（后端总是生成 JSON，不需要传递格式）
  exportReviewedData(taskId: string, statusFilter?: string) {
    return request.get<TaskResponse>(`/reviews/${taskId}/export`, {
      params: {
        status_filter: statusFilter
      }
    })
  },

  // 下载审核后的数据
  downloadReviewedData(taskId: string, format: 'json' | 'csv' = 'json', optionalFields: string[] = []) {
    return request.get(`/reviews/${taskId}/download`, {
      params: {
        format,
        optional_fields: optionalFields.join(',')
      },
      responseType: 'blob'
    })
  },

  // ==================== 认证相关 ====================

  auth: {
    // 登录
    login(data: { username: string; password: string }) {
      return request.post<TaskResponse>('/auth/login', data)
    },

    // 注册（仅管理员）
    register(data: { username: string; password: string; email?: string; role: 'admin' | 'reviewer' }) {
      return request.post<TaskResponse>('/auth/register', data)
    },

    // 获取当前用户信息
    getMe() {
      return request.get<TaskResponse>('/auth/me')
    },

    // 修改密码
    changePassword(data: { old_password: string; new_password: string }) {
      return request.post<TaskResponse>('/auth/change-password', data)
    },

    // 获取所有用户（仅管理员）
    getUsers() {
      return request.get<TaskResponse>('/auth/users')
    },

    // 更新用户（仅管理员）
    updateUser(username: string, data: any) {
      return request.put<TaskResponse>(`/auth/users/${username}`, data)
    },

    // 删除用户（仅管理员）
    deleteUser(username: string) {
      return request.delete<TaskResponse>(`/auth/users/${username}`)
    }
  }
}

export default api

