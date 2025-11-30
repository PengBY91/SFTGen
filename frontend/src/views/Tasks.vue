<template>
  <div class="tasks-container">
    <el-card class="table-card">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span class="header-title">任务列表</span>
            <div class="stats-inline">
              <span class="stat-inline-item">总数: <strong>{{ taskStats.total }}</strong></span>
              <span class="stat-inline-item pending">待处理: <strong>{{ taskStats.pending }}</strong></span>
              <span class="stat-inline-item processing">处理中: <strong>{{ taskStats.processing }}</strong></span>
              <span class="stat-inline-item completed">已完成: <strong>{{ taskStats.completed }}</strong></span>
              <span class="stat-inline-item failed">失败: <strong>{{ taskStats.failed }}</strong></span>
            </div>
          </div>
          <div class="header-actions">
            <el-select
              v-model="selectedStatus"
              placeholder="筛选状态"
              style="width: 140px; margin-right: 10px"
              clearable
            >
              <el-option label="全部" value="" />
              <el-option label="待处理" value="pending" />
              <el-option label="处理中" value="processing" />
              <el-option label="已完成" value="completed" />
              <el-option label="失败" value="failed" />
            </el-select>
            <el-input
              v-model="searchText"
              placeholder="搜索任务"
              style="width: 200px; margin-right: 10px"
              clearable
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button size="small" @click="refreshTasks" :loading="loading">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>

      <el-table
        :data="filteredTasks"
        v-loading="loading"
        style="width: 100%; table-layout: auto"
        @row-click="handleRowClick"
      >
        <el-table-column prop="task_name" label="任务名称" width="120" show-overflow-tooltip />
        <el-table-column label="文件数" width="80">
          <template #default="{ row }">
            {{ row.filenames?.length || 1 }}
          </template>
        </el-table-column>
        <el-table-column label="模型" width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="model-info">
              <div v-if="row.synthesizer_model" class="model-item">
                <span class="model-label">合成器:</span>
                <span class="model-name">{{ row.synthesizer_model }}</span>
              </div>
              <div v-if="row.trainee_model" class="model-item">
                <span class="model-label">训练:</span>
                <span class="model-name">{{ row.trainee_model }}</span>
              </div>
              <span v-if="!row.synthesizer_model && !row.trainee_model">-</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <span class="status-text">{{ getStatusText(row.status) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="问答对数" width="100">
          <template #default="{ row }">
            {{ row.qa_count || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="处理时间" width="100">
          <template #default="{ row }">
            {{ row.processing_time ? `${row.processing_time.toFixed(2)}s` : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="Token使用" width="180">
          <template #default="{ row }">
            <div v-if="row.token_usage" class="token-usage-cell">
              <div class="token-total">
                <strong>{{ row.token_usage.total_tokens.toLocaleString() }}</strong>
              </div>
              <div v-if="row.token_usage.total_input_tokens !== undefined" class="token-detail">
                <span class="token-input">输入: {{ row.token_usage.total_input_tokens.toLocaleString() }}</span>
                <span class="token-output">输出: {{ row.token_usage.total_output_tokens.toLocaleString() }}</span>
              </div>
            </div>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" :width="authStore.isAdmin ? '400' : '200'" fixed="right">
          <template #default="{ row }">
            <!-- 管理员操作 -->
            <template v-if="authStore.isAdmin">
              <el-button
                size="small"
                type="primary"
                :disabled="row.status !== 'pending'"
                @click.stop="handleStartTask(row)"
              >
                <el-icon><VideoPlay /></el-icon>
                启动
              </el-button>
              <el-button
                v-if="row.status === 'failed'"
                size="small"
                type="danger"
                @click.stop="handleResumeTask(row)"
              >
                <el-icon><RefreshLeft /></el-icon>
                重新开始
              </el-button>
              <el-button
                v-else-if="canResumeTask(row)"
                size="small"
                type="warning"
                @click.stop="handleResumeTask(row)"
              >
                <el-icon><RefreshRight /></el-icon>
                继续
              </el-button>
              <el-button
                size="small"
                type="success"
                :disabled="row.status !== 'completed'"
                @click.stop="handleDownload(row)"
              >
                <el-icon><Download /></el-icon>
                下载
              </el-button>
              <el-button
                size="small"
                type="primary"
                :disabled="row.status !== 'completed'"
                @click.stop="handleReview(row)"
              >
                <el-icon><Edit /></el-icon>
                审核
              </el-button>
              <el-button
                size="small"
                type="info"
                @click.stop="handleViewDetail(row)"
              >
                <el-icon><View /></el-icon>
                详情
              </el-button>
              <el-popconfirm
                title="确定要删除这个任务吗？"
                @confirm="handleDelete(row)"
              >
                <template #reference>
                  <el-button
                    size="small"
                    type="danger"
                    @click.stop
                  >
                    <el-icon><Delete /></el-icon>
                    删除
                  </el-button>
                </template>
              </el-popconfirm>
            </template>
            
            <!-- 审核员操作 -->
            <template v-else>
              <el-button
                size="small"
                type="success"
                :disabled="row.status !== 'completed'"
                @click.stop="handleDownload(row)"
              >
                <el-icon><Download /></el-icon>
                下载
              </el-button>
              <el-button
                size="small"
                type="primary"
                :disabled="row.status !== 'completed'"
                @click.stop="handleReview(row)"
              >
                <el-icon><Edit /></el-icon>
                审核
              </el-button>
              <el-button
                size="small"
                type="info"
                @click.stop="handleViewDetail(row)"
              >
                <el-icon><View /></el-icon>
                详情
              </el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 启动任务对话框 -->
    <el-dialog
      v-model="startDialogVisible"
      title="启动任务"
      width="500px"
    >
      <el-alert
        title="提示"
        type="info"
        description="任务将使用当前的配置设置启动，请确认配置信息正确。"
        :closable="false"
        style="margin-bottom: 20px"
      />
      <div v-if="selectedTask">
        <p><strong>任务名称：</strong>{{ selectedTask.task_name }}</p>
        <p><strong>文件数量：</strong>{{ selectedTask.filenames?.length || 1 }} 个</p>
        <p><strong>任务ID：</strong>{{ selectedTask.task_id }}</p>
      </div>
      <template #footer>
        <el-button @click="startDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmStartTask" :loading="startLoading">
          确认启动
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTaskStore } from '@/stores/task'
import { useConfigStore } from '@/stores/config'
import { useAuthStore } from '@/stores/auth'
import type { TaskInfo } from '@/api/types'
import api from '@/api'
import { ElMessage } from 'element-plus'
import {
  Refresh,
  Search,
  VideoPlay,
  Download,
  View,
  Delete,
  Edit,
  RefreshRight,
  RefreshLeft
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const router = useRouter()
const taskStore = useTaskStore()
const configStore = useConfigStore()
const authStore = useAuthStore()

const loading = ref(false)
const searchText = ref('')
const selectedStatus = ref<string>('')
const startDialogVisible = ref(false)
const selectedTask = ref<TaskInfo | null>(null)
const startLoading = ref(false)
const taskStats = ref({
  total: 0,
  pending: 0,
  processing: 0,
  completed: 0,
  failed: 0
})

let refreshTimer: number | null = null

// 过滤后的任务列表（按时间倒序排序，最新的在前）
const filteredTasks = computed(() => {
  let result = taskStore.tasks
  
  // 状态筛选
  if (selectedStatus.value) {
    result = result.filter((task) => task.status === selectedStatus.value)
  }
  
  // 文本搜索过滤
  if (searchText.value) {
    result = result.filter((task) =>
      (task.task_name || task.filename || '').toLowerCase().includes(searchText.value.toLowerCase())
    )
  }
  
  // 按创建时间倒序排序（最新的在前）
  return result.slice().sort((a, b) => {
    const dateA = new Date(a.created_at || 0).getTime()
    const dateB = new Date(b.created_at || 0).getTime()
    return dateB - dateA
  })
})

// 刷新任务列表
const refreshTasks = async () => {
  loading.value = true
  let fetchSuccess = false
  try {
    await taskStore.fetchTasks()
    fetchSuccess = true
    await fetchTaskStats()
  } catch (error: any) {
    fetchSuccess = false
    console.error('刷新任务列表失败:', error)
    // 检查是否是认证错误
    if (error?.response?.status === 401 || error?.message?.includes('401')) {
      ElMessage.error('登录已过期，请重新登录')
      // 等待一下再跳转，让用户看到错误消息
      setTimeout(() => {
        router.push('/login')
      }, 1500)
    } else if (error?.response?.status === 403) {
      ElMessage.error('权限不足，无法访问任务列表')
    } else if (!error?.response) {
      // 网络错误已在拦截器中处理，这里不需要重复
      console.warn('网络错误或后端服务未运行')
    }
  } finally {
    loading.value = false
  }
}

// 获取任务统计
const fetchTaskStats = async () => {
  try {
    const response = await api.getTaskStats()
    if (response?.success && response.data) {
      taskStats.value = response.data
    } else {
      // 如果获取失败，重置统计
      taskStats.value = {
        total: 0,
        pending: 0,
        processing: 0,
        completed: 0,
        failed: 0
      }
    }
  } catch (error) {
    console.error('获取任务统计失败', error)
    // 重置统计以避免显示错误数据
    taskStats.value = {
      total: 0,
      pending: 0,
      processing: 0,
      completed: 0,
      failed: 0
    }
  }
}

// 判断是否可以恢复任务
const canResumeTask = (task: TaskInfo) => {
  // 失败的任务可以恢复
  if (task.status === 'failed') {
    return true
  }
  // 已完成但有多个文件的任务可以继续处理
  if (task.status === 'completed' && (task.filenames?.length || 1) > 1) {
    return true
  }
  return false
}

// 获取状态文本
const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    pending: '待处理',
    processing: '处理中',
    completed: '已完成',
    failed: '失败'
  }
  return statusMap[status] || status
}

// 获取状态类型
const getStatusType = (status: string) => {
  const typeMap: Record<string, any> = {
    pending: 'warning',
    processing: 'primary',
    completed: 'success',
    failed: 'danger'
  }
  return typeMap[status] || 'info'
}

// 格式化日期
const formatDate = (date: string) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

// 启动任务
const handleStartTask = (task: TaskInfo) => {
  selectedTask.value = task
  startDialogVisible.value = true
}

// 确认启动任务
const confirmStartTask = async () => {
  if (!selectedTask.value) return

  startLoading.value = true
  try {
    const response = await api.startTask(selectedTask.value.task_id, configStore.config)
    if (response.success) {
      ElMessage.success('任务已启动')
      startDialogVisible.value = false
      await refreshTasks()
    } else {
      ElMessage.error(response.error || '任务启动失败')
    }
  } catch (error) {
    ElMessage.error('任务启动失败')
  } finally {
    startLoading.value = false
  }
}

// 恢复中断的任务
const handleResumeTask = async (task: TaskInfo) => {
  try {
    const response = await api.resumeTask(task.task_id, task.config || configStore.config)
    if (response.success) {
      if (task.status === 'failed') {
        ElMessage.success('任务已恢复并重新启动')
      } else {
        ElMessage.success('任务已重新启动，将处理所有文件')
      }
      await refreshTasks()
    } else {
      ElMessage.error(response.error || '任务恢复失败')
    }
  } catch (error) {
    ElMessage.error('任务恢复失败')
  }
}

// 下载任务结果
const handleDownload = async (task: TaskInfo) => {
  try {
    const blob = await api.downloadTask(task.task_id)
    const url = window.URL.createObjectURL(blob as Blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${task.filename}_output.json`
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('下载成功')
  } catch (error) {
    ElMessage.error('下载失败')
  }
}

// 查看详情
const handleViewDetail = (task: TaskInfo) => {
  router.push(`/task/${task.task_id}`)
}

// 审核数据
const handleReview = (task: TaskInfo) => {
  router.push(`/review/${task.task_id}`)
}

// 删除任务
const handleDelete = async (task: TaskInfo) => {
  const success = await taskStore.deleteTask(task.task_id)
  if (success) {
    ElMessage.success('删除成功')
    await refreshTasks()
  } else {
    ElMessage.error('删除失败')
  }
}

// 行点击
const handleRowClick = (task: TaskInfo) => {
  handleViewDetail(task)
}

// 初始化
onMounted(async () => {
  try {
    await configStore.loadConfig()
    await refreshTasks()
  } catch (error) {
    console.error('初始化失败:', error)
    ElMessage.error('页面初始化失败，请刷新页面重试')
  }
  // 自动刷新已禁用，用户可以通过点击刷新按钮手动刷新
  // refreshTimer = window.setInterval(() => {
  //   refreshTasks()
  // }, 5000)
})

// 清理
onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.tasks-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
  width: 100%;
  max-width: 100%;
  animation: fadeIn 0.3s ease-in-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.table-card {
  width: 100%;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.08);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 18px;
  font-weight: 600;
  color: white;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 24px;
  flex: 1;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  white-space: nowrap;
}

.stats-inline {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.stat-inline-item {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.9);
  white-space: nowrap;
}

.stat-inline-item strong {
  font-size: 16px;
  font-weight: 700;
  margin-left: 4px;
}

.stat-inline-item.pending strong {
  color: #ffd666;
}

.stat-inline-item.processing strong {
  color: #91d5ff;
}

.stat-inline-item.completed strong {
  color: #95de64;
}

.stat-inline-item.failed strong {
  color: #ffa39e;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

:deep(.el-card__header) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-bottom: none;
  padding: 18px 20px;
}

:deep(.el-card__header .card-header) {
  color: white;
}

:deep(.el-card__header .el-button) {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.3);
  color: white;
}

:deep(.el-card__header .el-button:hover) {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.5);
}

:deep(.el-card__header .el-input__wrapper) {
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: none;
}

:deep(.el-card__header .el-input__inner) {
  color: white;
}

:deep(.el-card__header .el-input__inner::placeholder) {
  color: rgba(255, 255, 255, 0.7);
}

:deep(.el-card__header .el-select) {
  --el-select-input-color: white;
}

:deep(.el-card__header .el-select .el-input__wrapper) {
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: none;
}

:deep(.el-card__header .el-select .el-input__inner) {
  color: white;
}

:deep(.el-card__header .el-select .el-input__inner::placeholder) {
  color: rgba(255, 255, 255, 0.7);
}

:deep(.el-card__header .el-select .el-select__caret) {
  color: rgba(255, 255, 255, 0.7);
}

:deep(.el-table) {
  border-radius: 8px;
}

:deep(.el-table__row) {
  cursor: pointer;
  transition: all 0.2s;
}

:deep(.el-table__row:hover) {
  background-color: #f0f9ff !important;
  transform: scale(1.001);
}

:deep(.el-table th) {
  background-color: #f8fafc;
  font-weight: 600;
  color: #475569;
}

.token-usage-cell {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.token-total {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.token-detail {
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-size: 12px;
  color: #909399;
}

.token-input {
  color: #409eff;
  font-weight: 500;
}

.token-output {
  color: #67c23a;
  font-weight: 500;
}

.model-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.model-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.model-label {
  color: #909399;
  font-weight: 500;
}

.model-name {
  color: #303133;
  font-weight: 400;
}

.status-text {
  color: #606266;
  font-size: 14px;
  font-weight: 500;
}

:deep(.el-button) {
  border-radius: 6px;
  font-weight: 500;
  transition: all 0.3s;
}

:deep(.el-button:hover) {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

:deep(.el-tag) {
  border-radius: 4px;
  font-weight: 500;
  padding: 4px 10px;
}

/* 添加成功/警告/错误颜色的渐变效果 */
:deep(.el-tag--success) {
  background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
  border: none;
}

:deep(.el-tag--warning) {
  background: linear-gradient(135deg, #e6a23c 0%, #f5a742 100%);
  border: none;
}

:deep(.el-tag--danger) {
  background: linear-gradient(135deg, #f56c6c 0%, #f78989 100%);
  border: none;
}

:deep(.el-tag--primary) {
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  border: none;
}
</style>

