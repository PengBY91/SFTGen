<template>
  <div class="datog-pipeline-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>DA-ToG 管道</span>
        </div>
      </template>

      <el-alert
        title="DA-ToG 管道说明"
        type="info"
        :closable="false"
        style="margin-bottom: 24px"
      >
        <template #default>
          <div style="font-size: 13px; line-height: 1.8">
            <p>DA-ToG 管道通过以下步骤生成领域特定的SFT数据：</p>
            <ol style="margin: 8px 0; padding-left: 24px">
              <li><strong>意图采样</strong>：从意图树中根据采样策略选择目标意图</li>
              <li><strong>知识检索</strong>：从知识图谱中检索相关事实子图</li>
              <li><strong>问答生成</strong>：基于意图和知识生成问答对</li>
              <li><strong>质量评审</strong>：使用评审器过滤低质量数据</li>
            </ol>
          </div>
        </template>
      </el-alert>

      <el-form :model="pipelineConfig" label-width="160px" label-position="left">
        <el-collapse v-model="activeNames">
          <!-- 基础配置 -->
          <el-collapse-item title="基础配置" name="basic">
            <el-form-item label="领域配置路径">
              <el-input
                v-model="pipelineConfig.domain_config_path"
                placeholder="graphgen/configs/datog/xxx"
              />
              <span class="form-item-tip">包含领域特定配置的YAML文件路径</span>
            </el-form-item>

            <el-form-item label="意图树路径">
              <el-input
                v-model="pipelineConfig.taxonomy_path"
                placeholder="请选择意图树文件"
              >
                <template #append>
                  <el-button @click="showTaxonomySelector = true">选择</el-button>
                </template>
              </el-input>
              <span class="form-item-tip">用于生成目标意图的意图树文件</span>
            </el-form-item>

            <el-form-item label="输入文件">
              <el-input
                v-model="pipelineConfig.input_file"
                placeholder="领域文档路径"
              />
              <span class="form-item-tip">领域原始文档，用于构建知识图谱</span>
            </el-form-item>
          </el-collapse-item>

          <!-- 知识图谱配置 -->
          <el-collapse-item title="知识图谱配置" name="kg">
            <el-form-item label="知识图谱路径">
              <el-input
                v-model="pipelineConfig.kg_path"
                placeholder="已构建的知识图谱文件路径"
              />
              <span class="form-item-tip">如已存在知识图谱，可跳过构建步骤</span>
            </el-form-item>

            <el-form-item label="自动生成意图树">
              <el-switch v-model="pipelineConfig.generate_taxonomy" />
              <span class="form-item-tip">从源文档自动生成意图树（实验性功能）</span>
            </el-form-item>

            <el-form-item
              label="源文档"
              v-if="pipelineConfig.generate_taxonomy"
            >
              <el-input
                v-model="pipelineConfig.source_document"
                placeholder="用于自动生成意图树的源文档"
              />
              <span class="form-item-tip">输入文档，LLM将从中提取层次化意图</span>
            </el-form-item>
          </el-collapse-item>

          <!-- 输出配置 -->
          <el-collapse-item title="输出配置" name="output">
            <el-form-item label="输出路径">
              <el-input
                v-model="pipelineConfig.output_path"
                placeholder="data/output/datog/xxx.json"
              />
              <span class="form-item-tip">生成的问答对将保存到此文件</span>
            </el-form-item>
          </el-collapse-item>
        </el-collapse>

        <div class="action-buttons">
          <el-button size="large" @click="handleReset">重置</el-button>
          <el-button
            type="primary"
            size="large"
            @click="handleRun"
            :loading="running"
            :disabled="!canRun"
          >
            <el-icon v-if="!running"><VideoPlay /></el-icon>
            <el-icon v-else><Loading /></el-icon>
            {{ running ? '运行中...' : '启动管道' }}
          </el-button>
        </div>
      </el-form>
    </el-card>

    <!-- 运行状态 -->
    <el-card v-if="pipelineStatus" style="margin-top: 20px">
      <template #header>
        <div class="card-header">
          <span>运行状态</span>
          <el-tag :type="statusType" size="large">{{ statusText }}</el-tag>
        </div>
      </template>

      <el-descriptions :column="2" border>
        <el-descriptions-item label="任务ID">
          <code>{{ pipelineStatus.task_id }}</code>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          {{ statusText }}
        </el-descriptions-item>
        <el-descriptions-item label="输出文件" :span="2">
          <span v-if="pipelineStatus.output_file">
            {{ pipelineStatus.output_file }}
          </span>
          <span v-else class="text-muted">暂无</span>
        </el-descriptions-item>
        <el-descriptions-item label="进度" :span="2" v-if="pipelineStatus.progress !== undefined">
          <el-progress
            :percentage="pipelineStatus.progress"
            :status="progressStatus"
          />
        </el-descriptions-item>
        <el-descriptions-item
          label="错误信息"
          :span="2"
          v-if="pipelineStatus.error_message"
        >
          <el-alert type="error" :closable="false">
            {{ pipelineStatus.error_message }}
          </el-alert>
        </el-descriptions-item>
      </el-descriptions>

      <div class="status-actions">
        <el-button @click="refreshStatus">刷新状态</el-button>
        <el-button @click="clearStatus">清除状态</el-button>
      </div>
    </el-card>

    <!-- 意图树选择器对话框 -->
    <el-dialog
      v-model="showTaxonomySelector"
      title="选择意图树"
      width="600px"
    >
      <el-table
        :data="availableTaxonomies"
        v-loading="loadingTaxonomies"
        @row-click="selectTaxonomy"
        style="cursor: pointer"
      >
        <el-table-column prop="name" label="名称">
          <template #default="{ row }">
            <span>{{ row.name }}</span>
            <el-tag v-if="row.builtin" size="small" type="warning" style="margin-left: 8px">内置</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="domain" label="领域" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.domain" size="small">{{ row.domain }}</el-tag>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="path" label="路径" show-overflow-tooltip />
      </el-table>

      <el-empty
        v-if="!loadingTaxonomies && availableTaxonomies.length === 0"
        description="暂无可用的意图树"
      >
        <el-button type="primary" @click="goToTaxonomies">创建意图树</el-button>
      </el-empty>

      <template #footer>
        <el-button @click="showTaxonomySelector = false">取消</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDAToGStore } from '@/stores/datog'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VideoPlay, Loading } from '@element-plus/icons-vue'
import type { DAToGPipelineConfig, DAToGTaxonomy, PipelineTaskStatus } from '@/api/types'

const route = useRoute()
const router = useRouter()
const datogStore = useDAToGStore()

const activeNames = ref(['basic', 'kg', 'output'])
const showTaxonomySelector = ref(false)
const loadingTaxonomies = ref(false)
const refreshTimer = ref<number | null>(null)

const pipelineConfig = ref<DAToGPipelineConfig>({
  domain_config_path: '',
  taxonomy_path: '',
  input_file: '',
  kg_path: '',
  output_path: '',
  generate_taxonomy: false,
  source_document: ''
})

const availableTaxonomies = ref<DAToGTaxonomy[]>([])

const pipelineStatus = computed(() => datogStore.pipelineStatus)
const running = computed(() => datogStore.pipelineRunning)

// 判断是否可以运行
const canRun = computed(() => {
  return pipelineConfig.value.taxonomy_path &&
         pipelineConfig.value.domain_config_path &&
         !running.value
})

// 状态类型
const statusType = computed(() => {
  if (!pipelineStatus.value) return 'info'
  switch (pipelineStatus.value.status) {
    case 'running':
      return 'warning'
    case 'completed':
      return 'success'
    case 'failed':
      return 'danger'
    default:
      return 'info'
  }
})

// 状态文本
const statusText = computed(() => {
  if (!pipelineStatus.value) return '未启动'
  switch (pipelineStatus.value.status) {
    case 'not_started':
      return '未启动'
    case 'running':
      return '运行中'
    case 'completed':
      return '已完成'
    case 'failed':
      return '失败'
    default:
      return '未知'
  }
})

// 进度状态
const progressStatus = computed(() => {
  if (!pipelineStatus.value) return undefined
  const progress = pipelineStatus.value.progress || 0
  if (progress >= 100) return 'success'
  if (progress > 0) return undefined
  return 'exception'
})

// 加载可用意图树
const loadAvailableTaxonomies = async () => {
  loadingTaxonomies.value = true
  try {
    await datogStore.loadTaxonomies()
    availableTaxonomies.value = datogStore.taxonomies
  } finally {
    loadingTaxonomies.value = false
  }
}

// 选择意图树
const selectTaxonomy = (taxonomy: DAToGTaxonomy) => {
  pipelineConfig.value.taxonomy_path = taxonomy.path
  showTaxonomySelector.value = false
}

// 运行管道
const handleRun = async () => {
  if (!canRun.value) {
    ElMessage.warning('请完善配置后再启动')
    return
  }

  try {
    await ElMessageBox.confirm(
      '确定要启动 DA-ToG 管道吗？这可能需要较长时间。',
      '确认启动',
      {
        confirmButtonText: '启动',
        cancelButtonText: '取消',
        type: 'info'
      }
    )

    const result = await datogStore.runPipeline(pipelineConfig.value)
    if (result) {
      ElMessage.success('管道已启动')
      startAutoRefresh()
    }
  } catch (error) {
    // 用户取消
  }
}

// 重置配置
const handleReset = () => {
  pipelineConfig.value = {
    domain_config_path: '',
    taxonomy_path: '',
    input_file: '',
    kg_path: '',
    output_path: '',
    generate_taxonomy: false,
    source_document: ''
  }
}

// 刷新状态
const refreshStatus = async () => {
  if (pipelineStatus.value?.task_id) {
    await datogStore.getPipelineStatus(pipelineStatus.value.task_id)
  }
}

// 清除状态
const clearStatus = () => {
  datogStore.pipelineStatus = null
  stopAutoRefresh()
}

// 开始自动刷新
const startAutoRefresh = () => {
  if (refreshTimer.value) return
  refreshTimer.value = window.setInterval(async () => {
    if (pipelineStatus.value?.task_id) {
      await refreshStatus()
      // 如果完成或失败，停止刷新
      if (['completed', 'failed'].includes(pipelineStatus.value?.status || '')) {
        stopAutoRefresh()
      }
    }
  }, 3000)
}

// 停止自动刷新
const stopAutoRefresh = () => {
  if (refreshTimer.value) {
    clearInterval(refreshTimer.value)
    refreshTimer.value = null
  }
}

// 跳转到意图树管理
const goToTaxonomies = () => {
  showTaxonomySelector.value = false
  router.push('/datog/taxonomies')
}

// 检查URL参数中的任务ID
const checkTaskId = () => {
  const taskId = route.query.task_id as string
  if (taskId) {
    refreshStatus()
  }
}

onMounted(() => {
  loadAvailableTaxonomies()
  checkTaskId()
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<style scoped>
.datog-pipeline-container {
  max-width: 1200px;
  margin: 0 auto;
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

:deep(.el-card) {
  border-radius: 12px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.08);
  transition: all 0.3s;
}

:deep(.el-card:hover) {
  box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.12);
}

:deep(.el-card__header) {
  background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%);
  color: white;
  border-bottom: none;
  padding: 20px 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 20px;
  font-weight: 600;
  color: white;
}

:deep(.el-card__body) {
  padding: 32px;
}

.form-item-tip {
  display: block;
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
  padding: 8px 12px;
  background: #f8fafc;
  border-left: 3px solid #8b5cf6;
  border-radius: 4px;
}

.action-buttons {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid #e4e7ed;
}

:deep(.el-collapse) {
  border: none;
}

:deep(.el-collapse-item) {
  margin-bottom: 16px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #e4e7ed;
  background: white;
}

:deep(.el-collapse-item__header) {
  font-size: 16px;
  font-weight: 600;
  background: #fafbfc;
  padding: 16px 20px;
  border-bottom: 1px solid #e4e7ed;
  color: #303133;
  transition: all 0.3s;
}

:deep(.el-collapse-item__header:hover) {
  background: #f0f2f5;
  color: #8b5cf6;
}

:deep(.el-collapse-item__wrap) {
  border: none;
  background: white;
}

:deep(.el-collapse-item__content) {
  padding: 24px 20px;
}

:deep(.el-form-item) {
  margin-bottom: 24px;
}

:deep(.el-form-item__label) {
  font-weight: 500;
  color: #475569;
}

:deep(.el-input__wrapper) {
  border-radius: 6px;
  box-shadow: 0 0 0 1px #dcdfe6 inset;
  transition: all 0.3s;
}

:deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #c0c4cc inset;
}

:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #8b5cf6 inset;
}

:deep(.el-switch.is-checked .el-switch__core) {
  background: linear-gradient(90deg, #8b5cf6 0%, #6366f1 100%);
  border-color: #8b5cf6;
}

:deep(.el-alert) {
  border-radius: 8px;
  border: none;
  padding: 16px;
}

:deep(.el-alert--info) {
  background: linear-gradient(135deg, #e0e7ff 0%, #f0f9ff 100%);
}

:deep(.el-descriptions) {
  border-radius: 8px;
  overflow: hidden;
}

:deep(.el-descriptions__label) {
  background: #f8fafc;
  font-weight: 600;
  color: #475569;
}

:deep(.el-descriptions__body) {
  color: #303133;
}

code {
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

.text-muted {
  color: #909399;
}

.status-actions {
  display: flex;
  gap: 12px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #e4e7ed;
}

:deep(.el-dialog) {
  border-radius: 12px;
  overflow: hidden;
}

:deep(.el-dialog__header) {
  background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%);
  padding: 20px;
  margin: 0;
}

:deep(.el-dialog__title) {
  color: white;
  font-weight: 600;
}

:deep(.el-dialog__close) {
  color: white;
}

:deep(.el-table tbody tr:hover) {
  background: #f0f9ff;
}
</style>
