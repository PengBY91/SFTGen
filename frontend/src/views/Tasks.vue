<template>
  <div class="tasks-container">
    <el-card class="stats-card">
      <template #header>
        <div class="card-header">
          <span>任务统计</span>
          <el-button size="small" @click="refreshTasks" :loading="loading">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>
      <div class="stats-content">
        <div class="stat-item">
          <div class="stat-value">{{ taskStats.total }}</div>
          <div class="stat-label">总任务数</div>
        </div>
        <div class="stat-item">
          <div class="stat-value" style="color: #e6a23c">{{ taskStats.pending }}</div>
          <div class="stat-label">待处理</div>
        </div>
        <div class="stat-item">
          <div class="stat-value" style="color: #409eff">{{ taskStats.processing }}</div>
          <div class="stat-label">处理中</div>
        </div>
        <div class="stat-item">
          <div class="stat-value" style="color: #67c23a">{{ taskStats.completed }}</div>
          <div class="stat-label">已完成</div>
        </div>
        <div class="stat-item">
          <div class="stat-value" style="color: #f56c6c">{{ taskStats.failed }}</div>
          <div class="stat-label">失败</div>
        </div>
      </div>
    </el-card>

    <el-card class="table-card">
      <template #header>
        <div class="card-header">
          <span>任务列表</span>
          <el-input
            v-model="searchText"
            placeholder="搜索任务"
            style="width: 200px"
            clearable
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
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
                <el-tag size="small" type="primary">合成器: {{ row.synthesizer_model }}</el-tag>
              </div>
              <div v-if="row.trainee_model" class="model-item">
                <el-tag size="small" type="success">训练: {{ row.trainee_model }}</el-tag>
              </div>
              <span v-if="!row.synthesizer_model && !row.trainee_model">-</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
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

// 过滤后的任务列表
const filteredTasks = computed(() => {
  if (!searchText.value) {
    return taskStore.tasks
  }
  return taskStore.tasks.filter((task) =>
    (task.task_name || task.filename || '').toLowerCase().includes(searchText.value.toLowerCase())
  )
})

// 刷新任务列表
const refreshTasks = async () => {
  loading.value = true
  await taskStore.fetchTasks()
  await fetchTaskStats()
  loading.value = false
}

// 获取任务统计
const fetchTaskStats = async () => {
  try {
    const response = await api.getTaskStats()
    if (response.success && response.data) {
      taskStats.value = response.data
    }
  } catch (error) {
    console.error('获取任务统计失败', error)
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
  await configStore.loadConfig()
  await refreshTasks()
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
  gap: 20px;
  width: 100%;
  max-width: 100%;
}

.stats-card {
  width: 100%;
}

.stats-content {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 20px;
}

.stat-item {
  text-align: center;
}

.stat-value {
  font-size: 32px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  color: #909399;
}

.table-card {
  width: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

:deep(.el-table__row) {
  cursor: pointer;
}

:deep(.el-table__row:hover) {
  background-color: #f5f7fa;
}

.token-usage-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.token-total {
  font-size: 14px;
}

.token-detail {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 12px;
  color: #909399;
}

.token-input {
  color: #409eff;
}

.token-output {
  color: #67c23a;
}

.model-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.model-item {
  display: flex;
  align-items: center;
}
</style>

