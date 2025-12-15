<template>
  <div class="task-detail-container">
    <el-card v-loading="loading">
      <template #header>
        <div class="card-header">
          <el-button @click="goBack" :icon="ArrowLeft">返回</el-button>
          <span>任务详情</span>
          <div class="header-actions">
            <el-button
              @click="handleViewSource"
              :icon="View"
            >
              查看原文件
            </el-button>
            <!-- 管理员操作 -->
            <template v-if="authStore.isAdmin">
              <el-button
                type="primary"
                :disabled="task?.status !== 'pending'"
                @click="handleStart"
              >
                启动任务
              </el-button>
              <el-button
                type="success"
                :disabled="task?.status !== 'completed'"
                @click="handleDownload"
              >
                下载结果
              </el-button>
              <el-popconfirm title="确定要删除这个任务吗？" @confirm="handleDelete">
                <template #reference>
                  <el-button type="danger">删除任务</el-button>
                </template>
              </el-popconfirm>
            </template>
            <!-- 审核员操作 -->
            <template v-else>
              <el-button
                type="success"
                :disabled="task?.status !== 'completed'"
                @click="handleDownload"
              >
                下载结果
              </el-button>
            </template>
          </div>
        </div>
      </template>

      <div v-if="task" class="task-content">
        <!-- 基本信息 -->
        <el-descriptions title="基本信息" :column="2" border>
          <el-descriptions-item label="任务ID">{{ task.task_id }}</el-descriptions-item>
          <el-descriptions-item label="任务名称">{{ task.task_name || task.filename }}</el-descriptions-item>
          <el-descriptions-item label="任务类型">
            <el-tag v-if="task.task_type === 'evaluation'" type="success">
              评测任务
            </el-tag>
            <el-tag v-else type="primary">
              SFT任务
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="任务简介">{{ task.task_description || '-' }}</el-descriptions-item>
          <el-descriptions-item label="文件数量">{{ task.filenames?.length || 1 }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(task.status)">
              {{ getStatusText(task.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item :label="task.task_type === 'evaluation' ? '评测项数' : '问答对数'">
            {{ task.qa_count || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatDate(task.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="开始时间">
            {{ task.started_at ? formatDate(task.started_at) : '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="完成时间">
            {{ task.completed_at ? formatDate(task.completed_at) : '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="处理时长">
            {{ task.processing_time ? `${task.processing_time.toFixed(2)} 秒` : '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="合成器模型">
            {{ task.synthesizer_model || task.config?.synthesizer_model || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="训练模型">
            {{ task.trainee_model || task.config?.trainee_model || '-' }}
          </el-descriptions-item>
        </el-descriptions>

        <!-- 文件管理 -->
        <el-card shadow="never" style="margin-top: 20px">
          <template #header>
            <div class="file-header">
              <span>文件管理</span>
              <!-- 只有管理员可以添加文件 -->
              <el-button
                v-if="authStore.isAdmin"
                type="primary"
                size="small"
                :disabled="task.status === 'processing'"
                @click="showUploadDialog = true"
              >
                <el-icon><Plus /></el-icon>
                添加文件
              </el-button>
            </div>
          </template>
          
          <el-table :data="task.filenames || [task.filename]" style="width: 100%">
            <el-table-column label="文件路径" min-width="400">
              <template #default="{ $index }">
                {{ task.filepaths?.[$index] || task.file_path }}
              </template>
            </el-table-column>
            <el-table-column label="操作" :width="authStore.isAdmin ? '150' : '80'">
              <template #default="{ $index }">
                <el-button
                  size="small"
                  type="primary"
                  @click="handleViewFile($index)"
                >
                  查看
                </el-button>
                <!-- 只有管理员可以删除文件 -->
                <el-button
                  v-if="authStore.isAdmin && task.status === 'pending' && (task.filenames?.length || 1) > 1"
                  size="small"
                  type="danger"
                  @click="handleRemoveFile($index)"
                >
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- Token 使用情况 -->
        <el-descriptions
          v-if="task.token_usage"
          title="Token 使用情况"
          :column="3"
          border
          style="margin-top: 20px"
        >
          <el-descriptions-item label="Synthesizer Tokens">
            {{ task.token_usage.synthesizer_tokens.toLocaleString() }}
            <span v-if="task.token_usage.synthesizer_input_tokens !== undefined" class="token-detail">
              (输入: {{ task.token_usage.synthesizer_input_tokens.toLocaleString() }}, 
              输出: {{ task.token_usage.synthesizer_output_tokens.toLocaleString() }})
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="Trainee Tokens" v-if="task.token_usage.trainee_tokens > 0">
            {{ task.token_usage.trainee_tokens.toLocaleString() }}
            <span v-if="task.token_usage.trainee_input_tokens !== undefined" class="token-detail">
              (输入: {{ task.token_usage.trainee_input_tokens.toLocaleString() }}, 
              输出: {{ task.token_usage.trainee_output_tokens.toLocaleString() }})
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="Total Tokens">
            <el-tag type="success" size="large">
              {{ task.token_usage.total_tokens.toLocaleString() }}
            </el-tag>
            <span v-if="task.token_usage.total_input_tokens !== undefined" class="token-detail" style="margin-left: 10px">
              (输入: {{ task.token_usage.total_input_tokens.toLocaleString() }}, 
              输出: {{ task.token_usage.total_output_tokens.toLocaleString() }})
            </span>
          </el-descriptions-item>
        </el-descriptions>

        <!-- 错误信息 -->
        <el-alert
          v-if="task.error_message"
          title="错误信息"
          type="error"
          :description="task.error_message"
          :closable="false"
          show-icon
          style="margin-top: 20px"
        />

        <!-- 输出文件信息 -->
        <el-card v-if="task.output_file" shadow="never" style="margin-top: 20px">
          <template #header>
            <span>输出文件</span>
          </template>
          <div class="output-file-info">
            <el-icon class="file-icon"><Document /></el-icon>
            <div class="file-details">
              <div class="file-name">{{ task.output_file }}</div>
              <el-button type="primary" size="small" @click="handleDownload">
                <el-icon><Download /></el-icon>
                下载文件
              </el-button>
            </div>
          </div>
        </el-card>

        <!-- 操作历史 -->
        <el-timeline style="margin-top: 40px">
          <el-timeline-item :timestamp="formatDate(task.created_at)" placement="top">
            <el-card>
              <h4>任务创建</h4>
              <p>任务已创建，等待启动</p>
            </el-card>
          </el-timeline-item>

          <el-timeline-item
            v-if="task.started_at"
            :timestamp="formatDate(task.started_at)"
            placement="top"
          >
            <el-card>
              <h4>任务启动</h4>
              <p>任务开始处理</p>
            </el-card>
          </el-timeline-item>

          <el-timeline-item
            v-if="task.completed_at"
            :timestamp="formatDate(task.completed_at)"
            placement="top"
            :type="task.status === 'completed' ? 'success' : 'danger'"
          >
            <el-card>
              <h4>{{ task.status === 'completed' ? '任务完成' : '任务失败' }}</h4>
              <p v-if="task.status === 'completed'">
                任务成功完成，耗时 {{ task.processing_time?.toFixed(2) }} 秒
              </p>
              <p v-else>{{ task.error_message }}</p>
            </el-card>
          </el-timeline-item>
        </el-timeline>

        <!-- 评测集展示 (仅评测任务) -->
        <el-card shadow="never" style="margin-top: 40px" v-if="task.status === 'completed' && task.task_type === 'evaluation'">
          <template #header>
            <div class="card-header-inline">
              <span>评测集</span>
              <el-button
                v-if="evaluationData"
                type="primary"
                size="small"
                @click="handleDownloadEvaluation"
              >
                <el-icon><Download /></el-icon>
                下载评测集
              </el-button>
            </div>
          </template>

          <div v-loading="evaluationLoading">
            <div v-if="evaluationData">
              <!-- 统计信息 -->
              <el-descriptions title="评测集统计" :column="2" border>
                <el-descriptions-item label="评测集名称">
                  {{ evaluationData.name }}
                </el-descriptions-item>
                <el-descriptions-item label="总评测项">
                  {{ evaluationStats.total_items }}
                </el-descriptions-item>
                <el-descriptions-item label="生成时间" :span="2">
                  {{ evaluationStats.generated_at ? formatDate(evaluationStats.generated_at) : '未知' }}
                </el-descriptions-item>
              </el-descriptions>

              <!-- 类型分布 -->
              <div style="margin-top: 24px">
                <h4 style="margin-bottom: 16px">评测类型分布</h4>
                <div v-for="(value, key) in evaluationStats.type_distribution" :key="key" style="margin-bottom: 12px">
                  <div style="display: flex; justify-content: space-between; margin-bottom: 4px">
                    <span>{{ getEvalTypeName(key) }}</span>
                    <span>{{ Math.round(value * 100) }}%</span>
                  </div>
                  <el-progress
                    :percentage="Math.round(value * 100)"
                    :color="getEvalTypeColor(key)"
                  />
                </div>
              </div>

              <!-- 难度分布 -->
              <div style="margin-top: 24px">
                <h4 style="margin-bottom: 16px">难度分布</h4>
                <div v-for="(value, key) in evaluationStats.difficulty_distribution" :key="key" style="margin-bottom: 12px">
                  <div style="display: flex; justify-content: space-between; margin-bottom: 4px">
                    <span>{{ getEvalDifficultyName(key) }}</span>
                    <span>{{ Math.round(value * 100) }}%</span>
                  </div>
                  <el-progress
                    :percentage="Math.round(value * 100)"
                    :color="getEvalDifficultyColor(key)"
                  />
                </div>
              </div>

              <!-- 评测项预览 -->
              <div style="margin-top: 24px">
                <h4 style="margin-bottom: 16px">评测项预览（前10项）</h4>
                <el-table :data="evaluationData.items.slice(0, 10)" border style="width: 100%">
                  <el-table-column prop="id" label="ID" width="180" />
                  <el-table-column label="问题" min-width="300">
                    <template #default="{ row }">
                      <el-tooltip :content="row.question" placement="top">
                        <span>{{ row.question.substring(0, 50) }}{{ row.question.length > 50 ? '...' : '' }}</span>
                      </el-tooltip>
                    </template>
                  </el-table-column>
                  <el-table-column label="类型" width="120">
                    <template #default="{ row }">
                      <el-tag :color="getEvalTypeColor(row.type)" effect="light">
                        {{ getEvalTypeName(row.type) }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="难度" width="100">
                    <template #default="{ row }">
                      <el-tag :type="getEvalDifficultyTagType(row.difficulty)">
                        {{ getEvalDifficultyName(row.difficulty) }}
                      </el-tag>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </div>

            <el-empty v-else description="该任务未生成评测集" />
          </div>
        </el-card>
      </div>
    </el-card>

    <!-- 文件上传对话框 -->
    <el-dialog
      v-model="showUploadDialog"
      title="添加文件到任务"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-upload
        ref="uploadRef"
        class="upload-demo"
        drag
        :auto-upload="false"
        :limit="10"
        :file-list="newFileList"
        :on-change="handleFileChange"
        :on-remove="handleFileRemove"
        :on-exceed="handleExceed"
        accept=".txt,.json,.jsonl,.csv,.pdf,.docx,.md,.markdown"
        multiple
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          拖拽文件到此处或 <em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持 .txt, .json, .jsonl, .csv, .pdf, .docx, .md, .markdown 格式文件，最多10个文件
          </div>
        </template>
      </el-upload>

      <div v-if="newFileList.length > 0" class="file-info">
        <el-alert
          :title="`已选择 ${newFileList.length} 个文件`"
          type="success"
          :closable="false"
        />
      </div>

      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmAddFiles" :loading="uploading">
          确认添加
        </el-button>
      </template>
    </el-dialog>

    <!-- 查看原文件对话框 -->
    <el-dialog
      v-model="sourceDialogVisible"
      title="查看原始文件"
      width="80%"
      :close-on-click-modal="false"
    >
      <div v-loading="sourceLoading">
        <el-descriptions :column="3" border style="margin-bottom: 20px">
          <el-descriptions-item label="文件名">{{ sourceData.filename }}</el-descriptions-item>
          <el-descriptions-item label="文件大小">
            {{ formatFileSize(sourceData.file_size) }}
          </el-descriptions-item>
          <el-descriptions-item label="行数">{{ sourceData.line_count }}</el-descriptions-item>
          <el-descriptions-item label="编码">{{ sourceData.encoding }}</el-descriptions-item>
          <el-descriptions-item label="文件路径" :span="2">
            {{ sourceData.file_path }}
          </el-descriptions-item>
        </el-descriptions>

        <el-input
          v-model="sourceData.content"
          type="textarea"
          :rows="20"
          readonly
          style="font-family: 'Courier New', monospace"
        />
      </div>
      <template #footer>
        <el-button @click="sourceDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="copySource">
          <el-icon><CopyDocument /></el-icon>
          复制内容
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTaskStore } from '@/stores/task'
import { useConfigStore } from '@/stores/config'
import { useAuthStore } from '@/stores/auth'
import type { TaskInfo } from '@/api/types'
import api from '@/api'
import { getEvaluationDataset, getEvaluationStats, downloadEvaluation } from '@/api/evaluation'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Document, Download, View, CopyDocument, Plus, UploadFilled } from '@element-plus/icons-vue'
import type { UploadInstance, UploadProps, UploadRawFile, UploadUserFile } from 'element-plus'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()
const taskStore = useTaskStore()
const configStore = useConfigStore()
const authStore = useAuthStore()

const loading = ref(false)
const task = ref<TaskInfo | null>(null)
let refreshTimer: number | null = null

const taskId = route.params.id as string

// 文件上传相关
const showUploadDialog = ref(false)
const uploadRef = ref<UploadInstance>()
const newFileList = ref<UploadUserFile[]>([])
const uploading = ref(false)

// 原文件查看相关
const sourceDialogVisible = ref(false)
const sourceLoading = ref(false)
const sourceData = ref({
  filename: '',
  file_path: '',
  content: '',
  file_size: 0,
  line_count: 0,
  encoding: 'utf-8'
})

// 评测集相关
const evaluationLoading = ref(false)
const evaluationData = ref<any>(null)
const evaluationStats = ref<any>({
  total_items: 0,
  type_distribution: {},
  difficulty_distribution: {},
  generated_at: null
})

// 获取任务详情
const fetchTaskDetail = async () => {
  loading.value = true
  try {
    const data = await taskStore.fetchTask(taskId)
    if (data) {
      task.value = data
    }
  } finally {
    loading.value = false
  }
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

// 返回
const goBack = () => {
  router.back()
}

// 启动任务
const handleStart = async () => {
  if (!task.value) return

  try {
    const response = await api.startTask(task.value.task_id, configStore.config)
    if (response.success) {
      ElMessage.success('任务已启动')
      await fetchTaskDetail()
    } else {
      ElMessage.error(response.error || '任务启动失败')
    }
  } catch (error) {
    ElMessage.error('任务启动失败')
  }
}

// 下载结果
const handleDownload = async () => {
  if (!task.value) return

  try {
    const blob = await api.downloadTask(task.value.task_id)
    const url = window.URL.createObjectURL(blob as Blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${task.value.filename}_output.json`
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('下载成功')
  } catch (error) {
    ElMessage.error('下载失败')
  }
}

// 删除任务
const handleDelete = async () => {
  if (!task.value) return

  const success = await taskStore.deleteTask(task.value.task_id)
  if (success) {
    ElMessage.success('删除成功')
    router.push('/tasks')
  } else {
    ElMessage.error('删除失败')
  }
}

// 查看原文件
const handleViewSource = async () => {
  if (!task.value) return

  sourceLoading.value = true
  sourceDialogVisible.value = true

  try {
    const response = await api.getTaskSource(task.value.task_id)
    if (response.success && response.data) {
      sourceData.value = {
        filename: response.data.filename || '',
        file_path: response.data.file_path || '',
        content: response.data.content || '',
        file_size: response.data.file_size || 0,
        line_count: response.data.line_count || 0,
        encoding: response.data.encoding || 'utf-8'
      }
    } else {
      ElMessage.error(response.error || '获取文件内容失败')
      sourceDialogVisible.value = false
    }
  } catch (error) {
    ElMessage.error('获取文件内容失败')
    sourceDialogVisible.value = false
  } finally {
    sourceLoading.value = false
  }
}

// 复制文件内容
const copySource = async () => {
  try {
    await navigator.clipboard.writeText(sourceData.value.content)
    ElMessage.success('内容已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

// 文件上传相关方法
const handleFileChange: UploadProps['onChange'] = (uploadFile, uploadFiles) => {
  newFileList.value = uploadFiles
}

const handleFileRemove: UploadProps['onRemove'] = (uploadFile, uploadFiles) => {
  newFileList.value = uploadFiles
}

const handleExceed: UploadProps['onExceed'] = (files) => {
  ElMessage.warning('最多只能上传10个文件')
}

const confirmAddFiles = async () => {
  if (newFileList.value.length === 0) {
    ElMessage.warning('请选择要添加的文件')
    return
  }

  uploading.value = true
  try {
    const uploadedFilePaths: string[] = []
    
    // 上传所有文件
    for (const file of newFileList.value) {
      if (file.raw) {
        const response = await api.uploadFile(file.raw)
        if (response.success && response.data) {
          uploadedFilePaths.push(response.data.filepath)
        } else {
          throw new Error(`上传文件 ${file.name} 失败`)
        }
      }
    }

    // 更新任务文件列表
    const response = await api.addFilesToTask(taskId, uploadedFilePaths)
    if (response.success) {
      ElMessage.success(`成功添加 ${uploadedFilePaths.length} 个文件`)
      showUploadDialog.value = false
      newFileList.value = []
      await fetchTaskDetail() // 刷新任务详情
    } else {
      ElMessage.error(response.error || '添加文件失败')
    }
  } catch (error: any) {
    const message = typeof error === 'string' ? error : (error?.message || '添加文件失败')
    ElMessage.error(message)
  } finally {
    uploading.value = false
  }
}

const handleViewFile = async (index: number) => {
  if (!task.value) return
  
  sourceLoading.value = true
  sourceDialogVisible.value = true

  try {
    // 使用文件索引获取指定文件的内容
    const response = await api.getTaskSource(task.value.task_id, index)
    if (response.success && response.data) {
      sourceData.value = {
        filename: response.data.filename || task.value.filenames?.[index] || task.value.filename || '',
        file_path: response.data.file_path || task.value.filepaths?.[index] || task.value.file_path || '',
        content: response.data.content || '',
        file_size: response.data.file_size || 0,
        line_count: response.data.line_count || 0,
        encoding: response.data.encoding || 'utf-8'
      }
    } else {
      ElMessage.error(response.error || '获取文件内容失败')
      sourceDialogVisible.value = false
    }
  } catch (error) {
    ElMessage.error('获取文件内容失败')
    sourceDialogVisible.value = false
  } finally {
    sourceLoading.value = false
  }
}

const handleRemoveFile = async (index: number) => {
  if (!task.value) return
  
  try {
    const response = await api.removeFileFromTask(taskId, index)
    if (response.success) {
      ElMessage.success('文件已删除')
      await fetchTaskDetail() // 刷新任务详情
    } else {
      ElMessage.error(response.error || '删除文件失败')
    }
  } catch (error) {
    ElMessage.error('删除文件失败')
  }
}

// 格式化文件大小
const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

// 评测集相关函数
const loadEvaluationData = async () => {
  if (!task.value) return
  
  // 只有评测任务才加载评测数据
  if (task.value.task_type !== 'evaluation') {
    return
  }
  
  evaluationLoading.value = true
  try {
    // 获取评测集统计
    const statsResponse = await getEvaluationStats(task.value.task_id)
    if (statsResponse.success && statsResponse.data) {
      evaluationStats.value = statsResponse.data
    }

    // 获取评测集数据
    const dataResponse = await getEvaluationDataset(task.value.task_id)
    if (dataResponse.success && dataResponse.data) {
      evaluationData.value = dataResponse.data
    }
  } catch (error) {
    console.error('加载评测集失败:', error)
    // 评测集加载失败不影响页面其他功能
  } finally {
    evaluationLoading.value = false
  }
}

const getEvalTypeName = (type: string) => {
  const names: Record<string, string> = {
    knowledge_coverage: '知识覆盖',
    reasoning_ability: '推理能力',
    factual_accuracy: '事实准确',
    comprehensive: '综合应用'
  }
  return names[type] || type
}

const getEvalDifficultyName = (difficulty: string) => {
  const names: Record<string, string> = {
    easy: '简单',
    medium: '中等',
    hard: '困难'
  }
  return names[difficulty] || difficulty
}

const getEvalTypeColor = (type: string) => {
  const colors: Record<string, string> = {
    knowledge_coverage: '#409eff',
    reasoning_ability: '#67c23a',
    factual_accuracy: '#e6a23c',
    comprehensive: '#f56c6c'
  }
  return colors[type] || '#909399'
}

const getEvalDifficultyColor = (difficulty: string) => {
  const colors: Record<string, string> = {
    easy: '#67c23a',
    medium: '#e6a23c',
    hard: '#f56c6c'
  }
  return colors[difficulty] || '#909399'
}

const getEvalDifficultyTagType = (difficulty: string) => {
  const types: Record<string, any> = {
    easy: 'success',
    medium: 'warning',
    hard: 'danger'
  }
  return types[difficulty] || 'info'
}

const handleDownloadEvaluation = async () => {
  if (!task.value) return
  
  try {
    const response = await downloadEvaluation(taskId, 'json')
    const url = window.URL.createObjectURL(new Blob([response as any]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `${taskId}_evaluation.json`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    ElMessage.success('下载成功')
  } catch (error) {
    ElMessage.error('下载失败')
  }
}

onMounted(async () => {
  await fetchTaskDetail()
  // 只有评测任务才加载评测数据
  if (task.value?.task_type === 'evaluation') {
    await loadEvaluationData()
  }
  // 如果任务正在处理中，启动自动刷新
  if (task.value?.status === 'processing') {
    refreshTimer = window.setInterval(() => {
      fetchTaskDetail()
    }, 3000)
  }
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.task-detail-container {
  max-width: 1200px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.file-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.upload-demo {
  width: 100%;
}

.file-info {
  margin-top: 20px;
}

.task-content {
  padding: 20px 0;
}

.output-file-info {
  display: flex;
  align-items: center;
  gap: 20px;
}

.file-icon {
  font-size: 48px;
  color: #409eff;
}

.file-details {
  flex: 1;
}

.file-name {
  font-size: 14px;
  color: #606266;
  margin-bottom: 10px;
  word-break: break-all;
}

.token-detail {
  font-size: 12px;
  color: #909399;
  margin-left: 8px;
}

:deep(.el-descriptions__title) {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
}

:deep(.el-timeline-item__timestamp) {
  color: #909399;
  font-size: 13px;
}

.card-header-inline {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>

